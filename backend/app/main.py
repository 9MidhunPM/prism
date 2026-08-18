from __future__ import annotations

import hashlib
import io
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import fitz
from fastapi import BackgroundTasks, Cookie, Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageOps
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text

from . import database
from .ai import (EXAM_IMPORT_VERSION, PerceptionResult, answer_teacher_question,
                 grade_criterion, import_exam_pages, model_for, perceive_page, review_criterion)
from .auth import hash_password, random_token, token_hash, verify_password
from .demo import seed_demo_accounts
from .models import (AIArtifact, Account, AccountRole, Answer, AuthSession, ClassCohort, ClassMembership, CriterionEvaluation, EvaluationEvidence, Exam,
                     EvidenceRegion, ProcessingJob, Question, ReviewSuggestion, RubricCriterion, Student, Submission,
                     SubmissionPage, SubmissionStatus, Teacher, TeacherOverride)
from .settings import get_settings

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
settings = get_settings()
UPLOADS = settings.upload_root
MODEL = settings.openai_model
REVIEW_THRESHOLD = settings.ai_review_threshold
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}


def init_storage() -> None:
    UPLOADS.mkdir(parents=True, exist_ok=True)


def session():
    return database.SessionLocal()


def normalize_pages(original_path: Path, mime_type: str) -> list[dict]:
    """Create conservative, correctly oriented PNGs without modifying originals."""
    processed_dir = UPLOADS / "processed"
    processed_dir.mkdir(exist_ok=True)
    images: list[Image.Image] = []
    if mime_type == "application/pdf":
        with fitz.open(original_path) as document:
            if not document or len(document) > settings.max_submission_pages:
                raise HTTPException(422, f"Submissions may contain up to {settings.max_submission_pages} pages.")
            for pdf_page in document:
                pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                with Image.open(io.BytesIO(pixmap.tobytes("png"))) as rendered:
                    images.append(rendered.copy())
    else:
        try:
            with Image.open(original_path) as source:
                images = [source.copy()]
        except OSError as exc:
            raise HTTPException(422, "The uploaded image could not be decoded.") from exc
    normalized = []
    for page_number, image in enumerate(images, 1):
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((settings.max_image_dimension, settings.max_image_dimension))
        processed_path = processed_dir / f"{original_path.stem}-page-{page_number}.jpg"
        image.save(processed_path, "JPEG", quality=settings.processed_image_quality, optimize=True)
        normalized.append({"page_number": page_number, "processed_key": str(processed_path), "width": image.width, "height": image.height, "image_hash": hashlib.sha256(processed_path.read_bytes()).hexdigest()})
    return normalized


def page_preview_path(page: SubmissionPage) -> Path | None:
    """Return an existing JPEG preview, recreating one from a retained source."""
    if page.processed_key and Path(page.processed_key).is_file():
        return Path(page.processed_key)
    original = Path(page.original_key)
    if not original.is_file():
        return None
    if page.mime_type == "application/pdf":
        rendered = normalize_pages(original, page.mime_type)
        preview = rendered[page.page_number - 1] if len(rendered) >= page.page_number else None
        if not preview:
            return None
        page.processed_key = preview["processed_key"]
        page.width = preview["width"]
        page.height = preview["height"]
        page.image_hash = preview["image_hash"]
        return Path(preview["processed_key"])
    return original


def unavailable_preview() -> bytes:
    image = Image.new("RGB", (1200, 900), "#f3f1eb")
    draw = ImageDraw.Draw(image)
    draw.text((70, 110), "Original paper unavailable", fill="#172126")
    draw.text((70, 180), "The stored scan is no longer available. Upload a replacement page to continue.", fill="#566164")
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88)
    return buffer.getvalue()


def set_processing_stage(submission_id: str, stage: SubmissionStatus, error: str | None = None, increment_attempts: bool = False) -> None:
    with session() as db:
        submission = db.get(Submission, submission_id)
        job = db.scalar(select(ProcessingJob).where(ProcessingJob.submission_id == submission_id))
        if submission and job:
            submission.status = stage
            submission.error = error
            job.stage = stage
            job.error = error
            if increment_attempts:
                job.attempts += 1
            db.commit()


class CriterionInput(BaseModel):
    title: str
    description: str
    max_marks: float = Field(gt=0)
    concept: str


class QuestionInput(BaseModel):
    number: str
    text: str
    criteria: list[CriterionInput]


class ExamInput(BaseModel):
    title: str
    subject: str
    date: str | None = None
    class_id: str | None = None
    questions: list[QuestionInput]


class ReviewInput(BaseModel):
    comment: str = Field(min_length=3)


class OverrideInput(BaseModel):
    marks: float = Field(ge=0)
    reason: str | None = None


class AssistantQuery(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    mentions: list["MentionInput"] = []


class MentionInput(BaseModel):
    type: Literal["student", "class", "exam", "paper"]
    id: str


class ClassInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class StudentInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    identifier: str = Field(min_length=1, max_length=100)


class RosterInput(BaseModel):
    students: list[StudentInput] = Field(min_length=1, max_length=200)


class StudentAssignmentInput(BaseModel):
    student_id: str
    reason: str | None = Field(default=None, max_length=500)


class TeacherCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=256)
    name: str | None = Field(default=None, min_length=2, max_length=120)


def imported_draft(result) -> dict:
    warnings = list(result.warnings)
    clarifications = []
    questions = []
    for question in result.questions:
        criterion_total = sum(criterion.max_marks for criterion in question.criteria)
        if question.max_marks is not None and round(criterion_total, 2) != round(question.max_marks, 2):
            warnings.append(f"{question.number}: suggested criteria total {criterion_total:g}, but the paper shows {question.max_marks:g} marks.")
            clarifications.append({"type": "criterion_total_mismatch", "question_number": question.number, "message": "Confirm the marks shown on the paper or adjust the rubric total.", "required": True})
        if question.max_marks is None:
            clarifications.append({"type": "missing_question_marks", "question_number": question.number, "message": "Enter the maximum marks for this question before saving.", "required": True})
        if question.confidence < REVIEW_THRESHOLD:
            clarifications.append({"type": "low_question_confidence", "question_number": question.number, "message": "Check this question against the original paper; its extraction confidence is low.", "required": True})
        questions.append({
            "number": question.number,
            "text": question.text,
            "max_marks": question.max_marks,
            "confidence": question.confidence,
            "criteria": [criterion.model_dump() for criterion in question.criteria],
        })
    clarifications.append({"type": "question_count", "question_number": None, "message": f"Confirm that this paper contains {len(questions)} questions.", "required": True})
    return {"title": result.title, "subject": result.subject, "questions": questions, "warnings": list(dict.fromkeys(warnings)), "clarifications": clarifications, "prompt_version": EXAM_IMPORT_VERSION}


def current_account(session_token: str | None = Cookie(default=None, alias="prism_session")) -> dict:
    if not session_token:
        raise HTTPException(401, "Sign in to continue.")
    with session() as db:
        active_session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(session_token), AuthSession.revoked_at.is_(None), AuthSession.expires_at > datetime.now(timezone.utc)))
        account = db.get(Account, active_session.account_id) if active_session else None
        if not account:
            raise HTTPException(401, "Sign in to continue.")
        return {"id": account.id, "role": account.role.value, "teacher_id": account.teacher_id, "student_id": account.student_id, "email": account.email}


def current_teacher(account: dict = Depends(current_account)) -> dict:
    if account["role"] != AccountRole.TEACHER.value or not account["teacher_id"]:
        raise HTTPException(403, "Teacher access is required.")
    with session() as db:
        teacher = db.get(Teacher, account["teacher_id"])
        if not teacher:
            raise HTTPException(401, "Sign in to continue.")
        return {"id": teacher.id, "account_id": account["id"], "name": teacher.name, "email": teacher.email, "role": AccountRole.TEACHER.value}


def current_student(account: dict = Depends(current_account)) -> dict:
    if account["role"] != AccountRole.STUDENT.value or not account["student_id"]:
        raise HTTPException(403, "Student access is required.")
    with session() as db:
        student = db.get(Student, account["student_id"])
        if not student:
            raise HTTPException(401, "Sign in to continue.")
        return {"id": student.id, "account_id": account["id"], "name": student.name, "email": account["email"], "role": AccountRole.STUDENT.value}


def set_session(response: Response, account: Account) -> None:
    token = random_token()
    csrf_token = random_token()
    with session() as db:
        db.add(AuthSession(account_id=account.id, token_hash=token_hash(token), csrf_hash=token_hash(csrf_token), expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.session_ttl_seconds)))
        db.commit()
    response.set_cookie("prism_session", token, max_age=settings.session_ttl_seconds, httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/")
    response.set_cookie("prism_csrf", csrf_token, max_age=settings.session_ttl_seconds, httponly=False, secure=settings.session_cookie_secure, samesite="lax", path="/")


def owned_exam(db, exam_id: str, teacher_id: str) -> Exam:
    exam = db.scalar(select(Exam).where(Exam.id == exam_id, Exam.teacher_id == teacher_id))
    if not exam:
        raise HTTPException(404, "Exam not found")
    return exam


def active_owned_exam(db, exam_id: str, teacher_id: str) -> Exam:
    exam = owned_exam(db, exam_id, teacher_id)
    if exam.archived_at:
        raise HTTPException(404, "Exam not found")
    if exam.class_id:
        cohort = db.get(ClassCohort, exam.class_id)
        if not cohort or cohort.archived_at:
            raise HTTPException(404, "Exam not found")
    return exam


def owned_submission(db, submission_id: str, teacher_id: str) -> Submission:
    submission = db.scalar(select(Submission).join(Exam).where(Submission.id == submission_id, Exam.teacher_id == teacher_id))
    if not submission:
        raise HTTPException(404, "Submission not found")
    return submission


def active_owned_submission(db, submission_id: str, teacher_id: str) -> Submission:
    submission = owned_submission(db, submission_id, teacher_id)
    student = db.get(Student, submission.student_id)
    exam = active_owned_exam(db, submission.exam_id, teacher_id)
    if submission.archived_at or not student or student.archived_at:
        raise HTTPException(404, "Submission not found")
    return submission


def owned_class(db, class_id: str, teacher_id: str) -> ClassCohort:
    cohort = db.scalar(select(ClassCohort).where(ClassCohort.id == class_id, ClassCohort.teacher_id == teacher_id))
    if not cohort:
        raise HTTPException(404, "Class not found")
    return cohort


def owned_evaluation(db, evaluation_id: str, teacher_id: str) -> CriterionEvaluation:
    evaluation = db.scalar(select(CriterionEvaluation).join(Answer).join(Submission).join(Exam).where(CriterionEvaluation.id == evaluation_id, Exam.teacher_id == teacher_id))
    if not evaluation:
        raise HTTPException(404, "Evaluation not found")
    return evaluation


def owned_review(db, review_id: str, teacher_id: str) -> ReviewSuggestion:
    review = db.scalar(select(ReviewSuggestion).join(CriterionEvaluation).join(Answer).join(Submission).join(Exam).where(ReviewSuggestion.id == review_id, Exam.teacher_id == teacher_id))
    if not review:
        raise HTTPException(404, "Review not found")
    return review


def criterion_data(criterion: RubricCriterion) -> dict:
    return {"id": criterion.id, "title": criterion.title, "description": criterion.description, "max_marks": criterion.max_marks, "concept": criterion.concept_tags[0] if criterion.concept_tags else "Uncategorized"}


def exam_detail(exam_id: str, teacher_id: str | None = None) -> dict:
    with session() as db:
        statement = select(Exam).where(Exam.id == exam_id)
        if teacher_id:
            statement = statement.where(Exam.teacher_id == teacher_id)
        exam = db.scalar(statement)
        if not exam:
            raise HTTPException(404, "Exam not found")
        questions = []
        for question in db.scalars(select(Question).where(Question.exam_id == exam.id).order_by(Question.number)):
            criteria = [criterion_data(c) for c in db.scalars(select(RubricCriterion).where(RubricCriterion.question_id == question.id))]
            questions.append({"id": question.id, "exam_id": question.exam_id, "number": question.number, "text": question.text, "max_marks": sum(c["max_marks"] for c in criteria), "criteria": criteria})
        return {"id": exam.id, "title": exam.title, "subject": exam.subject, "date": exam.date.isoformat() if exam.date else None, "created_at": exam.created_at, "teacher_id": exam.teacher_id, "class_id": exam.class_id, "archived_at": exam.archived_at, "questions": questions, "total_marks": sum(q["max_marks"] for q in questions)}


def score_submission(db, submission: Submission) -> float:
    evaluations = db.scalars(select(CriterionEvaluation).join(Answer).where(Answer.submission_id == submission.id)).all()
    submission.total_score = sum(item.teacher_marks if item.teacher_marks is not None else item.ai_marks for item in evaluations)
    return submission.total_score


def create_exam(payload: ExamInput, teacher_id: str) -> dict:
    parsed_date = date.fromisoformat(payload.date) if payload.date else None
    with session() as db:
        if payload.class_id:
            owned_class(db, payload.class_id, teacher_id)
        exam = Exam(teacher_id=teacher_id, class_id=payload.class_id, title=payload.title, subject=payload.subject, date=parsed_date, total_marks=sum(c.max_marks for q in payload.questions for c in q.criteria))
        db.add(exam)
        db.flush()
        for question_input in payload.questions:
            question = Question(exam_id=exam.id, number=question_input.number, text=question_input.text, max_marks=sum(c.max_marks for c in question_input.criteria), concept_tags=[])
            db.add(question)
            db.flush()
            for index, criterion in enumerate(question_input.criteria, 1):
                db.add(RubricCriterion(question_id=question.id, code=f"C{index}", title=criterion.title, description=criterion.description, max_marks=criterion.max_marks, concept_tags=[criterion.concept]))
        db.commit()
        exam_id = exam.id
    return exam_detail(exam_id, teacher_id)


def unassigned_class(db, teacher_id: str) -> ClassCohort:
    cohort = db.scalar(select(ClassCohort).where(ClassCohort.teacher_id == teacher_id, ClassCohort.name == "Unassigned"))
    if not cohort:
        cohort = ClassCohort(teacher_id=teacher_id, name="Unassigned")
        db.add(cohort)
        db.flush()
    return cohort


def submission_summary(submission: Submission, student: Student, exam: Exam) -> dict:
    return {
        "id": submission.id,
        "exam_id": submission.exam_id,
        "student_id": submission.student_id,
        "status": submission.status.value,
        "total_score": submission.total_score,
        "created_at": submission.created_at,
        "error": submission.error,
        "archived_at": submission.archived_at,
        "student_name": student.name,
        "exam_title": exam.title,
        "class_id": exam.class_id,
    }


def clear_submission_results(db, submission_id: str) -> None:
    """Remove derived AI results before a retry or page replacement, retaining originals."""
    evaluations = db.scalars(select(CriterionEvaluation).join(Answer).where(Answer.submission_id == submission_id)).all()
    for evaluation in evaluations:
        for evidence in db.scalars(select(EvaluationEvidence).where(EvaluationEvidence.evaluation_id == evaluation.id)):
            db.delete(evidence)
        for review in db.scalars(select(ReviewSuggestion).where(ReviewSuggestion.evaluation_id == evaluation.id)):
            db.delete(review)
        for override in db.scalars(select(TeacherOverride).where(TeacherOverride.evaluation_id == evaluation.id)):
            db.delete(override)
        db.delete(evaluation)
    for answer in db.scalars(select(Answer).where(Answer.submission_id == submission_id)):
        for region in db.scalars(select(EvidenceRegion).where(EvidenceRegion.answer_id == answer.id)):
            db.delete(region)
        db.delete(answer)
    for artifact in db.scalars(select(AIArtifact).where(AIArtifact.submission_id == submission_id)):
        db.delete(artifact)
    submission = db.get(Submission, submission_id)
    if submission:
        submission.total_score = 0


def recalculate_submission_state(db, submission_id: str) -> SubmissionStatus:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(404, "Submission not found")
    unresolved = db.scalar(
        select(CriterionEvaluation.id)
        .join(Answer)
        .where(
            Answer.submission_id == submission_id,
            CriterionEvaluation.needs_review.is_(True),
            CriterionEvaluation.review_resolved.is_(False),
        )
        .limit(1)
    )
    status = SubmissionStatus.REVIEW_REQUIRED if unresolved else SubmissionStatus.COMPLETED
    submission.status = status
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.submission_id == submission_id))
    if job:
        job.stage = status
        job.error = None
    score_submission(db, submission)
    return status


def active_submission_rows(db, teacher_id: str):
    return (
        select(Submission, Student, Exam)
        .join(Student)
        .join(Exam)
        .join(ClassCohort, Student.class_id == ClassCohort.id)
        .where(
            Exam.teacher_id == teacher_id,
            Submission.archived_at.is_(None),
            Student.archived_at.is_(None),
            Exam.archived_at.is_(None),
            ClassCohort.archived_at.is_(None),
        )
    )


def delete_submission_data(db, submission: Submission) -> set[str]:
    """Delete a submission tree and return media paths eligible for cleanup."""
    pages = db.scalars(select(SubmissionPage).where(SubmissionPage.submission_id == submission.id)).all()
    paths = {path for page in pages for path in (page.original_key, page.processed_key) if path}
    clear_submission_results(db, submission.id)
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.submission_id == submission.id))
    if job:
        db.delete(job)
    for page in pages:
        db.delete(page)
    db.delete(submission)
    return paths


def remove_unreferenced_media(db, paths: set[str]) -> None:
    for value in paths:
        if db.scalar(select(SubmissionPage.id).where((SubmissionPage.original_key == value) | (SubmissionPage.processed_key == value)).limit(1)):
            continue
        path = Path(value)
        if path.is_file() and path.is_relative_to(UPLOADS):
            path.unlink(missing_ok=True)


async def process_submission(submission_id: str) -> None:
    set_processing_stage(submission_id, SubmissionStatus.PREPROCESSING, increment_attempts=True)
    try:
        if not settings.openai_enabled:
            raise RuntimeError("OPENAI_API_KEY is required for live Luna processing. Demo submissions remain available.")
        with session() as db:
            submission = db.get(Submission, submission_id)
            if not submission:
                return
            pages = db.scalars(select(SubmissionPage).where(SubmissionPage.submission_id == submission_id).order_by(SubmissionPage.page_number)).all()
            questions = db.scalars(select(Question).where(Question.exam_id == submission.exam_id).order_by(Question.number)).all()
            clear_submission_results(db, submission_id)
            db.commit()
        set_processing_stage(submission_id, SubmissionStatus.TRANSCRIBING)
        for page in pages:
            source_key = page.processed_key or page.original_key
            source_mime = "image/jpeg" if page.processed_key else page.mime_type
            image_hash = page.image_hash or hashlib.sha256(Path(source_key).read_bytes()).hexdigest()
            with session() as db:
                artifact = db.scalar(select(AIArtifact).where(AIArtifact.operation == "perception", AIArtifact.prompt_version == "perception_v1", AIArtifact.input_hash == image_hash).order_by(AIArtifact.created_at.desc()))
            perception = PerceptionResult.model_validate(artifact.output) if artifact else await perceive_page(source_key, source_mime, [q.number for q in questions])
            with session() as db:
                stored_page = db.get(SubmissionPage, page.id)
                # A legible page may still have uncertain words or a partial answer.
                # Only halt grading when perception explicitly says the page is unusable.
                unreadable = (
                    perception.requires_rescan
                    or perception.quality_status == "unreadable"
                )
                stored_page.quality_status = "rescan_required" if unreadable else perception.quality_status
                stored_page.quality_reason = perception.quality_reason or ("No reliable handwritten answers could be read from this page." if not perception.answers else None)
                stored_page.quality_confidence = perception.quality_confidence
                if not artifact:
                    db.add(AIArtifact(submission_id=submission_id, operation="perception", model=model_for("perception"), prompt_version="perception_v1", input_hash=image_hash, output=perception.model_dump()))
                for result_answer in perception.answers:
                    matched_question = next((q for q in questions if q.number == result_answer.question_id), None)
                    answer = Answer(submission_id=submission_id, question_id=matched_question.id if matched_question else None, page_id=page.id, transcription=result_answer.transcription, confidence=result_answer.confidence, uncertainty=[segment.model_dump() for segment in result_answer.uncertain_segments], prompt_version="perception_v1")
                    db.add(answer)
                    db.flush()
                    for region in result_answer.visual_regions:
                        db.add(EvidenceRegion(answer_id=answer.id, page_id=page.id, kind=region.kind, text=region.description, bbox={"coordinates": region.bbox}))
                    for region in result_answer.formula_regions:
                        db.add(EvidenceRegion(answer_id=answer.id, page_id=page.id, kind="formula", text=region.description, bbox={"coordinates": region.bbox}))
                db.commit()
            if unreadable:
                # Keep the submission in an existing persisted state. Page-level
                # quality carries the rescan requirement without a DB enum migration.
                set_processing_stage(submission_id, SubmissionStatus.REVIEW_REQUIRED, "A page is too unclear to grade reliably. Replace the affected scan and retry.")
                return
        set_processing_stage(submission_id, SubmissionStatus.GRADING)
        for question in questions:
            with session() as db:
                mapped_answers = db.scalars(select(Answer).join(SubmissionPage).where(Answer.submission_id == submission_id, Answer.question_id == question.id).order_by(SubmissionPage.page_number, Answer.id)).all()
                criteria = db.scalars(select(RubricCriterion).where(RubricCriterion.question_id == question.id).order_by(RubricCriterion.code)).all()
                page = db.get(SubmissionPage, mapped_answers[0].page_id) if mapped_answers else None
            if not mapped_answers or not page:
                continue
            transcription = "\n\n".join(answer.transcription for answer in mapped_answers)
            for criterion in criteria:
                result = await grade_criterion(page.processed_key or page.original_key, "image/jpeg" if page.processed_key else page.mime_type, question.text, criterion_data(criterion), transcription)
                with session() as db:
                    requires_review = result.needs_review or result.confidence < REVIEW_THRESHOLD or any(answer.uncertainty or (answer.confidence or 0) < REVIEW_THRESHOLD for answer in mapped_answers)
                    evaluation = CriterionEvaluation(answer_id=mapped_answers[0].id, criterion_id=criterion.id, ai_marks=min(criterion.max_marks, max(0, result.awarded_marks)), reason=result.reason, confidence=result.confidence, needs_review=requires_review, review_resolved=not requires_review)
                    db.add(evaluation)
                    db.flush()
                    for quote in result.evidence_quotes:
                        db.add(EvaluationEvidence(evaluation_id=evaluation.id, page_id=page.id, quote=quote))
                    db.commit()
        with session() as db:
            submission = db.get(Submission, submission_id)
            review_needed = db.scalar(select(CriterionEvaluation.id).join(Answer).where(Answer.submission_id == submission_id, CriterionEvaluation.needs_review.is_(True), CriterionEvaluation.review_resolved.is_(False)).limit(1)) is not None
            score_submission(db, submission)
            db.commit()
        set_processing_stage(submission_id, SubmissionStatus.REVIEW_REQUIRED if review_needed else SubmissionStatus.COMPLETED)
    except Exception as exc:
        set_processing_stage(submission_id, SubmissionStatus.FAILED, str(exc))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_storage()
    if settings.demo_mode:
        seed_demo_accounts(settings)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_origin_regex=r"http://localhost:\d+", allow_methods=["*"], allow_headers=["*"], allow_credentials=True)


@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    if request.method in {"GET", "HEAD", "OPTIONS"} or request.url.path in {"/api/auth/login", "/api/auth/bootstrap", "/api/health", "/api/health/ready"}:
        return await call_next(request)
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origin_list:
        return Response(status_code=403, content='{"detail":"Untrusted request origin."}', media_type="application/json")
    if request.headers.get("sec-fetch-site") == "cross-site":
        return Response(status_code=403, content='{"detail":"Cross-site requests are not allowed."}', media_type="application/json")
    return await call_next(request)


@app.get("/api/health")
def health(): return {"status": "ok", "model": MODEL, "ai_enabled": settings.openai_enabled}


@app.get("/api/health/ready")
def readiness():
    try:
        with session() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(503, "Database is unavailable.") from exc


@app.post("/api/auth/bootstrap", status_code=201)
def bootstrap_teacher(payload: TeacherCredentials, response: Response, bootstrap_token: str | None = Header(default=None, alias="X-Bootstrap-Token")):
    if settings.app_env == "production":
        if not settings.enable_http_bootstrap:
            raise HTTPException(403, "HTTP bootstrap is disabled.")
        if not settings.bootstrap_token or not bootstrap_token or token_hash(bootstrap_token) != token_hash(settings.bootstrap_token.get_secret_value()):
            raise HTTPException(403, "Invalid bootstrap token.")
    if not payload.name: raise HTTPException(422, "A teacher name is required.")
    with session() as db:
        if db.scalar(select(Teacher.id).limit(1)): raise HTTPException(403, "Teacher setup is already complete. Sign in instead.")
        teacher = Teacher(name=payload.name.strip(), email=payload.email.strip().lower(), password_hash=hash_password(payload.password))
        db.add(teacher); db.flush()
        account = Account(email=teacher.email, password_hash=teacher.password_hash, role=AccountRole.TEACHER, teacher_id=teacher.id)
        db.add(account); db.commit()
        result = {"id": teacher.id, "name": teacher.name, "email": teacher.email, "role": account.role.value}
    set_session(response, account)
    return result


@app.post("/api/auth/login")
def login(payload: TeacherCredentials, response: Response):
    with session() as db:
        account = db.scalar(select(Account).where(Account.email == payload.email.strip().lower()))
        if not account or not verify_password(payload.password, account.password_hash): raise HTTPException(401, "Invalid email or password.")
        if account.role == AccountRole.TEACHER:
            identity = db.get(Teacher, account.teacher_id)
        else:
            identity = db.get(Student, account.student_id)
        if not identity: raise HTTPException(401, "Invalid account.")
        result = {"id": identity.id, "name": identity.name, "email": account.email, "role": account.role.value}
    set_session(response, account); return result


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response, session_token: str | None = Cookie(default=None, alias="prism_session")):
    if session_token:
        with session() as db:
            active_session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(session_token), AuthSession.revoked_at.is_(None)))
            if active_session:
                active_session.revoked_at = datetime.now(timezone.utc)
                db.commit()
    response.delete_cookie("prism_session", path="/")
    response.delete_cookie("prism_csrf", path="/")


@app.get("/api/auth/me")
def me(account: dict = Depends(current_account)):
    if account["role"] == AccountRole.TEACHER.value:
        return current_teacher(account)
    return current_student(account)


@app.get("/api/dashboard")
def dashboard(teacher: dict = Depends(current_teacher)):
    with session() as db:
        exams = db.scalars(select(Exam).where(Exam.teacher_id == teacher["id"], Exam.archived_at.is_(None)).order_by(Exam.created_at.desc())).all()
        pending = db.scalar(select(func.count()).select_from(CriterionEvaluation).join(Answer).join(Submission).join(Student).join(ClassCohort, Student.class_id == ClassCohort.id).join(Exam).where(Exam.teacher_id == teacher["id"], Submission.archived_at.is_(None), Student.archived_at.is_(None), ClassCohort.archived_at.is_(None), Exam.archived_at.is_(None), CriterionEvaluation.needs_review.is_(True), CriterionEvaluation.review_resolved.is_(False))) or 0
        rows = db.execute(active_submission_rows(db, teacher["id"]).order_by(Submission.created_at.desc()).limit(8)).all()
        return {"exams": [{"id": e.id, "title": e.title, "subject": e.subject, "date": e.date, "created_at": e.created_at, "teacher_id": e.teacher_id, "class_id": e.class_id} for e in exams], "pending_reviews": pending, "submissions": [submission_summary(s, st, ex) for s, st, ex in rows]}


@app.post("/api/exams")
def post_exam(payload: ExamInput, teacher: dict = Depends(current_teacher)): return create_exam(payload, teacher["id"])


@app.get("/api/classes")
def get_classes(include_archived: bool = False, teacher: dict = Depends(current_teacher)):
    with session() as db:
        statement = select(ClassCohort).where(ClassCohort.teacher_id == teacher["id"])
        if not include_archived:
            statement = statement.where(ClassCohort.archived_at.is_(None))
        cohorts = db.scalars(statement.order_by(ClassCohort.name)).all()
        return [{"id": cohort.id, "name": cohort.name, "archived_at": cohort.archived_at, "student_count": db.scalar(select(func.count()).select_from(Student).where(Student.class_id == cohort.id, Student.archived_at.is_(None))) or 0} for cohort in cohorts]


@app.post("/api/classes", status_code=201)
def create_class(payload: ClassInput, teacher: dict = Depends(current_teacher)):
    with session() as db:
        cohort = ClassCohort(teacher_id=teacher["id"], name=payload.name.strip())
        db.add(cohort)
        db.commit()
        return {"id": cohort.id, "name": cohort.name, "student_count": 0}


@app.get("/api/classes/{class_id}")
def get_class(class_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        cohort = owned_class(db, class_id, teacher["id"])
        primary_students = db.scalars(select(Student).where(Student.class_id == cohort.id, Student.archived_at.is_(None))).all()
        member_students = db.scalars(select(Student).join(ClassMembership).where(ClassMembership.class_id == cohort.id, Student.archived_at.is_(None))).all()
        students = sorted({student.id: student for student in [*primary_students, *member_students]}.values(), key=lambda student: student.name)
        exams = db.scalars(select(Exam).where(Exam.class_id == cohort.id, Exam.archived_at.is_(None)).order_by(Exam.created_at.desc())).all()
        return {"id": cohort.id, "name": cohort.name, "archived_at": cohort.archived_at, "students": [{"id": student.id, "name": student.name, "identifier": student.identifier} for student in students], "exams": [{"id": exam.id, "title": exam.title, "subject": exam.subject, "total_marks": exam.total_marks} for exam in exams]}


@app.patch("/api/classes/{class_id}")
def update_class(class_id: str, payload: ClassInput, teacher: dict = Depends(current_teacher)):
    with session() as db:
        cohort = owned_class(db, class_id, teacher["id"])
        cohort.name = payload.name.strip()
        db.commit()
    return {"id": class_id, "name": payload.name.strip()}


@app.patch("/api/classes/{class_id}/archive")
def archive_class(class_id: str, archived: bool = True, teacher: dict = Depends(current_teacher)):
    with session() as db:
        cohort = owned_class(db, class_id, teacher["id"])
        cohort.archived_at = datetime.now(timezone.utc) if archived else None
        db.commit()
    return {"id": class_id, "archived": archived}


@app.delete("/api/classes/{class_id}")
def delete_class(class_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        cohort = owned_class(db, class_id, teacher["id"])
        if db.scalar(select(Exam.id).where(Exam.class_id == cohort.id).limit(1)):
            raise HTTPException(409, "Delete or reassign this class's exams before deleting the class.")
        if db.scalar(select(Student.id).where(Student.class_id == cohort.id).limit(1)):
            raise HTTPException(409, "Move or delete the class's students before deleting the class.")
        for membership in db.scalars(select(ClassMembership).where(ClassMembership.class_id == cohort.id)):
            db.delete(membership)
        db.delete(cohort)
        db.commit()
    return {"id": class_id, "deleted": True}


@app.post("/api/classes/{class_id}/students", status_code=201)
def create_student(class_id: str, payload: StudentInput, teacher: dict = Depends(current_teacher)):
    with session() as db:
        owned_class(db, class_id, teacher["id"])
        existing = db.scalar(select(Student).where(Student.class_id == class_id, Student.identifier == payload.identifier.strip()))
        if existing:
            raise HTTPException(409, "A student with this identifier already exists in the class.")
        student = Student(class_id=class_id, name=payload.name.strip(), identifier=payload.identifier.strip())
        db.add(student)
        db.commit()
        return {"id": student.id, "name": student.name, "identifier": student.identifier}


@app.get("/api/students")
def get_students(q: str = "", teacher: dict = Depends(current_teacher)):
    with session() as db:
        statement = select(Student, ClassCohort).join(ClassCohort).where(ClassCohort.teacher_id == teacher["id"], Student.archived_at.is_(None), ClassCohort.archived_at.is_(None))
        if q.strip():
            like = f"%{q.strip()}%"
            statement = statement.where((Student.name.ilike(like)) | (Student.identifier.ilike(like)))
        return [{"id": student.id, "name": student.name, "identifier": student.identifier, "class_id": cohort.id, "class_name": cohort.name} for student, cohort in db.execute(statement.order_by(Student.name).limit(20)).all()]


@app.post("/api/classes/{class_id}/memberships", status_code=201)
def add_existing_student_to_class(class_id: str, payload: StudentAssignmentInput, teacher: dict = Depends(current_teacher)):
    with session() as db:
        cohort = owned_class(db, class_id, teacher["id"])
        student = db.scalar(select(Student).join(ClassCohort).where(Student.id == payload.student_id, ClassCohort.teacher_id == teacher["id"], Student.archived_at.is_(None)))
        if not student:
            raise HTTPException(404, "Student not found")
        if db.scalar(select(ClassMembership.id).where(ClassMembership.class_id == cohort.id, ClassMembership.student_id == student.id)):
            raise HTTPException(409, "Student is already in this class.")
        db.add(ClassMembership(class_id=cohort.id, student_id=student.id))
        db.commit()
        return {"class_id": cohort.id, "student": {"id": student.id, "name": student.name, "identifier": student.identifier}}


@app.post("/api/classes/{class_id}/students/import", status_code=201)
def import_students(class_id: str, payload: RosterInput, teacher: dict = Depends(current_teacher)):
    created = []
    with session() as db:
        owned_class(db, class_id, teacher["id"])
        identifiers = [student.identifier.strip() for student in payload.students]
        if len(identifiers) != len(set(identifiers)):
            raise HTTPException(422, "Each roster identifier must be unique.")
        existing = set(db.scalars(select(Student.identifier).where(Student.class_id == class_id, Student.identifier.in_(identifiers))).all())
        if existing:
            raise HTTPException(409, f"These identifiers already exist: {', '.join(sorted(existing))}")
        for item in payload.students:
            student = Student(class_id=class_id, name=item.name.strip(), identifier=item.identifier.strip())
            db.add(student)
            created.append(student)
        db.commit()
        return {"created": [{"id": student.id, "name": student.name, "identifier": student.identifier} for student in created]}


@app.patch("/api/students/{student_id}/archive")
def archive_student(student_id: str, archived: bool = True, teacher: dict = Depends(current_teacher)):
    with session() as db:
        student = db.scalar(select(Student).join(ClassCohort).where(Student.id == student_id, ClassCohort.teacher_id == teacher["id"]))
        if not student:
            raise HTTPException(404, "Student not found")
        student.archived_at = datetime.now(timezone.utc) if archived else None
        db.commit()
    return {"id": student_id, "archived": archived}


@app.delete("/api/students/{student_id}")
def delete_student(student_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        student = db.scalar(select(Student).join(ClassCohort).where(Student.id == student_id, ClassCohort.teacher_id == teacher["id"]))
        if not student:
            raise HTTPException(404, "Student not found")
        paths: set[str] = set()
        for submission in db.scalars(select(Submission).where(Submission.student_id == student.id)).all():
            paths.update(delete_submission_data(db, submission))
        for membership in db.scalars(select(ClassMembership).where(ClassMembership.student_id == student.id)):
            db.delete(membership)
        account = db.scalar(select(Account).where(Account.student_id == student.id))
        if account:
            for auth in db.scalars(select(AuthSession).where(AuthSession.account_id == account.id)):
                db.delete(auth)
            db.delete(account)
        db.delete(student)
        db.commit()
        remove_unreferenced_media(db, paths)
        db.commit()
    return {"id": student_id, "deleted": True}


@app.post("/api/exam-drafts/import")
async def import_exam_draft(file: UploadFile = File(...), teacher: dict = Depends(current_teacher)):
    if not settings.openai_enabled:
        raise HTTPException(503, "OPENAI_API_KEY is required to import a question paper.")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Upload a JPEG, PNG, or PDF question paper.")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "The uploaded question paper is empty.")
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Files must be smaller than {settings.max_upload_mb} MB.")
    extension = {"image/jpeg": ".jpg", "image/png": ".png", "application/pdf": ".pdf"}[file.content_type]
    path = UPLOADS / f"exam-draft-{uuid.uuid4()}{extension}"
    path.write_bytes(contents)
    pages = normalize_pages(path, file.content_type)
    image_hash = hashlib.sha256(contents).hexdigest()
    with session() as db:
        artifact = db.scalar(select(AIArtifact).where(
            AIArtifact.operation == "exam_import",
            AIArtifact.prompt_version == EXAM_IMPORT_VERSION,
            AIArtifact.input_hash == image_hash,
        ).order_by(AIArtifact.created_at.desc()))
    if artifact:
        return {**artifact.output, "cached": True}
    result = await import_exam_pages([(page["processed_key"], "image/jpeg") for page in pages])
    draft = imported_draft(result)
    with session() as db:
        db.add(AIArtifact(
            operation="exam_import",
            model=model_for("exam_import"),
            prompt_version=EXAM_IMPORT_VERSION,
            input_hash=image_hash,
            output=draft,
        ))
        db.commit()
    return {**draft, "cached": False}


@app.get("/api/exams")
def get_exams(include_archived: bool = False, teacher: dict = Depends(current_teacher)):
    with session() as db:
        statement = select(Exam.id).where(Exam.teacher_id == teacher["id"])
        if not include_archived:
            statement = statement.where(Exam.archived_at.is_(None))
        ids = db.scalars(statement.order_by(Exam.created_at.desc())).all()
    return [exam_detail(exam_id, teacher["id"]) for exam_id in ids]


@app.get("/api/exams/{exam_id}")
def get_exam(exam_id: str, teacher: dict = Depends(current_teacher)): return exam_detail(exam_id, teacher["id"])


@app.patch("/api/exams/{exam_id}/archive")
def archive_exam(exam_id: str, archived: bool = True, teacher: dict = Depends(current_teacher)):
    with session() as db:
        exam = owned_exam(db, exam_id, teacher["id"])
        exam.archived_at = datetime.now(timezone.utc) if archived else None
        db.commit()
    return {"id": exam_id, "archived": archived}


@app.delete("/api/exams/{exam_id}")
def delete_exam(exam_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        exam = owned_exam(db, exam_id, teacher["id"])
        paths: set[str] = set()
        for submission in db.scalars(select(Submission).where(Submission.exam_id == exam.id)).all():
            paths.update(delete_submission_data(db, submission))
        for criterion in db.scalars(select(RubricCriterion).join(Question).where(Question.exam_id == exam.id)):
            db.delete(criterion)
        for question in db.scalars(select(Question).where(Question.exam_id == exam.id)):
            db.delete(question)
        db.delete(exam)
        db.commit()
        remove_unreferenced_media(db, paths)
        db.commit()
    return {"id": exam_id, "deleted": True}


@app.get("/api/submissions")
def get_submissions(exam_id: str | None = None, class_id: str | None = None, student_id: str | None = None, include_archived: bool = False, teacher: dict = Depends(current_teacher)):
    with session() as db:
        statement = active_submission_rows(db, teacher["id"])
        if exam_id:
            statement = statement.where(Submission.exam_id == exam_id)
        if class_id:
            statement = statement.where(Student.class_id == class_id)
        if isinstance(student_id, str) and student_id:
            statement = statement.where(Submission.student_id == student_id)
        if include_archived:
            statement = select(Submission, Student, Exam).join(Student).join(Exam).where(Exam.teacher_id == teacher["id"])
        return [submission_summary(submission, student, exam) for submission, student, exam in db.execute(statement.order_by(Submission.created_at.desc())).all()]


@app.post("/api/exams/{exam_id}/submissions")
async def upload_submission(background_tasks: BackgroundTasks, exam_id: str, student_name: str = Form(""), file: UploadFile | None = File(None), pages: list[UploadFile] | None = File(None), student_id: str | None = Form(None), teacher: dict = Depends(current_teacher)):
    uploads = pages if isinstance(pages, list) else ([file] if isinstance(file, UploadFile) else [])
    if not uploads:
        raise HTTPException(422, "Upload one PDF or at least one image page.")
    if len(uploads) > settings.max_submission_pages:
        raise HTTPException(422, f"Submissions may contain up to {settings.max_submission_pages} pages.")
    if any(upload.content_type not in ALLOWED_TYPES for upload in uploads):
        raise HTTPException(415, "Upload JPEG, PNG, or PDF files only.")
    if len(uploads) > 1 and any(upload.content_type == "application/pdf" for upload in uploads):
        raise HTTPException(422, "Upload one PDF or ordered image pages, not both.")
    payloads = [(upload, await upload.read()) for upload in uploads]
    if any(not contents for _, contents in payloads):
        raise HTTPException(400, "An uploaded page is empty.")
    if sum(len(contents) for _, contents in payloads) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"All pages together must be smaller than {settings.max_upload_mb} MB.")
    with session() as db:
        exam = owned_exam(db, exam_id, teacher["id"])
    source_hash = hashlib.sha256(b"".join(hashlib.sha256(contents).digest() for _, contents in payloads)).hexdigest()
    normalized_pages: list[dict] = []
    for upload, contents in payloads:
        extension = {"image/jpeg": ".jpg", "image/png": ".png", "application/pdf": ".pdf"}[upload.content_type]
        path = UPLOADS / f"{uuid.uuid4()}{extension}"
        path.write_bytes(contents)
        for page in normalize_pages(path, upload.content_type):
            normalized_pages.append({**page, "original_key": str(path), "mime_type": upload.content_type})
    if len(normalized_pages) > settings.max_submission_pages:
        raise HTTPException(422, f"Submissions may contain up to {settings.max_submission_pages} pages.")
    with session() as db:
        if isinstance(student_id, str) and student_id:
            student = db.scalar(select(Student).join(ClassCohort).where(Student.id == student_id, ClassCohort.teacher_id == teacher["id"], Student.archived_at.is_(None)))
            if not student:
                raise HTTPException(404, "Student not found in your active roster.")
            if exam.class_id and student.class_id != exam.class_id:
                raise HTTPException(422, "Choose a student from the exam class.")
        else:
            if not student_name.strip():
                raise HTTPException(422, "Choose a roster student or provide a student name.")
            cohort = db.get(ClassCohort, exam.class_id) if exam.class_id else unassigned_class(db, teacher["id"])
            student = db.scalar(select(Student).where(Student.class_id == cohort.id, Student.name == student_name.strip()))
            if not student:
                student = Student(class_id=cohort.id, name=student_name.strip(), identifier=f"UP-{uuid.uuid4().hex[:6]}"); db.add(student); db.flush()
        duplicate = db.scalar(select(Submission).where(Submission.exam_id == exam_id, Submission.student_id == student.id, Submission.source_hash == source_hash).order_by(Submission.created_at.desc()))
        if duplicate:
            return {"id": duplicate.id, "status": duplicate.status.value, "student_name": student.name, "page_count": db.scalar(select(func.count()).select_from(SubmissionPage).where(SubmissionPage.submission_id == duplicate.id)), "duplicate": True}
        submission = Submission(exam_id=exam_id, student_id=student.id, status=SubmissionStatus.UPLOADED, source_hash=source_hash)
        db.add(submission); db.flush(); db.add(ProcessingJob(submission_id=submission.id, stage=SubmissionStatus.UPLOADED))
        for page_number, page in enumerate(normalized_pages, 1):
            db.add(SubmissionPage(submission_id=submission.id, page_number=page_number, original_key=page["original_key"], mime_type=page["mime_type"], **{key: page[key] for key in ("processed_key", "width", "height", "image_hash")}))
        db.commit(); submission_id = submission.id
    background_tasks.add_task(process_submission, submission_id)
    return {"id": submission_id, "status": "uploaded", "student_name": student.name, "page_count": len(normalized_pages), "duplicate": False}


@app.post("/api/submissions/{submission_id}/process")
async def start_processing(submission_id: str, background_tasks: BackgroundTasks, teacher: dict = Depends(current_teacher)):
    with session() as db:
        submission = owned_submission(db, submission_id, teacher["id"])
        if submission.status in {SubmissionStatus.PREPROCESSING, SubmissionStatus.TRANSCRIBING, SubmissionStatus.GRADING}: raise HTTPException(409, "Submission processing is already in progress.")
    background_tasks.add_task(process_submission, submission_id); return {"id": submission_id, "status": "queued"}


@app.post("/api/submissions/{submission_id}/retry")
async def retry_processing(submission_id: str, background_tasks: BackgroundTasks, teacher: dict = Depends(current_teacher)):
    with session() as db:
        submission = owned_submission(db, submission_id, teacher["id"])
        if submission.status not in {SubmissionStatus.FAILED, SubmissionStatus.REVIEW_REQUIRED, SubmissionStatus.COMPLETED, SubmissionStatus.RESCAN_REQUIRED}: raise HTTPException(409, "Only finished or failed submissions can be retried.")
    background_tasks.add_task(process_submission, submission_id); return {"id": submission_id, "status": "queued"}


@app.get("/api/submissions/{submission_id}/status")
def processing_status(submission_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        owned_submission(db, submission_id, teacher["id"]); job = db.scalar(select(ProcessingJob).where(ProcessingJob.submission_id == submission_id))
        if not job: raise HTTPException(404, "Processing job not found")
        return {"stage": job.stage.value, "attempts": job.attempts, "error": job.error, "updated_at": job.updated_at}


@app.get("/api/submissions/{submission_id}")
def get_submission(submission_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        submission = owned_submission(db, submission_id, teacher["id"]); student = db.get(Student, submission.student_id); exam = db.get(Exam, submission.exam_id)
        pages = [{"id": p.id, "page_number": p.page_number, "width": p.width, "height": p.height, "preview_url": f"/api/pages/{p.id}/preview", "original_url": f"/api/pages/{p.id}", "quality_status": p.quality_status, "quality_reason": p.quality_reason, "quality_confidence": p.quality_confidence} for p in db.scalars(select(SubmissionPage).where(SubmissionPage.submission_id == submission_id).order_by(SubmissionPage.page_number))]
        answers = []
        for answer in db.scalars(select(Answer).where(Answer.submission_id == submission_id)):
            regions = db.scalars(select(EvidenceRegion).where(EvidenceRegion.answer_id == answer.id)).all()
            region_data = lambda region: {"kind": region.kind, "description": region.text, "bbox": (region.bbox or {}).get("coordinates")}
            answers.append({"id": answer.id, "question_id": answer.question_id, "page_id": answer.page_id, "transcription": answer.transcription, "uncertainty": answer.uncertainty, "prompt_version": answer.prompt_version, "confidence": answer.confidence, "visual_regions": [region_data(region) for region in regions if region.kind != "formula"], "formula_regions": [region_data(region) for region in regions if region.kind == "formula"]})
        evaluations = []
        for ev, criterion, question in db.execute(select(CriterionEvaluation, RubricCriterion, Question).select_from(CriterionEvaluation).join(RubricCriterion, CriterionEvaluation.criterion_id == RubricCriterion.id).join(Question, RubricCriterion.question_id == Question.id).join(Answer, CriterionEvaluation.answer_id == Answer.id).where(Answer.submission_id == submission_id).order_by(Question.number)):
            pending = db.scalar(select(ReviewSuggestion).where(ReviewSuggestion.evaluation_id == ev.id, ReviewSuggestion.status == "pending").order_by(ReviewSuggestion.created_at.desc()))
            evaluations.append({"id": ev.id, "ai_marks": ev.ai_marks, "teacher_marks": ev.teacher_marks, "reason": ev.reason, "confidence": ev.confidence, "needs_review": ev.needs_review, "review_resolved": ev.review_resolved, "review_resolution": ev.review_resolution, "criterion_title": criterion.title, "criterion_description": criterion.description, "max_marks": criterion.max_marks, "concept": criterion.concept_tags[0] if criterion.concept_tags else "Uncategorized", "question_id": question.id, "question_number": question.number, "question_text": question.text, "evidence": [{"page_id": evidence.page_id, "page": p.page_number if (p := db.get(SubmissionPage, evidence.page_id)) else None, "quote": evidence.quote} for evidence in db.scalars(select(EvaluationEvidence).where(EvaluationEvidence.evaluation_id == ev.id))], "pending_review": {"id": pending.id, "suggested_marks": pending.suggested_marks, "reason": pending.reason, "confidence": pending.confidence} if pending else None, "effective_marks": ev.teacher_marks if ev.teacher_marks is not None else ev.ai_marks})
        return {"id": submission.id, "exam_id": submission.exam_id, "student_id": submission.student_id, "status": submission.status.value, "total_score": submission.total_score, "created_at": submission.created_at, "error": submission.error, "student_name": student.name, "exam_title": exam.title, "pages": pages, "answers": answers, "evaluations": evaluations}


def student_result(db, submission: Submission) -> dict:
    exam = db.get(Exam, submission.exam_id)
    evaluations = []
    for ev, criterion, question in db.execute(select(CriterionEvaluation, RubricCriterion, Question).select_from(CriterionEvaluation).join(RubricCriterion, CriterionEvaluation.criterion_id == RubricCriterion.id).join(Question, RubricCriterion.question_id == Question.id).join(Answer, CriterionEvaluation.answer_id == Answer.id).where(Answer.submission_id == submission.id).order_by(Question.number)):
        evaluations.append({"id": ev.id, "question_number": question.number, "criterion_title": criterion.title, "max_marks": criterion.max_marks, "marks": ev.teacher_marks if ev.teacher_marks is not None else ev.ai_marks, "reason": ev.reason, "confidence": ev.confidence, "needs_review": ev.needs_review, "evidence": [{"page": page.page_number if (page := db.get(SubmissionPage, evidence.page_id)) else None, "quote": evidence.quote} for evidence in db.scalars(select(EvaluationEvidence).where(EvaluationEvidence.evaluation_id == ev.id))]})
    return {"id": submission.id, "exam_id": submission.exam_id, "exam_title": exam.title, "subject": exam.subject, "status": submission.status.value, "total_score": submission.total_score, "created_at": submission.created_at, "evaluations": evaluations}


@app.get("/api/student/submissions")
def own_submissions(student: dict = Depends(current_student)):
    with session() as db:
        submissions = db.scalars(select(Submission).where(Submission.student_id == student["id"]).order_by(Submission.created_at.desc())).all()
        return [student_result(db, submission) for submission in submissions]


@app.get("/api/student/submissions/{submission_id}")
def own_submission(submission_id: str, student: dict = Depends(current_student)):
    with session() as db:
        submission = db.scalar(select(Submission).where(Submission.id == submission_id, Submission.student_id == student["id"]))
        if not submission: raise HTTPException(404, "Submission not found")
        return student_result(db, submission)


@app.get("/api/pages/{page_id}")
def get_page(page_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        page = db.scalar(select(SubmissionPage).join(Submission).join(Exam).where(SubmissionPage.id == page_id, Exam.teacher_id == teacher["id"]))
        if not page or not Path(page.original_key).is_file(): raise HTTPException(404, "Original page not found")
        return FileResponse(page.original_key, media_type=page.mime_type, filename=Path(page.original_key).name)


@app.get("/api/pages/{page_id}/preview")
def get_page_preview(page_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        page = db.scalar(select(SubmissionPage).join(Submission).join(Exam).where(SubmissionPage.id == page_id, Exam.teacher_id == teacher["id"]))
        if not page:
            raise HTTPException(404, "Page not found")
        preview = page_preview_path(page)
        if preview:
            db.commit()
            return FileResponse(preview, media_type="image/jpeg" if page.processed_key else page.mime_type)
        return Response(content=unavailable_preview(), media_type="image/jpeg", headers={"X-PRISM-Preview": "unavailable"})


@app.patch("/api/submissions/{submission_id}/archive")
def archive_submission(submission_id: str, archived: bool = True, teacher: dict = Depends(current_teacher)):
    with session() as db:
        submission = owned_submission(db, submission_id, teacher["id"])
        paths = delete_submission_data(db, submission)
        db.commit()
        remove_unreferenced_media(db, paths)
        db.commit()
    return {"id": submission_id, "deleted": True}


@app.delete("/api/submissions/{submission_id}")
def delete_submission(submission_id: str, teacher: dict = Depends(current_teacher)):
    return archive_submission(submission_id, teacher=teacher)


@app.patch("/api/submissions/{submission_id}/student")
def reassign_submission_student(submission_id: str, payload: StudentAssignmentInput, teacher: dict = Depends(current_teacher)):
    with session() as db:
        submission = active_owned_submission(db, submission_id, teacher["id"])
        exam = db.get(Exam, submission.exam_id)
        student = db.scalar(select(Student).join(ClassCohort).where(Student.id == payload.student_id, ClassCohort.teacher_id == teacher["id"], Student.archived_at.is_(None)))
        if not student:
            raise HTTPException(404, "Student not found")
        if exam.class_id and not db.scalar(select(ClassMembership.id).where(ClassMembership.class_id == exam.class_id, ClassMembership.student_id == student.id)) and student.class_id != exam.class_id:
            raise HTTPException(422, "Student is not enrolled in the exam class.")
        if db.scalar(select(Submission.id).where(Submission.exam_id == exam.id, Submission.student_id == student.id, Submission.id != submission.id, Submission.archived_at.is_(None)).limit(1)):
            raise HTTPException(409, "This student already has an active paper for this exam.")
        submission.student_id = student.id
        db.commit()
    return {"id": submission_id, "student": {"id": student.id, "name": student.name, "identifier": student.identifier}}


@app.put("/api/submissions/{submission_id}/pages/{page_id}")
async def replace_submission_page(submission_id: str, page_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), teacher: dict = Depends(current_teacher)):
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(415, "Rescan replacement must be a JPEG or PNG image.")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "The replacement page is empty.")
    path = UPLOADS / f"rescan-{uuid.uuid4()}{'.jpg' if file.content_type == 'image/jpeg' else '.png'}"
    path.write_bytes(contents)
    normalized = normalize_pages(path, file.content_type)
    if len(normalized) != 1:
        raise HTTPException(422, "Replace one page with one image.")
    with session() as db:
        submission = owned_submission(db, submission_id, teacher["id"])
        page = db.scalar(select(SubmissionPage).where(SubmissionPage.id == page_id, SubmissionPage.submission_id == submission.id))
        if not page:
            raise HTTPException(404, "Submission page not found")
        clear_submission_results(db, submission_id)
        page.original_key = str(path)
        page.mime_type = file.content_type
        page.processed_key = normalized[0]["processed_key"]
        page.image_hash = normalized[0]["image_hash"]
        page.width = normalized[0]["width"]
        page.height = normalized[0]["height"]
        page.quality_status = "pending"
        page.quality_reason = None
        page.quality_confidence = None
        submission.total_score = 0
        submission.status = SubmissionStatus.UPLOADED
        db.commit()
    background_tasks.add_task(process_submission, submission_id)
    return {"id": submission_id, "status": "queued", "replaced_page_id": page_id}


@app.post("/api/evaluations/{evaluation_id}/review")
async def request_review(evaluation_id: str, payload: ReviewInput, teacher: dict = Depends(current_teacher)):
    if not settings.openai_enabled: raise HTTPException(503, "OPENAI_API_KEY is required for criterion re-evaluation.")
    with session() as db:
        evaluation = owned_evaluation(db, evaluation_id, teacher["id"]); answer = db.get(Answer, evaluation.answer_id); page = db.get(SubmissionPage, answer.page_id); criterion = db.get(RubricCriterion, evaluation.criterion_id); question = db.get(Question, criterion.question_id)
        if db.scalar(select(ReviewSuggestion.id).where(ReviewSuggestion.evaluation_id == evaluation.id, ReviewSuggestion.status == "pending").limit(1)):
            raise HTTPException(409, "A PRISM suggestion is already awaiting your decision.")
        current_marks = evaluation.teacher_marks if evaluation.teacher_marks is not None else evaluation.ai_marks
        result = await review_criterion(page.processed_key or page.original_key, "image/jpeg" if page.processed_key else page.mime_type, question.text, criterion_data(criterion), answer.transcription, current_marks, evaluation.reason, payload.comment)
        review = ReviewSuggestion(evaluation_id=evaluation.id, requested_by_teacher_id=teacher["id"], comment=payload.comment, suggested_marks=min(criterion.max_marks, max(0, result.suggested_marks)), reason=result.reason, evidence_quotes=result.evidence_quotes, confidence=result.confidence)
        db.add(review); db.commit()
        return {"id": review.id, "previous_marks": current_marks, "suggested_marks": review.suggested_marks, "reason": review.reason, "evidence": review.evidence_quotes, "confidence": review.confidence, "status": review.status}


@app.post("/api/reviews/{review_id}/{decision}")
def decide_review(review_id: str, decision: Literal["accept", "reject"], teacher: dict = Depends(current_teacher)):
    with session() as db:
        review = owned_review(db, review_id, teacher["id"])
        if review.status != "pending": raise HTTPException(404, "Pending review not found")
        evaluation = db.get(CriterionEvaluation, review.evaluation_id)
        if decision == "accept":
            previous = evaluation.teacher_marks if evaluation.teacher_marks is not None else evaluation.ai_marks; evaluation.teacher_marks = review.suggested_marks
            db.add(TeacherOverride(evaluation_id=evaluation.id, teacher_id=teacher["id"], previous_marks=previous, new_marks=review.suggested_marks, reason=review.reason))
        evaluation.review_resolved = True
        evaluation.review_resolution = decision
        evaluation.reviewed_at = datetime.now(timezone.utc)
        review.status = decision
        for other in db.scalars(select(ReviewSuggestion).where(ReviewSuggestion.evaluation_id == evaluation.id, ReviewSuggestion.status == "pending", ReviewSuggestion.id != review.id)):
            other.status = "superseded"
        submission_id = db.get(Answer, evaluation.answer_id).submission_id
        status = recalculate_submission_state(db, submission_id)
        db.commit()
    return {"status": decision, "submission_status": status.value}


@app.patch("/api/evaluations/{evaluation_id}")
def override(evaluation_id: str, payload: OverrideInput, teacher: dict = Depends(current_teacher)):
    with session() as db:
        evaluation = owned_evaluation(db, evaluation_id, teacher["id"]); criterion = db.get(RubricCriterion, evaluation.criterion_id)
        if payload.marks > criterion.max_marks: raise HTTPException(422, "Marks cannot exceed the criterion maximum.")
        previous = evaluation.teacher_marks if evaluation.teacher_marks is not None else evaluation.ai_marks; evaluation.teacher_marks = payload.marks
        evaluation.review_resolved = True
        evaluation.review_resolution = "overridden"
        evaluation.reviewed_at = datetime.now(timezone.utc)
        for review in db.scalars(select(ReviewSuggestion).where(ReviewSuggestion.evaluation_id == evaluation.id, ReviewSuggestion.status == "pending")):
            review.status = "superseded"
        db.add(TeacherOverride(evaluation_id=evaluation.id, teacher_id=teacher["id"], previous_marks=previous, new_marks=payload.marks, reason=payload.reason))
        status = recalculate_submission_state(db, db.get(Answer, evaluation.answer_id).submission_id)
        db.commit()
    return {"status": "overridden", "submission_status": status.value}


@app.get("/api/evaluations/{evaluation_id}/history")
def evaluation_history(evaluation_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        owned_evaluation(db, evaluation_id, teacher["id"])
        return {"overrides": [{"previous_marks": o.previous_marks, "new_marks": o.new_marks, "reason": o.reason, "created_at": o.created_at} for o in db.scalars(select(TeacherOverride).where(TeacherOverride.evaluation_id == evaluation_id).order_by(TeacherOverride.created_at.desc()))], "reviews": [{"suggested_marks": r.suggested_marks, "reason": r.reason, "status": r.status, "created_at": r.created_at} for r in db.scalars(select(ReviewSuggestion).where(ReviewSuggestion.evaluation_id == evaluation_id).order_by(ReviewSuggestion.created_at.desc()))]}


def concept_rows(db, teacher_id: str, student_id: str | None = None, exam_id: str | None = None):
    statement = select(CriterionEvaluation, RubricCriterion).select_from(CriterionEvaluation).join(RubricCriterion, CriterionEvaluation.criterion_id == RubricCriterion.id).join(Answer, CriterionEvaluation.answer_id == Answer.id).join(Submission, Answer.submission_id == Submission.id).join(Student, Submission.student_id == Student.id).join(ClassCohort, Student.class_id == ClassCohort.id).join(Exam, Submission.exam_id == Exam.id).where(Exam.teacher_id == teacher_id, Submission.archived_at.is_(None), Student.archived_at.is_(None), ClassCohort.archived_at.is_(None), Exam.archived_at.is_(None), Submission.status.in_([SubmissionStatus.COMPLETED, SubmissionStatus.REVIEW_REQUIRED]))
    if student_id: statement = statement.where(Submission.student_id == student_id)
    if exam_id: statement = statement.where(Submission.exam_id == exam_id)
    return db.execute(statement).all()


def profile_data(db, student: Student, teacher_id: str) -> dict:
    concepts = {}
    for ev, criterion in concept_rows(db, teacher_id, student_id=student.id):
        name = criterion.concept_tags[0] if criterion.concept_tags else "Uncategorized"; bucket = concepts.setdefault(name, [0, 0]); bucket[0] += ev.teacher_marks if ev.teacher_marks is not None else ev.ai_marks; bucket[1] += criterion.max_marks
    performance = [{"concept": name, "mastery": round(score / maximum * 100) if maximum else 0} for name, (score, maximum) in concepts.items()]
    submissions = db.execute(active_submission_rows(db, teacher_id).where(Submission.student_id == student.id).order_by(Submission.created_at.desc())).all()
    papers = []
    for submission, _, exam in submissions:
        papers.append({"id": submission.id, "exam_id": exam.id, "exam_title": exam.title, "subject": exam.subject, "total_marks": exam.total_marks, "score": submission.total_score, "percentage": round(submission.total_score / exam.total_marks * 100) if exam.total_marks else 0, "status": submission.status.value, "created_at": submission.created_at, "href": f"/submissions/{submission.id}"})
    memberships = db.scalars(select(ClassMembership).where(ClassMembership.student_id == student.id)).all()
    classes = [db.get(ClassCohort, membership.class_id) for membership in memberships]
    return {"student": {"id": student.id, "name": student.name, "identifier": student.identifier, "class_id": student.class_id, "classes": [{"id": cohort.id, "name": cohort.name} for cohort in classes if cohort and not cohort.archived_at]}, "concepts": performance, "strengths": [p["concept"] for p in performance if p["mastery"] >= 75], "developing": [p["concept"] for p in performance if p["mastery"] < 75], "submissions": papers}


@app.get("/api/students/{student_id}/profile")
def student_profile(student_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        student = db.scalar(select(Student).join(ClassCohort).where(Student.id == student_id, ClassCohort.teacher_id == teacher["id"]))
        if not student: raise HTTPException(404, "Student not found")
        return profile_data(db, student, teacher["id"])


@app.get("/api/classes/{class_id}/analytics")
def class_analytics(class_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        cohort = owned_class(db, class_id, teacher["id"])
        students = db.scalars(select(Student).where(Student.class_id == class_id, Student.archived_at.is_(None)).order_by(Student.name)).all()
        submissions = db.scalars(select(Submission).join(Student).where(Student.class_id == class_id, Submission.archived_at.is_(None))).all()
        concepts: dict[str, list[float]] = {}
        for evaluation, criterion in db.execute(select(CriterionEvaluation, RubricCriterion).select_from(CriterionEvaluation).join(RubricCriterion, CriterionEvaluation.criterion_id == RubricCriterion.id).join(Answer, CriterionEvaluation.answer_id == Answer.id).join(Submission, Answer.submission_id == Submission.id).join(Student, Submission.student_id == Student.id).where(Student.class_id == class_id)):
            marks = evaluation.teacher_marks if evaluation.teacher_marks is not None else evaluation.ai_marks
            name = criterion.concept_tags[0] if criterion.concept_tags else "Uncategorized"
            bucket = concepts.setdefault(name, [0, 0, 0])
            bucket[0] += marks
            bucket[1] += criterion.max_marks
            bucket[2] += int(evaluation.needs_review)
        scores = [submission.total_score for submission in submissions if submission.status in {SubmissionStatus.COMPLETED, SubmissionStatus.REVIEW_REQUIRED}]
        return {"class": {"id": cohort.id, "name": cohort.name}, "student_count": len(students), "submission_count": len(submissions), "average_score": round(sum(scores) / len(scores), 2) if scores else 0, "concepts": [{"name": name, "mastery": round(bucket[0] / bucket[1] * 100) if bucket[1] else 0, "review_rate": round(bucket[2] / len(submissions) * 100) if submissions else 0} for name, bucket in sorted(concepts.items(), key=lambda item: item[1][0] / item[1][1] if item[1][1] else 0)], "students": [{"id": student.id, "name": student.name, "identifier": student.identifier, "profile": profile_data(db, student, teacher["id"])} for student in students]}


@app.get("/api/student/profile")
def own_profile(student: dict = Depends(current_student)):
    with session() as db:
        profile_student = db.get(Student, student["id"])
        cohort = db.get(ClassCohort, profile_student.class_id) if profile_student else None
        if not profile_student or not cohort: raise HTTPException(404, "Student not found")
        return profile_data(db, profile_student, cohort.teacher_id)


@app.get("/api/exams/{exam_id}/analytics")
def analytics(exam_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        exam = owned_exam(db, exam_id, teacher["id"])
        submissions = db.scalars(select(Submission).where(Submission.exam_id == exam_id)).all()
        concepts: dict[str, list[float]] = {}
        questions: dict[str, list[float | str]] = {}
        criteria: dict[str, list[float | str]] = {}
        for evaluation, criterion, question in db.execute(
            select(CriterionEvaluation, RubricCriterion, Question)
            .select_from(CriterionEvaluation)
            .join(RubricCriterion, CriterionEvaluation.criterion_id == RubricCriterion.id)
            .join(Question, RubricCriterion.question_id == Question.id)
            .join(Answer, CriterionEvaluation.answer_id == Answer.id)
            .where(Answer.submission_id.in_([submission.id for submission in submissions] or ["-"]))
        ):
            marks = evaluation.teacher_marks if evaluation.teacher_marks is not None else evaluation.ai_marks
            concept = criterion.concept_tags[0] if criterion.concept_tags else "Uncategorized"
            concept_bucket = concepts.setdefault(concept, [0, 0, 0, 0])
            concept_bucket[0] += marks; concept_bucket[1] += criterion.max_marks; concept_bucket[2] += 1; concept_bucket[3] += int(evaluation.needs_review)
            question_bucket = questions.setdefault(question.number, [question.text, 0, 0, 0])
            question_bucket[1] += marks; question_bucket[2] += criterion.max_marks; question_bucket[3] += 1
            criterion_bucket = criteria.setdefault(criterion.title, [question.number, 0, 0, 0])
            criterion_bucket[1] += marks; criterion_bucket[2] += criterion.max_marks; criterion_bucket[3] += int(marks < criterion.max_marks)
        evaluated = [submission for submission in submissions if submission.status in {SubmissionStatus.COMPLETED, SubmissionStatus.REVIEW_REQUIRED}]
        average_score = round(sum(submission.total_score for submission in evaluated) / len(evaluated), 2) if evaluated else 0
        return {
            "exam": {"id": exam.id, "title": exam.title, "subject": exam.subject, "total_marks": exam.total_marks},
            "submission_count": len(submissions),
            "evaluated_count": len(evaluated),
            "average_score": average_score,
            "average_percentage": round(average_score / exam.total_marks * 100) if exam.total_marks else 0,
            "review_rate": round(sum(1 for submission in evaluated if submission.status == SubmissionStatus.REVIEW_REQUIRED) / len(evaluated) * 100) if evaluated else 0,
            "concepts": [{"name": name, "mastery": round(value[0] / value[1] * 100) if value[1] else 0, "attempts": value[2], "review_rate": round(value[3] / value[2] * 100) if value[2] else 0} for name, value in concepts.items()],
            "questions": [{"number": name, "text": value[0], "mastery": round(value[1] / value[2] * 100) if value[2] else 0, "attempts": value[3]} for name, value in questions.items()],
            "criteria": [{"title": name, "question_number": value[0], "mastery": round(value[1] / value[2] * 100) if value[2] else 0, "failure_rate": round(value[3] / len(evaluated) * 100) if evaluated else 0} for name, value in criteria.items()],
        }


@app.get("/api/processing-jobs")
def processing_jobs(teacher: dict = Depends(current_teacher)):
    active = {SubmissionStatus.UPLOADED, SubmissionStatus.PREPROCESSING, SubmissionStatus.TRANSCRIBING, SubmissionStatus.STRUCTURED, SubmissionStatus.GRADING, SubmissionStatus.FAILED}
    with session() as db:
        rows = db.execute(select(Submission, Student, Exam, ProcessingJob).join(Student).join(Exam).join(ClassCohort, Student.class_id == ClassCohort.id).join(ProcessingJob, ProcessingJob.submission_id == Submission.id).where(Exam.teacher_id == teacher["id"], Submission.archived_at.is_(None), Student.archived_at.is_(None), Exam.archived_at.is_(None), ClassCohort.archived_at.is_(None), ProcessingJob.stage.in_(active)).order_by(ProcessingJob.updated_at.desc())).all()
        return {"items": [{"id": job.id, "submission_id": submission.id, "student_name": student.name, "exam_title": exam.title, "stage": job.stage.value, "attempts": job.attempts, "error": job.error, "updated_at": job.updated_at, "href": f"/submissions/{submission.id}"} for submission, student, exam, job in rows]}


@app.post("/api/assistant/query")
async def assistant_query(payload: AssistantQuery, teacher: dict = Depends(current_teacher)):
    with session() as db:
        student_ids = {mention.id for mention in payload.mentions if mention.type == "student"}
        exam_ids = {mention.id for mention in payload.mentions if mention.type == "exam"}
        paper_ids = {mention.id for mention in payload.mentions if mention.type == "paper"}
        class_ids = {mention.id for mention in payload.mentions if mention.type == "class"}
        resolved = []
        for student_id in student_ids:
            student = db.scalar(select(Student).join(ClassCohort).where(Student.id == student_id, ClassCohort.teacher_id == teacher["id"], Student.archived_at.is_(None), ClassCohort.archived_at.is_(None)))
            if not student: raise HTTPException(404, "Mentioned student is not available.")
            resolved.append({"type": "student", "id": student.id, "label": student.name, "href": f"/students/{student.id}"})
        for exam_id in exam_ids:
            exam = active_owned_exam(db, exam_id, teacher["id"])
            resolved.append({"type": "exam", "id": exam.id, "label": exam.title, "href": f"/exams/{exam.id}"})
        for class_id in class_ids:
            cohort = owned_class(db, class_id, teacher["id"])
            if cohort.archived_at: raise HTTPException(404, "Mentioned class is not available.")
            resolved.append({"type": "class", "id": cohort.id, "label": cohort.name, "href": f"/classes/{cohort.id}"})
        for paper_id in paper_ids:
            submission = active_owned_submission(db, paper_id, teacher["id"])
            student = db.get(Student, submission.student_id); exam = db.get(Exam, submission.exam_id)
            resolved.append({"type": "paper", "id": submission.id, "label": f"{student.name} - {exam.title}", "href": f"/submissions/{submission.id}"})
        concepts = {}
        rows = concept_rows(db, teacher["id"])
        if student_ids:
            rows = [row for row in rows if db.get(Answer, row[0].answer_id).submission_id in {submission.id for submission in db.scalars(select(Submission).where(Submission.student_id.in_(student_ids), Submission.archived_at.is_(None)))}]
        if exam_ids:
            rows = [row for row in rows if db.get(Answer, row[0].answer_id).submission_id in {submission.id for submission in db.scalars(select(Submission).where(Submission.exam_id.in_(exam_ids), Submission.archived_at.is_(None)))}]
        if paper_ids:
            rows = [row for row in rows if db.get(Answer, row[0].answer_id).submission_id in paper_ids]
        if class_ids:
            rows = [row for row in rows if db.get(Exam, db.get(Submission, db.get(Answer, row[0].answer_id).submission_id).exam_id).class_id in class_ids]
        for ev, criterion in rows:
            name = criterion.concept_tags[0] if criterion.concept_tags else "Uncategorized"; bucket = concepts.setdefault(name, [0, 0]); bucket[0] += ev.teacher_marks if ev.teacher_marks is not None else ev.ai_marks; bucket[1] += criterion.max_marks
        sources = [{"name": name, "mastery": round(score / maximum * 100) if maximum else 0} for name, (score, maximum) in sorted(concepts.items(), key=lambda item: item[1][0] / item[1][1] if item[1][1] else 0)]
    if not settings.openai_enabled: return {"answer": "Add OPENAI_API_KEY to enable PRISM's grounded analysis. PRISM prepared only the visible assessment statistics and will not fabricate an answer.", "sources": sources[:3], "resolved_mentions": resolved, "ai_enabled": False}
    answer = await answer_teacher_question(payload.question, sources)
    return {"answer": answer.answer, "sources": [source for source in sources if source["name"] in answer.sources], "resolved_mentions": resolved, "ai_enabled": True}


@app.get("/api/assistant/mentions")
def assistant_mentions(q: str = "", teacher: dict = Depends(current_teacher)):
    query = q.strip()
    if len(query) < 1:
        return {"items": []}
    like = f"%{query}%"
    with session() as db:
        items = []
        for student, cohort in db.execute(select(Student, ClassCohort).join(ClassCohort).where(ClassCohort.teacher_id == teacher["id"], Student.archived_at.is_(None), ClassCohort.archived_at.is_(None), Student.name.ilike(like)).order_by(Student.name).limit(6)):
            items.append({"type": "student", "id": student.id, "label": student.name, "secondary_label": f"Student · {cohort.name}", "href": f"/students/{student.id}"})
        for cohort in db.scalars(select(ClassCohort).where(ClassCohort.teacher_id == teacher["id"], ClassCohort.archived_at.is_(None), ClassCohort.name.ilike(like)).order_by(ClassCohort.name).limit(4)):
            items.append({"type": "class", "id": cohort.id, "label": cohort.name, "secondary_label": "Class", "href": f"/classes/{cohort.id}"})
        for exam in db.scalars(select(Exam).where(Exam.teacher_id == teacher["id"], Exam.archived_at.is_(None), Exam.title.ilike(like)).order_by(Exam.created_at.desc()).limit(6)):
            items.append({"type": "exam", "id": exam.id, "label": exam.title, "secondary_label": f"Exam · {exam.subject}", "href": f"/exams/{exam.id}"})
        for submission, student, exam in db.execute(active_submission_rows(db, teacher["id"]).where(Student.name.ilike(like)).order_by(Submission.created_at.desc()).limit(6)):
            items.append({"type": "paper", "id": submission.id, "label": f"{student.name} - {exam.title}", "secondary_label": f"Paper · {submission.total_score:g} marks", "href": f"/submissions/{submission.id}"})
    return {"items": items[:12]}
