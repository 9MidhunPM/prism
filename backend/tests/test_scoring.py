import asyncio
import io

import pytest
import fitz
from fastapi import BackgroundTasks, HTTPException, UploadFile
from starlette.datastructures import Headers

from app.main import create_exam, ExamInput, QuestionInput, CriterionInput, start_processing, upload_submission
from app.models import ProcessingJob, SubmissionPage, Teacher
from app import database


def teacher_id():
    with database.SessionLocal() as db:
        teacher = Teacher(name="Teacher", email="teacher@example.com", password_hash="not-used")
        db.add(teacher)
        db.commit()
        return teacher.id


def exam_for(teacher):
    return create_exam(ExamInput(title="T", subject="S", questions=[QuestionInput(number="Q1", text="Question", criteria=[CriterionInput(title="C", description="D", max_marks=2, concept="X")])]), teacher)


def test_exam_totals_are_deterministic(isolated_database):
    exam = exam_for(teacher_id())
    assert exam["total_marks"] == 2


def test_upload_rejects_unsupported_file_type(isolated_database):
    teacher = teacher_id()
    exam = exam_for(teacher)
    file = UploadFile(filename="paper.txt", file=io.BytesIO(b"not an exam"), headers=Headers({"content-type": "text/plain"}))
    with pytest.raises(HTTPException) as error:
        asyncio.run(upload_submission(BackgroundTasks(), exam["id"], "Student", file, teacher={"id": teacher}))
    assert error.value.status_code == 415


def test_pdf_upload_creates_a_normalized_record_for_every_page(isolated_database):
    teacher = teacher_id()
    exam = exam_for(teacher)
    document = fitz.open()
    document.new_page()
    document.new_page()
    file = UploadFile(filename="paper.pdf", file=io.BytesIO(document.tobytes()), headers=Headers({"content-type": "application/pdf"}))
    submission = asyncio.run(upload_submission(BackgroundTasks(), exam["id"], "Student", file, teacher={"id": teacher}))
    with database.SessionLocal() as db:
        pages = db.query(SubmissionPage).filter_by(submission_id=submission["id"]).order_by(SubmissionPage.page_number).all()
        job = db.query(ProcessingJob).filter_by(submission_id=submission["id"]).one()
    assert len(pages) == 2
    assert all(page.width and page.height for page in pages)
    assert all(__import__("pathlib").Path(page.processed_key).exists() for page in pages)
    assert job.stage.value == "uploaded"
    assert job.attempts == 0


def test_process_endpoint_rejects_unknown_submission(isolated_database):
    with pytest.raises(HTTPException) as error:
        asyncio.run(start_processing("missing", BackgroundTasks(), teacher={"id": teacher_id()}))
    assert error.value.status_code == 404
