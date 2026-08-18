import asyncio
import io

import pytest
import fitz
from fastapi import BackgroundTasks, HTTPException, UploadFile
from starlette.datastructures import Headers

from app.main import init_db, create_exam, ExamInput, QuestionInput, CriterionInput, start_processing, upload_submission


def test_exam_totals_are_deterministic(tmp_path, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "DB", tmp_path / "test.db")
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "UPLOADS", tmp_path / "uploads")
    init_db()
    exam = create_exam(ExamInput(title="T", subject="S", questions=[QuestionInput(number="Q1", text="Question", criteria=[CriterionInput(title="C", description="D", max_marks=2, concept="X")])]))
    assert exam["total_marks"] == 2


def test_upload_rejects_unsupported_file_type(tmp_path, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "DB", tmp_path / "test.db")
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "UPLOADS", tmp_path / "uploads")
    init_db()
    exam = create_exam(ExamInput(title="T", subject="S", questions=[QuestionInput(number="Q1", text="Question", criteria=[CriterionInput(title="C", description="D", max_marks=2, concept="X")])]))
    file = UploadFile(filename="paper.txt", file=io.BytesIO(b"not an exam"), headers=Headers({"content-type": "text/plain"}))
    with pytest.raises(HTTPException) as error:
        asyncio.run(upload_submission(BackgroundTasks(), exam["id"], "Student", file, teacher={"id": None}))
    assert error.value.status_code == 415


def test_pdf_upload_creates_a_normalized_record_for_every_page(tmp_path, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "DB", tmp_path / "test.db")
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "UPLOADS", tmp_path / "uploads")
    init_db()
    exam = create_exam(ExamInput(title="T", subject="S", questions=[QuestionInput(number="Q1", text="Question", criteria=[CriterionInput(title="C", description="D", max_marks=2, concept="X")])]))
    document = fitz.open()
    document.new_page()
    document.new_page()
    file = UploadFile(filename="paper.pdf", file=io.BytesIO(document.tobytes()), headers=Headers({"content-type": "application/pdf"}))
    submission = asyncio.run(upload_submission(BackgroundTasks(), exam["id"], "Student", file, teacher={"id": None}))
    with main.connection() as con:
        pages = con.execute("SELECT processed_path, width, height FROM pages WHERE submission_id=? ORDER BY page_number", (submission["id"],)).fetchall()
        job = con.execute("SELECT stage, attempts FROM processing_jobs WHERE submission_id=?", (submission["id"],)).fetchone()
    assert len(pages) == 2
    assert all(page["width"] and page["height"] for page in pages)
    assert all(__import__("pathlib").Path(page["processed_path"]).exists() for page in pages)
    assert job["stage"] == "uploaded"
    assert job["attempts"] == 0


def test_process_endpoint_rejects_unknown_submission():
    with pytest.raises(HTTPException) as error:
        asyncio.run(start_processing("missing", BackgroundTasks()))
    assert error.value.status_code == 404
