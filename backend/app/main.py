from __future__ import annotations

import hashlib
import io
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal

import fitz
from fastapi import BackgroundTasks, Cookie, Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text

from . import database
from .ai import (EXAM_IMPORT_VERSION, PerceptionResult, answer_teacher_question,
                 grade_criterion, import_exam_pages, model_for, perceive_page, review_criterion)
from .auth import create_session, hash_password, read_session_data, verify_password
from .demo import seed_demo_accounts
from .models import (AIArtifact, Account, AccountRole, Answer, ClassCohort, CriterionEvaluation, EvaluationEvidence, Exam,
                     EvidenceRegion, ProcessingJob, Question, ReviewSuggestion, RubricCriterion, Student, Submission,
                     SubmissionPage, SubmissionStatus, Teacher, TeacherOverride)
from .settings import get_settings

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
UPLOADS = DATA / "uploads"
settings = get_settings()
MODEL = settings.openai_model
REVIEW_THRESHOLD = settings.ai_review_threshold
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}


def init_storage() -> None:
    DATA.mkdir(exist_ok=True)
    UPLOADS.mkdir(exist_ok=True)


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
    questions: list[QuestionInput]


class ReviewInput(BaseModel):
    comment: str = Field(min_length=3)


class OverrideInput(BaseModel):
    marks: float = Field(ge=0)
    reason: str | None = None


class AssistantQuery(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class TeacherCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=256)
    name: str | None = Field(default=None, min_length=2, max_length=120)


def imported_draft(result) -> dict:
    warnings = list(result.warnings)
    questions = []
    for question in result.questions:
        criterion_total = sum(criterion.max_marks for criterion in question.criteria)
        if question.max_marks is not None and round(criterion_total, 2) != round(question.max_marks, 2):
            warnings.append(f"{question.number}: suggested criteria total {criterion_total:g}, but the paper shows {question.max_marks:g} marks.")
        questions.append({
            "number": question.number,
            "text": question.text,
            "max_marks": question.max_marks,
            "confidence": question.confidence,
            "criteria": [criterion.model_dump() for criterion in question.criteria],
        })
    return {"title": result.title, "subject": result.subject, "questions": questions, "warnings": list(dict.fromkeys(warnings)), "prompt_version": EXAM_IMPORT_VERSION}


def current_account(session_token: str | None = Cookie(default=None, alias="prism_session")) -> dict:
    session_data = read_session_data(session_token, settings.session_secret.get_secret_value())
    if not session_data:
        raise HTTPException(401, "Sign in to continue.")
    with session() as db:
        account = db.get(Account, session_data["sub"])
        if not account or account.role.value != session_data["role"]:
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
    response.set_cookie("prism_session", create_session(account.id, settings.session_secret.get_secret_value(), settings.session_ttl_seconds, account.role.value), max_age=settings.session_ttl_seconds, httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/")


def owned_exam(db, exam_id: str, teacher_id: str) -> Exam:
    exam = db.scalar(select(Exam).where(Exam.id == exam_id, Exam.teacher_id == teacher_id))
    if not exam:
        raise HTTPException(404, "Exam not found")
    return exam


def owned_submission(db, submission_id: str, teacher_id: str) -> Submission:
    submission = db.scalar(select(Submission).join(Exam).where(Submission.id == submission_id, Exam.teacher_id == teacher_id))
    if not submission:
        raise HTTPException(404, "Submission not found")
    return submission


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
        return {"id": exam.id, "title": exam.title, "subject": exam.subject, "date": exam.date.isoformat() if exam.date else None, "created_at": exam.created_at, "teacher_id": exam.teacher_id, "questions": questions, "total_marks": sum(q["max_marks"] for q in questions)}


def score_submission(db, submission: Submission) -> float:
    evaluations = db.scalars(select(CriterionEvaluation).join(Answer).where(Answer.submission_id == submission.id)).all()
    submission.total_score = sum(item.teacher_marks if item.teacher_marks is not None else item.ai_marks for item in evaluations)
    return submission.total_score


def create_exam(payload: ExamInput, teacher_id: str) -> dict:
    parsed_date = date.fromisoformat(payload.date) if payload.date else None
    with session() as db:
        exam = Exam(teacher_id=teacher_id, title=payload.title, subject=payload.subject, date=parsed_date, total_marks=sum(c.max_marks for q in payload.questions for c in q.criteria))
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
            old_evaluations = db.scalars(select(CriterionEvaluation).join(Answer).where(Answer.submission_id == submission_id)).all()
            for evaluation in old_evaluations:
                for evidence in db.scalars(select(EvaluationEvidence).where(EvaluationEvidence.evaluation_id == evaluation.id)):
                    db.delete(evidence)
                db.delete(evaluation)
            for answer in db.scalars(select(Answer).where(Answer.submission_id == submission_id)):
                db.delete(answer)
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
                    evaluation = CriterionEvaluation(answer_id=mapped_answers[0].id, criterion_id=criterion.id, ai_marks=min(criterion.max_marks, max(0, result.awarded_marks)), reason=result.reason, confidence=result.confidence, needs_review=result.needs_review or result.confidence < REVIEW_THRESHOLD or any(answer.uncertainty for answer in mapped_answers))
                    db.add(evaluation)
                    db.flush()
                    for quote in result.evidence_quotes:
                        db.add(EvaluationEvidence(evaluation_id=evaluation.id, page_id=page.id, quote=quote))
                    db.commit()
        with session() as db:
            submission = db.get(Submission, submission_id)
            review_needed = db.scalar(select(CriterionEvaluation.id).join(Answer).where(Answer.submission_id == submission_id, CriterionEvaluation.needs_review.is_(True)).limit(1)) is not None
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
def bootstrap_teacher(payload: TeacherCredentials, response: Response):
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
def logout(response: Response): response.delete_cookie("prism_session", path="/")


@app.get("/api/auth/me")
def me(account: dict = Depends(current_account)):
    if account["role"] == AccountRole.TEACHER.value:
        return current_teacher(account)
    return current_student(account)


@app.get("/api/dashboard")
def dashboard(teacher: dict = Depends(current_teacher)):
    with session() as db:
        exams = db.scalars(select(Exam).where(Exam.teacher_id == teacher["id"]).order_by(Exam.created_at.desc())).all()
        pending = db.scalar(select(func.count()).select_from(CriterionEvaluation).join(Answer).join(Submission).join(Exam).where(Exam.teacher_id == teacher["id"], CriterionEvaluation.needs_review.is_(True), CriterionEvaluation.teacher_marks.is_(None))) or 0
        rows = db.execute(select(Submission, Student, Exam).join(Student).join(Exam).where(Exam.teacher_id == teacher["id"]).order_by(Submission.created_at.desc()).limit(8)).all()
        return {"exams": [{"id": e.id, "title": e.title, "subject": e.subject, "date": e.date, "created_at": e.created_at, "teacher_id": e.teacher_id} for e in exams], "pending_reviews": pending, "submissions": [{"id": s.id, "exam_id": s.exam_id, "student_id": s.student_id, "status": s.status.value, "total_score": s.total_score, "created_at": s.created_at, "error": s.error, "student_name": st.name, "exam_title": ex.title} for s, st, ex in rows]}


@app.post("/api/exams")
def post_exam(payload: ExamInput, teacher: dict = Depends(current_teacher)): return create_exam(payload, teacher["id"])


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
def get_exams(teacher: dict = Depends(current_teacher)):
    with session() as db: ids = db.scalars(select(Exam.id).where(Exam.teacher_id == teacher["id"]).order_by(Exam.created_at.desc())).all()
    return [exam_detail(exam_id, teacher["id"]) for exam_id in ids]


@app.get("/api/exams/{exam_id}")
def get_exam(exam_id: str, teacher: dict = Depends(current_teacher)): return exam_detail(exam_id, teacher["id"])


@app.post("/api/exams/{exam_id}/submissions")
async def upload_submission(background_tasks: BackgroundTasks, exam_id: str, student_name: str = Form(...), file: UploadFile | None = File(None), pages: list[UploadFile] | None = File(None), teacher: dict = Depends(current_teacher)):
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
    with session() as db: owned_exam(db, exam_id, teacher["id"])
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
        cohort = unassigned_class(db, teacher["id"])
        student = db.scalar(select(Student).where(Student.class_id == cohort.id, Student.name == student_name))
        if not student:
            student = Student(class_id=cohort.id, name=student_name, identifier=f"UP-{uuid.uuid4().hex[:6]}"); db.add(student); db.flush()
        duplicate = db.scalar(select(Submission).where(Submission.exam_id == exam_id, Submission.student_id == student.id, Submission.source_hash == source_hash).order_by(Submission.created_at.desc()))
        if duplicate:
            return {"id": duplicate.id, "status": duplicate.status.value, "student_name": student_name, "page_count": db.scalar(select(func.count()).select_from(SubmissionPage).where(SubmissionPage.submission_id == duplicate.id)), "duplicate": True}
        submission = Submission(exam_id=exam_id, student_id=student.id, status=SubmissionStatus.UPLOADED, source_hash=source_hash)
        db.add(submission); db.flush(); db.add(ProcessingJob(submission_id=submission.id, stage=SubmissionStatus.UPLOADED))
        for page_number, page in enumerate(normalized_pages, 1):
            db.add(SubmissionPage(submission_id=submission.id, page_number=page_number, original_key=page["original_key"], mime_type=page["mime_type"], **{key: page[key] for key in ("processed_key", "width", "height", "image_hash")}))
        db.commit(); submission_id = submission.id
    background_tasks.add_task(process_submission, submission_id)
    return {"id": submission_id, "status": "uploaded", "student_name": student_name, "page_count": len(normalized_pages), "duplicate": False}


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
        if submission.status not in {SubmissionStatus.FAILED, SubmissionStatus.REVIEW_REQUIRED, SubmissionStatus.COMPLETED}: raise HTTPException(409, "Only finished or failed submissions can be retried.")
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
        pages = [{"id": p.id, "page_number": p.page_number, "width": p.width, "height": p.height, "url": f"/api/pages/{p.id}"} for p in db.scalars(select(SubmissionPage).where(SubmissionPage.submission_id == submission_id).order_by(SubmissionPage.page_number))]
        answers = []
        for answer in db.scalars(select(Answer).where(Answer.submission_id == submission_id)):
            regions = db.scalars(select(EvidenceRegion).where(EvidenceRegion.answer_id == answer.id)).all()
            region_data = lambda region: {"kind": region.kind, "description": region.text, "bbox": (region.bbox or {}).get("coordinates")}
            answers.append({"id": answer.id, "question_id": answer.question_id, "page_id": answer.page_id, "transcription": answer.transcription, "uncertainty": answer.uncertainty, "prompt_version": answer.prompt_version, "confidence": answer.confidence, "visual_regions": [region_data(region) for region in regions if region.kind != "formula"], "formula_regions": [region_data(region) for region in regions if region.kind == "formula"]})
        evaluations = []
        for ev, criterion, question in db.execute(select(CriterionEvaluation, RubricCriterion, Question).select_from(CriterionEvaluation).join(RubricCriterion, CriterionEvaluation.criterion_id == RubricCriterion.id).join(Question, RubricCriterion.question_id == Question.id).join(Answer, CriterionEvaluation.answer_id == Answer.id).where(Answer.submission_id == submission_id).order_by(Question.number)):
            evaluations.append({"id": ev.id, "ai_marks": ev.ai_marks, "teacher_marks": ev.teacher_marks, "reason": ev.reason, "confidence": ev.confidence, "needs_review": ev.needs_review, "criterion_title": criterion.title, "criterion_description": criterion.description, "max_marks": criterion.max_marks, "concept": criterion.concept_tags[0] if criterion.concept_tags else "Uncategorized", "question_id": question.id, "question_number": question.number, "question_text": question.text, "evidence": [{"page": p.page_number if (p := db.get(SubmissionPage, evidence.page_id)) else None, "quote": evidence.quote} for evidence in db.scalars(select(EvaluationEvidence).where(EvaluationEvidence.evaluation_id == ev.id))], "effective_marks": ev.teacher_marks if ev.teacher_marks is not None else ev.ai_marks})
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
        if not page: raise HTTPException(404, "Page not found")
        return FileResponse(page.original_key, media_type=page.mime_type)


@app.post("/api/evaluations/{evaluation_id}/review")
async def request_review(evaluation_id: str, payload: ReviewInput, teacher: dict = Depends(current_teacher)):
    if not settings.openai_enabled: raise HTTPException(503, "OPENAI_API_KEY is required for criterion re-evaluation.")
    with session() as db:
        evaluation = owned_evaluation(db, evaluation_id, teacher["id"]); answer = db.get(Answer, evaluation.answer_id); page = db.get(SubmissionPage, answer.page_id); criterion = db.get(RubricCriterion, evaluation.criterion_id); question = db.get(Question, criterion.question_id)
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
        if decision == "accept":
            evaluation = db.get(CriterionEvaluation, review.evaluation_id); previous = evaluation.teacher_marks if evaluation.teacher_marks is not None else evaluation.ai_marks; evaluation.teacher_marks = review.suggested_marks
            db.add(TeacherOverride(evaluation_id=evaluation.id, teacher_id=teacher["id"], previous_marks=previous, new_marks=review.suggested_marks, reason="Accepted AI review suggestion")); score_submission(db, db.get(Submission, db.get(Answer, evaluation.answer_id).submission_id))
        review.status = decision; db.commit()
    return {"status": decision}


@app.patch("/api/evaluations/{evaluation_id}")
def override(evaluation_id: str, payload: OverrideInput, teacher: dict = Depends(current_teacher)):
    with session() as db:
        evaluation = owned_evaluation(db, evaluation_id, teacher["id"]); criterion = db.get(RubricCriterion, evaluation.criterion_id)
        if payload.marks > criterion.max_marks: raise HTTPException(422, "Marks cannot exceed the criterion maximum.")
        previous = evaluation.teacher_marks if evaluation.teacher_marks is not None else evaluation.ai_marks; evaluation.teacher_marks = payload.marks
        db.add(TeacherOverride(evaluation_id=evaluation.id, teacher_id=teacher["id"], previous_marks=previous, new_marks=payload.marks, reason=payload.reason)); score_submission(db, db.get(Submission, db.get(Answer, evaluation.answer_id).submission_id)); db.commit()
    return {"status": "overridden"}


@app.get("/api/evaluations/{evaluation_id}/history")
def evaluation_history(evaluation_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        owned_evaluation(db, evaluation_id, teacher["id"])
        return {"overrides": [{"previous_marks": o.previous_marks, "new_marks": o.new_marks, "reason": o.reason, "created_at": o.created_at} for o in db.scalars(select(TeacherOverride).where(TeacherOverride.evaluation_id == evaluation_id).order_by(TeacherOverride.created_at.desc()))], "reviews": [{"suggested_marks": r.suggested_marks, "reason": r.reason, "status": r.status, "created_at": r.created_at} for r in db.scalars(select(ReviewSuggestion).where(ReviewSuggestion.evaluation_id == evaluation_id).order_by(ReviewSuggestion.created_at.desc()))]}


def concept_rows(db, teacher_id: str, student_id: str | None = None, exam_id: str | None = None):
    statement = select(CriterionEvaluation, RubricCriterion).select_from(CriterionEvaluation).join(RubricCriterion, CriterionEvaluation.criterion_id == RubricCriterion.id).join(Answer, CriterionEvaluation.answer_id == Answer.id).join(Submission, Answer.submission_id == Submission.id).join(Exam, Submission.exam_id == Exam.id).where(Exam.teacher_id == teacher_id)
    if student_id: statement = statement.where(Submission.student_id == student_id)
    if exam_id: statement = statement.where(Submission.exam_id == exam_id)
    return db.execute(statement).all()


def profile_data(db, student: Student, teacher_id: str) -> dict:
    concepts = {}
    for ev, criterion in concept_rows(db, teacher_id, student_id=student.id):
        name = criterion.concept_tags[0] if criterion.concept_tags else "Uncategorized"; bucket = concepts.setdefault(name, [0, 0]); bucket[0] += ev.teacher_marks if ev.teacher_marks is not None else ev.ai_marks; bucket[1] += criterion.max_marks
    performance = [{"concept": name, "mastery": round(score / maximum * 100) if maximum else 0} for name, (score, maximum) in concepts.items()]
    return {"student": {"id": student.id, "name": student.name, "identifier": student.identifier}, "concepts": performance, "strengths": [p["concept"] for p in performance if p["mastery"] >= 75], "developing": [p["concept"] for p in performance if p["mastery"] < 75]}


@app.get("/api/students/{student_id}/profile")
def student_profile(student_id: str, teacher: dict = Depends(current_teacher)):
    with session() as db:
        student = db.scalar(select(Student).join(ClassCohort).where(Student.id == student_id, ClassCohort.teacher_id == teacher["id"]))
        if not student: raise HTTPException(404, "Student not found")
        return profile_data(db, student, teacher["id"])


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


@app.post("/api/assistant/query")
async def assistant_query(payload: AssistantQuery, teacher: dict = Depends(current_teacher)):
    with session() as db:
        concepts = {}
        for ev, criterion in concept_rows(db, teacher["id"]):
            name = criterion.concept_tags[0] if criterion.concept_tags else "Uncategorized"; bucket = concepts.setdefault(name, [0, 0]); bucket[0] += ev.teacher_marks if ev.teacher_marks is not None else ev.ai_marks; bucket[1] += criterion.max_marks
        sources = [{"name": name, "mastery": round(score / maximum * 100) if maximum else 0} for name, (score, maximum) in sorted(concepts.items(), key=lambda item: item[1][0] / item[1][1] if item[1][1] else 0)]
    if not settings.openai_enabled: return {"answer": "Add OPENAI_API_KEY to enable grounded Luna answers. PRISM has prepared the relevant class concept statistics but will not fabricate an AI response.", "sources": sources[:3], "ai_enabled": False}
    answer = await answer_teacher_question(payload.question, sources)
    return {"answer": answer.answer, "sources": [source for source in sources if source["name"] in answer.sources], "ai_enabled": True}
