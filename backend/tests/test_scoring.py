import asyncio
import io

import pytest
import fitz
from fastapi import BackgroundTasks, HTTPException, UploadFile
from starlette.datastructures import Headers

from app.main import create_exam, delete_exam, recalculate_submission_state, ExamInput, QuestionInput, CriterionInput, start_processing, upload_submission
from app.models import (AIArtifact, Answer, ClassCohort, CriterionEvaluation,
                        EvaluationEvidence, EvidenceRegion, Exam, ProcessingJob,
                        Question, ReviewSuggestion, RubricCriterion, Student,
                        Submission, SubmissionPage, SubmissionStatus, Teacher,
                        TeacherOverride)
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


def evaluation_tree(teacher: str, exam_id: str, stage: SubmissionStatus = SubmissionStatus.COMPLETED):
    with database.SessionLocal() as db:
        cohort = ClassCohort(teacher_id=teacher, name="Class A")
        db.add(cohort); db.flush()
        student = Student(class_id=cohort.id, name="Student", identifier="S-1")
        db.add(student); db.flush()
        submission = Submission(exam_id=exam_id, student_id=student.id, status=stage)
        db.add(submission); db.flush()
        page = SubmissionPage(submission_id=submission.id, page_number=1, original_key="/tmp/paper.jpg", mime_type="image/jpeg")
        db.add(page); db.flush()
        question = db.query(Question).filter_by(exam_id=exam_id).one()
        criterion = db.query(RubricCriterion).filter_by(question_id=question.id).one()
        answer = Answer(submission_id=submission.id, question_id=question.id, page_id=page.id, transcription="Answer", prompt_version="perception_v1")
        db.add(answer); db.flush()
        evaluation = CriterionEvaluation(answer_id=answer.id, criterion_id=criterion.id, ai_marks=1, reason="Evidence", confidence=0.9)
        db.add(evaluation); db.flush()
        db.add(EvidenceRegion(answer_id=answer.id, page_id=page.id, kind="text", text="Answer"))
        db.add(EvaluationEvidence(evaluation_id=evaluation.id, page_id=page.id, quote="Answer"))
        db.add(ReviewSuggestion(evaluation_id=evaluation.id, requested_by_teacher_id=teacher, comment="Check", suggested_marks=1, reason="Evidence", evidence_quotes=["Answer"], confidence=0.9))
        db.add(TeacherOverride(evaluation_id=evaluation.id, teacher_id=teacher, previous_marks=1, new_marks=1, reason="Checked"))
        db.add(AIArtifact(submission_id=submission.id, operation="perception", model="gpt-5.6-luna", prompt_version="perception_v1", input_hash="a" * 64, output={}))
        db.add(ProcessingJob(submission_id=submission.id, stage=stage))
        db.commit()
        return submission.id, evaluation.id


def test_recommended_reviews_do_not_block_completion(isolated_database):
    teacher = teacher_id()
    exam = exam_for(teacher)
    submission_id, evaluation_id = evaluation_tree(teacher, exam["id"])
    with database.SessionLocal() as db:
        evaluation = db.get(CriterionEvaluation, evaluation_id)
        evaluation.needs_review = True
        evaluation.review_severity = "review_recommended"
        evaluation.review_resolved = False
        assert recalculate_submission_state(db, submission_id) == SubmissionStatus.COMPLETED
        evaluation.review_severity = "review_required"
        assert recalculate_submission_state(db, submission_id) == SubmissionStatus.REVIEW_REQUIRED


def test_delete_exam_removes_dependent_records_in_foreign_key_order(isolated_database):
    teacher = teacher_id()
    exam = exam_for(teacher)
    evaluation_tree(teacher, exam["id"])
    assert delete_exam(exam["id"], teacher={"id": teacher})["deleted"] is True
    with database.SessionLocal() as db:
        assert db.query(Exam).count() == 0
        assert db.query(Submission).count() == 0
        assert db.query(SubmissionPage).count() == 0
        assert db.query(Answer).count() == 0
        assert db.query(CriterionEvaluation).count() == 0
        assert db.query(EvaluationEvidence).count() == 0
        assert db.query(ReviewSuggestion).count() == 0
        assert db.query(TeacherOverride).count() == 0
        assert db.query(AIArtifact).count() == 0
        assert db.query(ProcessingJob).count() == 0


def test_delete_exam_rejects_active_processing(isolated_database):
    teacher = teacher_id()
    exam = exam_for(teacher)
    evaluation_tree(teacher, exam["id"], SubmissionStatus.GRADING)
    with pytest.raises(HTTPException) as error:
        delete_exam(exam["id"], teacher={"id": teacher})
    assert error.value.status_code == 409
