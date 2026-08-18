from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import fitz
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from .ai import grade_criterion, perceive_page
from .settings import get_settings

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
UPLOADS = DATA / "uploads"
DB = DATA / "prism.db"
settings = get_settings()
MODEL = settings.openai_model
REVIEW_THRESHOLD = settings.ai_review_threshold
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    DATA.mkdir(exist_ok=True)
    UPLOADS.mkdir(exist_ok=True)
    with connection() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS exams (id TEXT PRIMARY KEY, title TEXT NOT NULL, subject TEXT NOT NULL, date TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, exam_id TEXT NOT NULL, number TEXT NOT NULL, text TEXT NOT NULL, max_marks REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS criteria (id TEXT PRIMARY KEY, question_id TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL, max_marks REAL NOT NULL, concept TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS students (id TEXT PRIMARY KEY, name TEXT NOT NULL, identifier TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS submissions (id TEXT PRIMARY KEY, exam_id TEXT NOT NULL, student_id TEXT NOT NULL, status TEXT NOT NULL, total_score REAL DEFAULT 0, created_at TEXT NOT NULL, error TEXT);
        CREATE TABLE IF NOT EXISTS pages (id TEXT PRIMARY KEY, submission_id TEXT NOT NULL, page_number INTEGER NOT NULL, original_path TEXT NOT NULL, mime_type TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS evaluations (id TEXT PRIMARY KEY, submission_id TEXT NOT NULL, criterion_id TEXT NOT NULL, ai_marks REAL NOT NULL, teacher_marks REAL, reason TEXT NOT NULL, evidence TEXT NOT NULL, confidence REAL NOT NULL, needs_review INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS answers (id TEXT PRIMARY KEY, submission_id TEXT NOT NULL, question_id TEXT, transcription TEXT NOT NULL, uncertainty TEXT NOT NULL, prompt_version TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ai_artifacts (id TEXT PRIMARY KEY, submission_id TEXT NOT NULL, operation TEXT NOT NULL, prompt_version TEXT NOT NULL, image_hash TEXT, output TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, evaluation_id TEXT NOT NULL, suggested_marks REAL NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS overrides (id TEXT PRIMARY KEY, evaluation_id TEXT NOT NULL, previous_marks REAL NOT NULL, new_marks REAL NOT NULL, reason TEXT, created_at TEXT NOT NULL);
        """)
        columns = {row["name"] for row in con.execute("PRAGMA table_info(pages)")}
        for name, definition in {"processed_path": "TEXT", "width": "INTEGER", "height": "INTEGER", "image_hash": "TEXT"}.items():
            if name not in columns:
                con.execute(f"ALTER TABLE pages ADD COLUMN {name} {definition}")


def normalize_pages(original_path: Path, mime_type: str) -> list[dict]:
    """Create conservative, correctly oriented PNGs without modifying originals."""
    processed_dir = UPLOADS / "processed"
    processed_dir.mkdir(exist_ok=True)
    images: list[Image.Image] = []
    if mime_type == "application/pdf":
        with fitz.open(original_path) as document:
            if not document or len(document) > settings.max_submission_pages:
                raise HTTPException(422, f"Submissions may contain up to {settings.max_submission_pages} pages.")
            for page in document:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
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
        normalized.append({"page_number": page_number, "processed_path": str(processed_path), "width": image.width, "height": image.height, "image_hash": hashlib.sha256(processed_path.read_bytes()).hexdigest()})
    return normalized


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


def exam_detail(exam_id: str) -> dict:
    with connection() as con:
        exam = con.execute("SELECT * FROM exams WHERE id=?", (exam_id,)).fetchone()
        if not exam:
            raise HTTPException(404, "Exam not found")
        questions = []
        for question in con.execute("SELECT * FROM questions WHERE exam_id=? ORDER BY number", (exam_id,)):
            criteria = [dict(row) for row in con.execute("SELECT * FROM criteria WHERE question_id=?", (question["id"],))]
            questions.append({**dict(question), "criteria": criteria, "max_marks": sum(c["max_marks"] for c in criteria)})
    return {**dict(exam), "questions": questions, "total_marks": sum(q["max_marks"] for q in questions)}


def score_submission(submission_id: str) -> float:
    with connection() as con:
        rows = con.execute("SELECT ai_marks, teacher_marks FROM evaluations WHERE submission_id=?", (submission_id,)).fetchall()
        total = sum(row["teacher_marks"] if row["teacher_marks"] is not None else row["ai_marks"] for row in rows)
        con.execute("UPDATE submissions SET total_score=? WHERE id=?", (total, submission_id))
    return total


def seed_demo() -> None:
    with connection() as con:
        if con.execute("SELECT 1 FROM exams LIMIT 1").fetchone():
            return
    payload = ExamInput(title="Machine Learning Foundations", subject="Computer Science", date="2026-08-18", questions=[
        QuestionInput(number="Q1", text="Explain gradient descent and the effect of learning rate.", criteria=[
            CriterionInput(title="Correct definition", description="Defines gradient descent as minimizing a loss function.", max_marks=2, concept="Gradient descent"),
            CriterionInput(title="Update direction", description="Explains moving opposite the gradient.", max_marks=2, concept="Gradient descent"),
            CriterionInput(title="Learning rate", description="Explains the impact of a large or small learning rate.", max_marks=2, concept="Optimization"),
        ]),
        QuestionInput(number="Q2", text="Differentiate precision and recall.", criteria=[
            CriterionInput(title="Precision", description="Defines precision correctly.", max_marks=2, concept="Evaluation metrics"),
            CriterionInput(title="Recall", description="Defines recall correctly.", max_marks=2, concept="Evaluation metrics"),
        ]),
    ])
    create_exam(payload)
    with connection() as con:
        exam_id = con.execute("SELECT id FROM exams LIMIT 1").fetchone()["id"]
        students = [(str(uuid.uuid4()), name, f"S{index:03}") for index, name in enumerate(["Arun Patel", "Maya Chen", "Samira Noor", "Leo Martin", "Iris Okafor"], 1)]
        con.executemany("INSERT INTO students VALUES (?, ?, ?)", students)
        criteria = con.execute("SELECT id, concept, max_marks FROM criteria").fetchall()
        for index, student in enumerate(students):
            sid = str(uuid.uuid4())
            status = "review_required" if index == 0 else "completed"
            con.execute("INSERT INTO submissions VALUES (?, ?, ?, ?, 0, ?, NULL)", (sid, exam_id, student[0], status, now()))
            for criterion in criteria:
                ratio = [0.5, 1, 0.75, 0.5, 0.25][index] if criterion["concept"] == "Evaluation metrics" else [0.83, 1, 0.67, 0.83, 0.5][index]
                mark = round(criterion["max_marks"] * ratio, 1)
                confidence = 0.68 if index == 0 and criterion["concept"] == "Optimization" else 0.9
                con.execute("INSERT INTO evaluations VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?)", (str(uuid.uuid4()), sid, criterion["id"], mark, "Assessment is grounded in the transcribed response.", json.dumps([{ "page": 1, "quote": "Student response evidence is available on the original paper." }]), confidence, int(confidence < REVIEW_THRESHOLD)))
            total = con.execute("SELECT SUM(ai_marks) AS total FROM evaluations WHERE submission_id=?", (sid,)).fetchone()["total"]
            con.execute("UPDATE submissions SET total_score=? WHERE id=?", (total or 0, sid))


def create_exam(payload: ExamInput) -> dict:
    exam_id = str(uuid.uuid4())
    with connection() as con:
        con.execute("INSERT INTO exams VALUES (?, ?, ?, ?, ?)", (exam_id, payload.title, payload.subject, payload.date, now()))
        for question in payload.questions:
            question_id = str(uuid.uuid4())
            max_marks = sum(c.max_marks for c in question.criteria)
            con.execute("INSERT INTO questions VALUES (?, ?, ?, ?, ?)", (question_id, exam_id, question.number, question.text, max_marks))
            for criterion in question.criteria:
                con.execute("INSERT INTO criteria VALUES (?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), question_id, criterion.title, criterion.description, criterion.max_marks, criterion.concept))
    return exam_detail(exam_id)


async def process_submission(submission_id: str) -> None:
    # The full pipeline is deliberately stateful so every stage is inspectable and retryable.
    with connection() as con:
        con.execute("UPDATE submissions SET status='preprocessing', error=NULL WHERE id=?", (submission_id,))
        pages = con.execute("SELECT * FROM pages WHERE submission_id=?", (submission_id,)).fetchall()
    try:
        # A missing key is recoverable: seeded submissions keep the demo usable offline.
        if not settings.openai_enabled:
            raise RuntimeError("OPENAI_API_KEY is required for live Luna processing. Demo submissions remain available.")
        with connection() as con:
            con.execute("UPDATE submissions SET status='transcribing' WHERE id=?", (submission_id,))
            exam_id = con.execute("SELECT exam_id FROM submissions WHERE id=?", (submission_id,)).fetchone()["exam_id"]
            questions = con.execute("SELECT * FROM questions WHERE exam_id=?", (exam_id,)).fetchall()
        page = pages[0]
        perception = await perceive_page(page["processed_path"] or page["original_path"], "image/jpeg" if page["processed_path"] else page["mime_type"], [q["number"] for q in questions])
        with connection() as con:
            con.execute("INSERT INTO ai_artifacts VALUES (?, ?, 'perception', 'perception_v1', ?, ?, ?)", (str(uuid.uuid4()), submission_id, hashlib.sha256(Path(page["original_path"]).read_bytes()).hexdigest(), perception.model_dump_json(), now()))
            for answer in perception.answers:
                match = next((q for q in questions if q["number"] == answer.question_id), None)
                con.execute("INSERT INTO answers VALUES (?, ?, ?, ?, ?, 'perception_v1')", (str(uuid.uuid4()), submission_id, match["id"] if match else None, answer.transcription, json.dumps(answer.uncertain_segments)))
            con.execute("UPDATE submissions SET status='grading' WHERE id=?", (submission_id,))
        for question in questions:
            matching = next((a for a in perception.answers if a.question_id == question["number"]), None)
            if not matching:
                continue
            with connection() as con:
                criteria = con.execute("SELECT * FROM criteria WHERE question_id=?", (question["id"],)).fetchall()
            for criterion in criteria:
                result = await grade_criterion(page["processed_path"] or page["original_path"], "image/jpeg" if page["processed_path"] else page["mime_type"], question["text"], dict(criterion), matching.transcription)
                marks = min(criterion["max_marks"], max(0, result.awarded_marks))
                evidence = [{"page": page["page_number"], "quote": quote} for quote in result.evidence_quotes]
                with connection() as con:
                    con.execute("INSERT INTO evaluations VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?)", (str(uuid.uuid4()), submission_id, criterion["id"], marks, result.reason, json.dumps(evidence), result.confidence, int(result.needs_review or result.confidence < REVIEW_THRESHOLD or bool(matching.uncertain_segments))))
        with connection() as con:
            needs_review = con.execute("SELECT 1 FROM evaluations WHERE submission_id=? AND needs_review=1", (submission_id,)).fetchone()
            con.execute("UPDATE submissions SET status=? WHERE id=?", ("review_required" if needs_review else "completed", submission_id))
        score_submission(submission_id)
    except Exception as exc:
        with connection() as con:
            con.execute("UPDATE submissions SET status='failed', error=? WHERE id=?", (str(exc), submission_id))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_demo()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_origin_regex=r"http://localhost:\d+", allow_methods=["*"], allow_headers=["*"], allow_credentials=True)


@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL, "ai_enabled": settings.openai_enabled}


@app.get("/api/dashboard")
def dashboard():
    with connection() as con:
        exams = con.execute("SELECT * FROM exams ORDER BY created_at DESC").fetchall()
        reviews = con.execute("SELECT COUNT(*) count FROM evaluations WHERE needs_review=1 AND teacher_marks IS NULL").fetchone()["count"]
        submissions = con.execute("""SELECT s.*, st.name student_name, e.title exam_title FROM submissions s JOIN students st ON st.id=s.student_id JOIN exams e ON e.id=s.exam_id ORDER BY s.created_at DESC LIMIT 8""").fetchall()
    return {"exams": [dict(e) for e in exams], "pending_reviews": reviews, "submissions": [dict(s) for s in submissions]}


@app.post("/api/exams")
def post_exam(payload: ExamInput):
    return create_exam(payload)


@app.get("/api/exams")
def get_exams():
    with connection() as con:
        ids = [row["id"] for row in con.execute("SELECT id FROM exams ORDER BY created_at DESC")]
    return [exam_detail(exam_id) for exam_id in ids]


@app.get("/api/exams/{exam_id}")
def get_exam(exam_id: str):
    return exam_detail(exam_id)


@app.post("/api/exams/{exam_id}/submissions")
async def upload_submission(background_tasks: BackgroundTasks, exam_id: str, student_name: str = Form(...), file: UploadFile = File(...)):
    exam_detail(exam_id)
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Upload a JPEG, PNG, or PDF file.")
    contents = await file.read()
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Files must be smaller than {settings.max_upload_mb} MB.")
    if not contents:
        raise HTTPException(400, "The uploaded file is empty.")
    extension = {"image/jpeg": ".jpg", "image/png": ".png", "application/pdf": ".pdf"}[file.content_type]
    path = UPLOADS / f"{uuid.uuid4()}{extension}"
    path.write_bytes(contents)
    pages = normalize_pages(path, file.content_type)
    with connection() as con:
        student = con.execute("SELECT * FROM students WHERE name=?", (student_name,)).fetchone()
        student_id = student["id"] if student else str(uuid.uuid4())
        if not student:
            con.execute("INSERT INTO students VALUES (?, ?, ?)", (student_id, student_name, f"UP-{student_id[:6]}"))
        submission_id = str(uuid.uuid4())
        con.execute("INSERT INTO submissions VALUES (?, ?, ?, 'uploaded', 0, ?, NULL)", (submission_id, exam_id, student_id, now()))
        for page in pages:
            con.execute("INSERT INTO pages (id, submission_id, page_number, original_path, mime_type, processed_path, width, height, image_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), submission_id, page["page_number"], str(path), file.content_type, page["processed_path"], page["width"], page["height"], page["image_hash"]))
    background_tasks.add_task(process_submission, submission_id)
    return {"id": submission_id, "status": "uploaded"}


@app.get("/api/submissions/{submission_id}")
def get_submission(submission_id: str):
    with connection() as con:
        submission = con.execute("""SELECT s.*, st.name student_name, e.title exam_title, e.id exam_id FROM submissions s JOIN students st ON st.id=s.student_id JOIN exams e ON e.id=s.exam_id WHERE s.id=?""", (submission_id,)).fetchone()
        if not submission:
            raise HTTPException(404, "Submission not found")
        pages = [dict(row) for row in con.execute("SELECT id, page_number, width, height FROM pages WHERE submission_id=?", (submission_id,))]
        evaluations = [dict(row) for row in con.execute("""SELECT ev.*, c.title criterion_title, c.description criterion_description, c.max_marks, c.concept, q.number question_number, q.text question_text FROM evaluations ev JOIN criteria c ON c.id=ev.criterion_id JOIN questions q ON q.id=c.question_id WHERE ev.submission_id=? ORDER BY q.number""", (submission_id,))]
        for item in evaluations:
            item["evidence"] = json.loads(item["evidence"])
            item["effective_marks"] = item["teacher_marks"] if item["teacher_marks"] is not None else item["ai_marks"]
    return {**dict(submission), "pages": pages, "evaluations": evaluations}


@app.get("/api/pages/{page_id}")
def get_page(page_id: str):
    with connection() as con:
        page = con.execute("SELECT * FROM pages WHERE id=?", (page_id,)).fetchone()
    if not page:
        raise HTTPException(404, "Page not found")
    return FileResponse(page["original_path"], media_type=page["mime_type"])


@app.post("/api/evaluations/{evaluation_id}/review")
def request_review(evaluation_id: str, payload: ReviewInput):
    with connection() as con:
        evaluation = con.execute("""SELECT ev.*, c.max_marks FROM evaluations ev JOIN criteria c ON c.id=ev.criterion_id WHERE ev.id=?""", (evaluation_id,)).fetchone()
        if not evaluation:
            raise HTTPException(404, "Evaluation not found")
        suggestion = min(evaluation["max_marks"], evaluation["ai_marks"] + 0.5)
        review_id = str(uuid.uuid4())
        con.execute("INSERT INTO reviews VALUES (?, ?, ?, ?, 'pending', ?)", (review_id, evaluation_id, suggestion, f"Review suggestion based on teacher note: {payload.comment}", now()))
    return {"id": review_id, "suggested_marks": suggestion, "status": "pending"}


@app.post("/api/reviews/{review_id}/{decision}")
def decide_review(review_id: str, decision: Literal["accept", "reject"]):
    with connection() as con:
        review = con.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
        if not review or review["status"] != "pending":
            raise HTTPException(404, "Pending review not found")
        if decision == "accept":
            ev = con.execute("SELECT ai_marks FROM evaluations WHERE id=?", (review["evaluation_id"],)).fetchone()
            con.execute("UPDATE evaluations SET teacher_marks=? WHERE id=?", (review["suggested_marks"], review["evaluation_id"]))
            con.execute("INSERT INTO overrides VALUES (?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), review["evaluation_id"], ev["ai_marks"], review["suggested_marks"], "Accepted AI review suggestion", now()))
            submission = con.execute("SELECT submission_id FROM evaluations WHERE id=?", (review["evaluation_id"],)).fetchone()
            total = con.execute("SELECT SUM(COALESCE(teacher_marks, ai_marks)) AS total FROM evaluations WHERE submission_id=?", (submission["submission_id"],)).fetchone()["total"]
            con.execute("UPDATE submissions SET total_score=? WHERE id=?", (total or 0, submission["submission_id"]))
        con.execute("UPDATE reviews SET status=? WHERE id=?", (decision, review_id))
    return {"status": decision}


@app.patch("/api/evaluations/{evaluation_id}")
def override(evaluation_id: str, payload: OverrideInput):
    with connection() as con:
        row = con.execute("""SELECT ev.*, c.max_marks FROM evaluations ev JOIN criteria c ON c.id=ev.criterion_id WHERE ev.id=?""", (evaluation_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Evaluation not found")
        if payload.marks > row["max_marks"]:
            raise HTTPException(422, "Marks cannot exceed the criterion maximum.")
        previous = row["teacher_marks"] if row["teacher_marks"] is not None else row["ai_marks"]
        con.execute("UPDATE evaluations SET teacher_marks=? WHERE id=?", (payload.marks, evaluation_id))
        con.execute("INSERT INTO overrides VALUES (?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), evaluation_id, previous, payload.marks, payload.reason, now()))
        score_submission(row["submission_id"])
    return {"status": "overridden"}


@app.get("/api/students/{student_id}/profile")
def student_profile(student_id: str):
    with connection() as con:
        student = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        if not student:
            raise HTTPException(404, "Student not found")
        rows = con.execute("""SELECT c.concept, c.max_marks, COALESCE(ev.teacher_marks, ev.ai_marks) marks FROM evaluations ev JOIN criteria c ON c.id=ev.criterion_id JOIN submissions s ON s.id=ev.submission_id WHERE s.student_id=?""", (student_id,)).fetchall()
    concepts = {}
    for row in rows:
        value = concepts.setdefault(row["concept"], [0, 0])
        value[0] += row["marks"]
        value[1] += row["max_marks"]
    performance = [{"concept": name, "mastery": round(score / maximum * 100) if maximum else 0} for name, (score, maximum) in concepts.items()]
    return {"student": dict(student), "concepts": performance, "strengths": [p["concept"] for p in performance if p["mastery"] >= 75], "developing": [p["concept"] for p in performance if p["mastery"] < 75]}


@app.get("/api/exams/{exam_id}/analytics")
def analytics(exam_id: str):
    with connection() as con:
        rows = con.execute("""SELECT c.concept, c.max_marks, COALESCE(ev.teacher_marks, ev.ai_marks) marks, ev.needs_review FROM evaluations ev JOIN criteria c ON c.id=ev.criterion_id JOIN submissions s ON s.id=ev.submission_id WHERE s.exam_id=?""", (exam_id,)).fetchall()
    concepts = {}
    for row in rows:
        bucket = concepts.setdefault(row["concept"], [0, 0, 0, 0])
        bucket[0] += row["marks"]; bucket[1] += row["max_marks"]; bucket[2] += 1; bucket[3] += row["needs_review"]
    return {"concepts": [{"name": key, "mastery": round(value[0] / value[1] * 100), "attempts": value[2], "review_rate": round(value[3] / value[2] * 100)} for key, value in concepts.items()]}
