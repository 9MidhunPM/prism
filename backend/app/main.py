from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DB = DATA / "prism.db"
MODEL = "gpt-5.6-luna"
REVIEW_THRESHOLD = 0.75


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def initialize() -> None:
    DATA.mkdir(exist_ok=True)
    with connection() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS exams (id TEXT PRIMARY KEY, title TEXT, subject TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS students (id TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE IF NOT EXISTS submissions (id TEXT PRIMARY KEY, exam_id TEXT, student_id TEXT, status TEXT, total_score REAL, created_at TEXT);
        CREATE TABLE IF NOT EXISTS evaluations (id TEXT PRIMARY KEY, submission_id TEXT, criterion_title TEXT, concept TEXT, max_marks REAL, ai_marks REAL, teacher_marks REAL, reason TEXT, evidence TEXT, confidence REAL, needs_review INTEGER);
        CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, evaluation_id TEXT, suggested_marks REAL, status TEXT, created_at TEXT);
        """)
        if con.execute("SELECT 1 FROM exams LIMIT 1").fetchone():
            return
        exam_id = str(uuid.uuid4())
        con.execute("INSERT INTO exams VALUES (?, ?, ?, ?)", (exam_id, "Machine Learning Foundations", "Computer Science", now()))
        criteria = [("Correct definition", "Gradient descent", 2), ("Update direction", "Gradient descent", 2), ("Learning rate", "Optimization", 2), ("Precision", "Evaluation metrics", 2), ("Recall", "Evaluation metrics", 2)]
        for index, name in enumerate(["Arun Patel", "Maya Chen", "Samira Noor", "Leo Martin", "Iris Okafor"]):
            student_id, submission_id = str(uuid.uuid4()), str(uuid.uuid4())
            status = "review_required" if index == 0 else "completed"
            con.execute("INSERT INTO students VALUES (?, ?)", (student_id, name))
            con.execute("INSERT INTO submissions VALUES (?, ?, ?, ?, 0, ?)", (submission_id, exam_id, student_id, status, now()))
            total = 0
            for title, concept, maximum in criteria:
                mark = round(maximum * ([0.83, 1, 0.67, 0.83, 0.5][index] if concept != "Evaluation metrics" else [0.5, 1, 0.75, 0.5, 0.25][index]), 1)
                confidence = 0.68 if index == 0 and concept == "Optimization" else 0.9
                total += mark
                con.execute("INSERT INTO evaluations VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)", (str(uuid.uuid4()), submission_id, title, concept, maximum, mark, "Assessment is grounded in the student response.", json.dumps([{"page": 1, "quote": "Student response evidence is available on the original paper."}]), confidence, int(confidence < REVIEW_THRESHOLD)))
            con.execute("UPDATE submissions SET total_score=? WHERE id=?", (total, submission_id))


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize()
    yield


app = FastAPI(title="PRISM API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["https://prism.midhunpm.in", "http://localhost:3000"], allow_origin_regex=r"http://localhost:\d+", allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL}


@app.get("/api/dashboard")
def dashboard():
    with connection() as con:
        exams = [dict(row) for row in con.execute("SELECT * FROM exams ORDER BY created_at DESC")]
        submissions = [dict(row) for row in con.execute("SELECT s.*, st.name student_name, e.title exam_title FROM submissions s JOIN students st ON st.id=s.student_id JOIN exams e ON e.id=s.exam_id ORDER BY s.created_at DESC")]
        pending = con.execute("SELECT COUNT(*) AS count FROM evaluations WHERE needs_review=1 AND teacher_marks IS NULL").fetchone()["count"]
    return {"exams": exams, "submissions": submissions, "pending_reviews": pending}


@app.get("/api/submissions/{submission_id}")
def submission(submission_id: str):
    with connection() as con:
        row = con.execute("SELECT s.*, st.name student_name, e.title exam_title FROM submissions s JOIN students st ON st.id=s.student_id JOIN exams e ON e.id=s.exam_id WHERE s.id=?", (submission_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Submission not found")
        evaluations = [dict(item) for item in con.execute("SELECT * FROM evaluations WHERE submission_id=?", (submission_id,))]
    for item in evaluations:
        item["effective_marks"] = item["teacher_marks"] if item["teacher_marks"] is not None else item["ai_marks"]
        item["evidence"] = json.loads(item["evidence"])
        item["question_number"] = "Q1" if item["concept"] != "Evaluation metrics" else "Q2"
    return {**dict(row), "evaluations": evaluations, "pages": []}


class ReviewInput(BaseModel):
    comment: str = Field(min_length=3)


@app.post("/api/evaluations/{evaluation_id}/review")
def request_review(evaluation_id: str, _: ReviewInput):
    with connection() as con:
        evaluation = con.execute("SELECT * FROM evaluations WHERE id=?", (evaluation_id,)).fetchone()
        if not evaluation:
            raise HTTPException(404, "Evaluation not found")
        review_id = str(uuid.uuid4())
        suggestion = min(evaluation["max_marks"], evaluation["ai_marks"] + 0.5)
        con.execute("INSERT INTO reviews VALUES (?, ?, ?, 'pending', ?)", (review_id, evaluation_id, suggestion, now()))
    return {"id": review_id, "suggested_marks": suggestion, "status": "pending"}


@app.post("/api/reviews/{review_id}/{decision}")
def decide_review(review_id: str, decision: Literal["accept", "reject"]):
    with connection() as con:
        review = con.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
        if not review or review["status"] != "pending":
            raise HTTPException(404, "Pending review not found")
        if decision == "accept":
            evaluation = con.execute("SELECT * FROM evaluations WHERE id=?", (review["evaluation_id"],)).fetchone()
            con.execute("UPDATE evaluations SET teacher_marks=? WHERE id=?", (review["suggested_marks"], review["evaluation_id"]))
            total = con.execute("SELECT SUM(COALESCE(teacher_marks, ai_marks)) AS total FROM evaluations WHERE submission_id=?", (evaluation["submission_id"],)).fetchone()["total"]
            con.execute("UPDATE submissions SET total_score=? WHERE id=?", (total, evaluation["submission_id"]))
        con.execute("UPDATE reviews SET status=? WHERE id=?", (decision, review_id))
    return {"status": decision}
