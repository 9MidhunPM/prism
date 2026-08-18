"""Idempotent environment-configured demo account provisioning."""

from __future__ import annotations

from sqlalchemy import select

from .auth import hash_password
from . import database
from .models import (Account, AccountRole, Answer, ClassCohort, CriterionEvaluation,
                     EvaluationEvidence, Exam, Question, RubricCriterion, Student,
                     Submission, SubmissionPage, SubmissionStatus, Teacher)
from .settings import Settings, get_settings


def _required(settings: Settings, name: str) -> str:
    value = getattr(settings, name)
    if value is not None and hasattr(value, "get_secret_value"):
        value = value.get_secret_value()
    if not value:
        raise ValueError(f"{name.upper()} must be set when DEMO_MODE is enabled")
    return value


def seed_demo_accounts(settings: Settings | None = None) -> dict[str, str]:
    """Create or reuse the configured demo teacher and student accounts."""
    settings = settings or get_settings()
    if not settings.demo_mode:
        return {"status": "disabled"}
    teacher_name = _required(settings, "demo_teacher_name")
    teacher_email = _required(settings, "demo_teacher_email").strip().lower()
    teacher_password = _required(settings, "demo_teacher_password")
    student_name = _required(settings, "demo_student_name")
    student_email = _required(settings, "demo_student_email").strip().lower()
    student_password = _required(settings, "demo_student_password")

    with database.SessionLocal() as db:
        teacher = db.scalar(select(Teacher).where(Teacher.email == teacher_email))
        if not teacher:
            teacher = Teacher(name=teacher_name, email=teacher_email, password_hash=hash_password(teacher_password))
            db.add(teacher)
            db.flush()
        if not db.scalar(select(Account).where(Account.teacher_id == teacher.id)):
            db.add(Account(email=teacher_email, password_hash=teacher.password_hash, role=AccountRole.TEACHER, teacher_id=teacher.id))

        cohort = db.scalar(select(ClassCohort).where(ClassCohort.teacher_id == teacher.id, ClassCohort.name == "Demo"))
        if not cohort:
            cohort = ClassCohort(teacher_id=teacher.id, name="Demo")
            db.add(cohort)
            db.flush()
        student_account = db.scalar(select(Account).where(Account.email == student_email))
        if student_account and student_account.role != AccountRole.STUDENT:
            raise ValueError("DEMO_STUDENT_EMAIL belongs to a non-student account")
        if not student_account:
            student = Student(class_id=cohort.id, name=student_name, identifier=f"DEMO-{student_email}")
            db.add(student)
            db.flush()
            student_account = Account(email=student_email, password_hash=hash_password(student_password), role=AccountRole.STUDENT, student_id=student.id)
            db.add(student_account)
        demo_exam = db.scalar(select(Exam).where(Exam.teacher_id == teacher.id, Exam.title == "Demo science assessment"))
        if not demo_exam:
            demo_exam = Exam(teacher_id=teacher.id, class_id=cohort.id, title="Demo science assessment", subject="Science", total_marks=4)
            db.add(demo_exam)
            db.flush()
            question = Question(exam_id=demo_exam.id, number="Q1", text="Explain how plants make food.", max_marks=4, concept_tags=["Photosynthesis"])
            db.add(question)
            db.flush()
            criterion = RubricCriterion(question_id=question.id, code="C1", title="Explains photosynthesis", description="Identifies sunlight, water, carbon dioxide, and food production.", max_marks=4, concept_tags=["Photosynthesis"])
            db.add(criterion)
            db.flush()
            submission = Submission(exam_id=demo_exam.id, student_id=student_account.student_id, status=SubmissionStatus.COMPLETED, total_score=3)
            db.add(submission)
            db.flush()
            page = SubmissionPage(submission_id=submission.id, page_number=1, original_key="demo://student-paper", mime_type="image/jpeg")
            db.add(page)
            db.flush()
            answer = Answer(submission_id=submission.id, question_id=question.id, page_id=page.id, transcription="Plants use sunlight, water and air to make food.", confidence=0.95, uncertainty=[], prompt_version="demo_v1")
            db.add(answer)
            db.flush()
            evaluation = CriterionEvaluation(answer_id=answer.id, criterion_id=criterion.id, ai_marks=3, reason="Correctly identifies the main inputs and food production, but does not name carbon dioxide explicitly.", confidence=0.9, needs_review=False)
            db.add(evaluation)
            db.flush()
            db.add(EvaluationEvidence(evaluation_id=evaluation.id, page_id=None, quote="Plants use sunlight, water and air to make food."))
        db.commit()
        return {"status": "seeded", "teacher_account_id": db.scalar(select(Account.id).where(Account.teacher_id == teacher.id)), "student_account_id": student_account.id}
