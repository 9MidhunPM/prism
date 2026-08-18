"""Versioned, narrowly scoped Luna operations for PRISM."""

import base64
import json
from typing import Literal
from pathlib import Path

import fitz
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from .settings import get_settings

settings = get_settings()
MODEL = settings.luna_model
PERCEPTION_VERSION = "perception_v2"
GRADING_VERSION = "grading_v2"
REVIEW_VERSION = "review_v2"
STUDENT_PROFILE_VERSION = "student_profile_v1"
CLASS_ANALYSIS_VERSION = "class_analysis_v1"
TEACHER_CHAT_VERSION = "teacher_chat_v1"
EXAM_IMPORT_VERSION = "exam_import_v1"


def model_for(operation: str) -> str:
    """Keep model choice explicit and stable for reproducible artifact keys."""
    if operation in {"perception", "grading"}:
        return settings.luna_model
    if operation in {"review", "exam_import"}:
        return settings.gpt4o_model
    return settings.gpt4o_mini_model


def client() -> AsyncOpenAI:
    if not settings.openai_enabled:
        raise RuntimeError("OPENAI_API_KEY is required for Luna operations.")
    return AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value(), max_retries=settings.openai_max_retries, timeout=settings.openai_timeout_seconds)


class PerceivedAnswer(BaseModel):
    question_id: str | None = None
    mapping_basis: Literal["visible_identifier", "previous_page_continuation", "unknown"]
    mapping_confidence: float = Field(ge=0, le=1)
    sequence: int = Field(ge=1)
    transcription: str
    confidence: float = Field(ge=0, le=1)
    uncertain_segments: list["UncertainSegment"] = []
    visual_regions: list["VisualRegion"] = []
    formula_regions: list["VisualRegion"] = []


class UncertainSegment(BaseModel):
    text: str
    alternatives: list[str] = []
    confidence: float = Field(ge=0, le=1)


class VisualRegion(BaseModel):
    kind: str
    description: str
    bbox: list[float] | None = None


class PerceptionResult(BaseModel):
    answers: list[PerceivedAnswer]
    quality_status: str = "readable"
    quality_reason: str | None = None
    quality_confidence: float = Field(default=1, ge=0, le=1)
    requires_rescan: bool = False


class GradeResult(BaseModel):
    awarded_marks: float = Field(ge=0)
    reason: str
    evidence: list["GradeEvidence"]
    confidence: float = Field(ge=0, le=1)
    blocking_reason: Literal["unreadable_evidence", "missing_evidence", "irreconcilable_ambiguity"] | None = None


class GradeEvidence(BaseModel):
    page_number: int = Field(ge=1)
    quote: str


class ReviewResult(BaseModel):
    suggested_marks: float = Field(ge=0)
    reason: str
    evidence_quotes: list[str]
    confidence: float = Field(ge=0, le=1)


class TeacherAnswer(BaseModel):
    answer: str
    sources: list[str]


class ImportedCriterion(BaseModel):
    title: str
    description: str
    max_marks: float = Field(gt=0)
    concept: str


class ImportedQuestion(BaseModel):
    number: str
    text: str
    max_marks: float | None = Field(default=None, gt=0)
    criteria: list[ImportedCriterion]
    confidence: float = Field(ge=0, le=1)


class ExamImportResult(BaseModel):
    title: str
    subject: str
    questions: list[ImportedQuestion]
    warnings: list[str] = []


def image_content(path: str, mime_type: str) -> dict:
    if mime_type == "application/pdf":
        document = fitz.open(path)
        if len(document) == 0:
            raise ValueError("The PDF has no pages.")
        pixmap = document[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        encoded = base64.b64encode(pixmap.tobytes("png")).decode("utf-8")
        return {"type": "input_image", "image_url": f"data:image/png;base64,{encoded}"}
    encoded = base64.b64encode(Path(path).read_bytes()).decode("utf-8")
    return {"type": "input_image", "image_url": f"data:{mime_type};base64,{encoded}"}


async def perceive_page(path: str, mime_type: str, question_numbers: list[str], page_number: int, previous_page_answers: list[dict]) -> PerceptionResult:
    openai_client = client()
    prompt = f"""You are PRISM's document perception operation ({PERCEPTION_VERSION}) for page {page_number}.
Transcribe only what is visibly handwritten. Expected question identifiers: {question_numbers}. The immediately previous page ended with these accepted answer fragments: {json.dumps(previous_page_answers)}.
For each visible fragment, return a sequence number and mapping_basis. Use visible_identifier only for a visibly associated identifier. Use previous_page_continuation only when an unlabelled fragment clearly continues a listed previous-page answer; never infer this from similar subject matter. Use unknown with question_id null when visible writing cannot be mapped safely. A page can contain a continuation followed by a newly labelled answer. Do not omit visible writing because its mapping is unknown.
Preserve spelling, grammar, incorrect statements and incorrect formulas exactly. Never solve, improve, or correct the exam. Never infer invisible content.
Use [ILLEGIBLE] for unreadable text and [UNCERTAIN: option A | option B] for ambiguity. For every uncertain segment, return the exact text, alternatives, and confidence. Record visibly present diagrams, tables, graphs, and formulas as visual/formula regions without judging correctness. Bounding boxes, when visible, are normalized [left, top, right, bottom] values from 0 to 1. Assess the overall page as readable, blurry, or unreadable. Set requires_rescan true only when the page cannot be responsibly assessed from the supplied scan and state the visual reason."""
    response = await openai_client.responses.parse(model=model_for("perception"), input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, image_content(path, mime_type)]}], text_format=PerceptionResult)
    return response.output_parsed


async def grade_criterion(pages: list[tuple[int, str, str]], question: str, criterion: dict, transcription: str) -> GradeResult:
    openai_client = client()
    prompt = f"""You are PRISM's rubric grading operation ({GRADING_VERSION}). Grade only this one criterion.
Question: {question}
Criterion: {criterion['title']} - {criterion['description']}
Maximum marks: {criterion['max_marks']}
Student transcription, labelled by page: {transcription}
Use every supplied image as ground evidence. Award a score between zero and the maximum. Every evidence item must quote exact evidence and identify its supplied page number. Set blocking_reason only when evidence is unreadable, missing, or irreconcilably ambiguous enough that a responsible mark cannot be finalized. Ordinary uncertainty belongs in confidence, not blocking_reason. Do not calculate totals."""
    content = [{"type": "input_text", "text": prompt}]
    for page_number, path, mime_type in pages:
        content.append({"type": "input_text", "text": f"Original paper page {page_number}:"})
        content.append(image_content(path, mime_type))
    response = await openai_client.responses.parse(model=model_for("grading"), input=[{"role": "user", "content": content}], text_format=GradeResult)
    return response.output_parsed


async def review_criterion(pages: list[tuple[int, str, str]], question: str, criterion: dict, transcription: str, current_marks: float, current_reason: str, teacher_comment: str) -> ReviewResult:
    openai_client = client()
    prompt = f"""You are PRISM's teacher review operation ({REVIEW_VERSION}). Re-evaluate only this criterion.
Question: {question}
Criterion: {criterion['title']} - {criterion['description']}
Maximum marks: {criterion['max_marks']}
Student transcription: {transcription}
Current suggested marks: {current_marks}
Current reason: {current_reason}
Teacher comment: {teacher_comment}
Use every supplied original-paper image as ground evidence. Return a suggested score between zero and the maximum, concise evidence-backed reasoning, and exact evidence quotes. Do not calculate totals and do not change any stored score."""
    content = [{"type": "input_text", "text": prompt}]
    for page_number, path, mime_type in pages:
        content.append({"type": "input_text", "text": f"Original paper page {page_number}:"})
        content.append(image_content(path, mime_type))
    response = await openai_client.responses.parse(model=model_for("review"), input=[{"role": "user", "content": content}], text_format=ReviewResult)
    return response.output_parsed


async def answer_teacher_question(question: str, concept_statistics: list[dict]) -> TeacherAnswer:
    openai_client = client()
    prompt = f"""You are PRISM's grounded teacher assistance operation ({TEACHER_CHAT_VERSION}).
Answer the teacher's question using only the supplied class statistics. Do not invent student traits, motivation, intelligence, cheating, or facts not provided. Give a concise instructional recommendation when appropriate.
Teacher question: {question}
Class statistics: {json.dumps(concept_statistics)}
Return the names of the statistics you used in sources."""
    response = await openai_client.responses.parse(
        model=model_for("teacher_chat"),
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        text_format=TeacherAnswer,
    )
    return response.output_parsed


async def import_exam_pages(pages: list[tuple[str, str]]) -> ExamImportResult:
    openai_client = client()
    prompt = f"""You are PRISM's exam-paper import operation ({EXAM_IMPORT_VERSION}).
Extract only the visible assessment metadata, questions, visible marks, and instructions from the supplied question-paper pages. Preserve wording, mathematical notation, and question identifiers exactly. Never answer the questions or invent missing marks.
Suggest concise rubric criteria that a teacher must review before saving. Each criterion must have a positive mark allocation and a concept label. When a question's visible maximum mark is unavailable, return null for question max_marks and add a warning. When suggested criterion marks do not add to a visible question maximum, add a warning. Return all questions in paper order."""
    content = [{"type": "input_text", "text": prompt}]
    content.extend(image_content(path, mime_type) for path, mime_type in pages)
    response = await openai_client.responses.parse(
        model=model_for("exam_import"),
        input=[{"role": "user", "content": content}],
        text_format=ExamImportResult,
    )
    return response.output_parsed
