"""Normalized PRISM persistence models. AI data is auditable and teacher decisions are immutable history."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def identifier() -> str:
    return str(uuid.uuid4())


class SubmissionStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    TRANSCRIBING = "transcribing"
    STRUCTURED = "structured"
    GRADING = "grading"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"
    RESCAN_REQUIRED = "rescan_required"
    FAILED = "failed"


class AccountRole(str, enum.Enum):
    TEACHER = "teacher"
    STUDENT = "student"


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClassCohort(Base):
    __tablename__ = "classes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("class_id", "identifier", name="uq_student_class_identifier"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    identifier: Mapped[str] = mapped_column(String(100))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClassMembership(Base):
    __tablename__ = "class_memberships"
    __table_args__ = (UniqueConstraint("class_id", "student_id", name="uq_class_membership"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("teacher_id", name="uq_account_teacher"),
        UniqueConstraint("student_id", name="uq_account_student"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[AccountRole] = mapped_column(Enum(AccountRole), index=True)
    teacher_id: Mapped[str | None] = mapped_column(ForeignKey("teachers.id"), nullable=True, index=True)
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id"), index=True)
    class_id: Mapped[str | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(120))
    course: Mapped[str | None] = mapped_column(String(120), nullable=True)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_marks: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("exam_id", "number", name="uq_question_exam_number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), index=True)
    number: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(Text)
    max_marks: Mapped[float] = mapped_column(Float)
    concept_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    answer_key: Mapped[str | None] = mapped_column(Text, nullable=True)


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"
    __table_args__ = (UniqueConstraint("question_id", "code", name="uq_criterion_question_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), index=True)
    code: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    max_marks: Mapped[float] = mapped_column(Float)
    concept_tags: Mapped[list[str]] = mapped_column(JSON, default=list)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus), default=SubmissionStatus.UPLOADED)
    total_score: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mapping_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by_teacher_id: Mapped[str | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)


class SubmissionPage(Base):
    __tablename__ = "submission_pages"
    __table_args__ = (UniqueConstraint("submission_id", "page_number", name="uq_page_submission_number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    original_key: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(100))
    processed_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_status: Mapped[str] = mapped_column(String(30), default="pending")
    quality_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    processed_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class Answer(Base):
    __tablename__ = "answers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    question_id: Mapped[str | None] = mapped_column(ForeignKey("questions.id"), nullable=True, index=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("submission_pages.id"), index=True)
    transcription: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    uncertainty: Mapped[list[dict]] = mapped_column(JSON, default=list)
    prompt_version: Mapped[str] = mapped_column(String(50))
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    mapping_basis: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mapping_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class EvidenceRegion(Base):
    __tablename__ = "evidence_regions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    answer_id: Mapped[str] = mapped_column(ForeignKey("answers.id"), index=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("submission_pages.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class CriterionEvaluation(Base):
    __tablename__ = "criterion_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    answer_id: Mapped[str] = mapped_column(ForeignKey("answers.id"), index=True)
    criterion_id: Mapped[str] = mapped_column(ForeignKey("rubric_criteria.id"), index=True)
    ai_marks: Mapped[float] = mapped_column(Float)
    teacher_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_severity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    review_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    review_resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvaluationEvidence(Base):
    __tablename__ = "evaluation_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("criterion_evaluations.id"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("submission_pages.id"), nullable=True, index=True)
    quote: Mapped[str] = mapped_column(Text)


class TeacherOverride(Base):
    __tablename__ = "teacher_overrides"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("criterion_evaluations.id"), index=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id"))
    previous_marks: Mapped[float] = mapped_column(Float)
    new_marks: Mapped[float] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewSuggestion(Base):
    __tablename__ = "review_suggestions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("criterion_evaluations.id"), index=True)
    requested_by_teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id"), index=True)
    comment: Mapped[str] = mapped_column(Text)
    suggested_marks: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    evidence_quotes: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIArtifact(Base):
    __tablename__ = "ai_artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    submission_id: Mapped[str | None] = mapped_column(ForeignKey("submissions.id"), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(50))
    prompt_version: Mapped[str] = mapped_column(String(50))
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    output: Mapped[dict] = mapped_column(JSON)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), unique=True, index=True)
    stage: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus), default=SubmissionStatus.UPLOADED)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
