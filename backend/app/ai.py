"""Versioned, narrowly scoped Luna operations for PRISM."""

import base64
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


class PerceivedAnswer(BaseModel):
    question_id: str
    transcription: str
    uncertain_segments: list[str] = []
    visual_notes: list[str] = []


class PerceptionResult(BaseModel):
    answers: list[PerceivedAnswer]


class GradeResult(BaseModel):
    awarded_marks: float = Field(ge=0)
    reason: str
    evidence_quotes: list[str]
    confidence: float = Field(ge=0, le=1)
    needs_review: bool


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
    client = AsyncOpenAI(max_retries=settings.openai_max_retries, timeout=settings.openai_timeout_seconds)
    prompt = f"""You are PRISM's document perception operation ({PERCEPTION_VERSION}).
Transcribe only what is visibly handwritten. Map it to these expected question identifiers when visible: {question_numbers}.
Preserve spelling, grammar, incorrect statements and incorrect formulas exactly. Never solve, improve, or correct the exam. Never infer invisible content.
Use [ILLEGIBLE] for unreadable text and [UNCERTAIN: option A | option B] for ambiguity. Note visible diagrams or equations without interpreting their correctness."""
    response = await client.responses.parse(model=MODEL, input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, image_content(path, mime_type)]}], text_format=PerceptionResult)
    return response.output_parsed


async def grade_criterion(path: str, mime_type: str, question: str, criterion: dict, transcription: str) -> GradeResult:
    client = AsyncOpenAI(max_retries=settings.openai_max_retries, timeout=settings.openai_timeout_seconds)
    prompt = f"""You are PRISM's rubric grading operation ({GRADING_VERSION}). Grade only this one criterion.
Question: {question}
Criterion: {criterion['title']} - {criterion['description']}
Maximum marks: {criterion['max_marks']}
Student transcription: {transcription}
Use the image as ground evidence. Award a score between zero and the maximum, quote evidence exactly, and flag uncertainty. Do not calculate totals."""
    response = await client.responses.parse(model=MODEL, input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, image_content(path, mime_type)]}], text_format=GradeResult)
    return response.output_parsed
