"""Versioned, narrowly scoped Luna operations for PRISM."""

import base64
import json
from pathlib import Path

import fitz
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from .settings import get_settings

settings = get_settings()
MODEL = settings.openai_model
PERCEPTION_VERSION = "perception_v1"
GRADING_VERSION = "grading_v1"
REVIEW_VERSION = "review_v1"
STUDENT_PROFILE_VERSION = "student_profile_v1"
CLASS_ANALYSIS_VERSION = "class_analysis_v1"
TEACHER_CHAT_VERSION = "teacher_chat_v1"
EXAM_IMPORT_VERSION = "exam_import_v1"


def client() -> AsyncOpenAI:
    if not settings.openai_enabled:
        raise RuntimeError("OPENAI_API_KEY is required for Luna operations.")
    return AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value(), max_retries=settings.openai_max_retries, timeout=settings.openai_timeout_seconds)


class PerceivedAnswer(BaseModel):
    question_id: str
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


class GradeResult(BaseModel):
    awarded_marks: float = Field(ge=0)
    reason: str
    evidence_quotes: list[str]
    confidence: float = Field(ge=0, le=1)
    needs_review: bool


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


async def perceive_page(path: str, mime_type: str, question_numbers: list[str]) -> PerceptionResult:
    openai_client = client()
    prompt = f"""You are PRISM's document perception operation ({PERCEPTION_VERSION}).
Transcribe only what is visibly handwritten. Map it to these expected question identifiers when visible: {question_numbers}.
Preserve spelling, grammar, incorrect statements and incorrect formulas exactly. Never solve, improve, or correct the exam. Never infer invisible content.
Use [ILLEGIBLE] for unreadable text and [UNCERTAIN: option A | option B] for ambiguity. For every uncertain segment, return the exact text, alternatives, and confidence. Record visibly present diagrams, tables, graphs, and formulas as visual/formula regions without judging correctness. Bounding boxes, when visible, are normalized [left, top, right, bottom] values from 0 to 1."""
    response = await openai_client.responses.parse(model=MODEL, input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, image_content(path, mime_type)]}], text_format=PerceptionResult)
    return response.output_parsed


async def grade_criterion(path: str, mime_type: str, question: str, criterion: dict, transcription: str) -> GradeResult:
    openai_client = client()
    prompt = f"""You are PRISM's rubric grading operation ({GRADING_VERSION}). Grade only this one criterion.
Question: {question}
Criterion: {criterion['title']} - {criterion['description']}
Maximum marks: {criterion['max_marks']}
Student transcription: {transcription}
Use the image as ground evidence. Award a score between zero and the maximum, quote evidence exactly, and flag uncertainty. Do not calculate totals."""
    response = await openai_client.responses.parse(model=MODEL, input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, image_content(path, mime_type)]}], text_format=GradeResult)
    return response.output_parsed


async def review_criterion(path: str, mime_type: str, question: str, criterion: dict, transcription: str, current_marks: float, current_reason: str, teacher_comment: str) -> ReviewResult:
    openai_client = client()
    prompt = f"""You are PRISM's teacher review operation ({REVIEW_VERSION}). Re-evaluate only this criterion.
Question: {question}
Criterion: {criterion['title']} - {criterion['description']}
Maximum marks: {criterion['max_marks']}
Student transcription: {transcription}
Current suggested marks: {current_marks}
Current reason: {current_reason}
Teacher comment: {teacher_comment}
Use the original image as ground evidence. Return a suggested score between zero and the maximum, concise evidence-backed reasoning, and exact evidence quotes. Do not calculate totals and do not change any stored score."""
    response = await openai_client.responses.parse(model=MODEL, input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, image_content(path, mime_type)]}], text_format=ReviewResult)
    return response.output_parsed


async def answer_teacher_question(question: str, concept_statistics: list[dict]) -> TeacherAnswer:
    openai_client = client()
    prompt = f"""You are PRISM's grounded teacher assistance operation ({TEACHER_CHAT_VERSION}).
Answer the teacher's question using only the supplied class statistics. Do not invent student traits, motivation, intelligence, cheating, or facts not provided. Give a concise instructional recommendation when appropriate.
Teacher question: {question}
Class statistics: {json.dumps(concept_statistics)}
Return the names of the statistics you used in sources."""
    response = await openai_client.responses.parse(
        model=MODEL,
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
        model=MODEL,
        input=[{"role": "user", "content": content}],
        text_format=ExamImportResult,
    )
    return response.output_parsed
