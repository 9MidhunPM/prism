# Product Overview

PRISM assists teachers with evaluating physical handwritten examination papers while preserving the paper, rubric, evidence, and teacher decision as distinct records.

## Product Promise

```text
Physical paper
    -> retained page evidence
    -> faithful transcription and answer mapping
    -> criterion-level AI suggestion
    -> teacher review and authority
    -> released feedback and learning analytics
```

PRISM does not treat AI output as an official mark by itself. Numerical totals are calculated in application code, confidence is presented as a review signal rather than a calibrated probability, and a teacher can directly override a mark or challenge an AI decision.

## Roles

### Teacher

Teachers can:

- create and manage classes and student rosters
- provision student sign-in accounts
- create exams manually or import a question paper and answer key
- define criterion-level rubrics with marks and concepts
- upload answer papers or import folder-organized scans from Google Drive
- inspect original pages, transcription, marks, reasoning, and evidence
- override marks or request and decide on an AI review suggestion
- release or withdraw results from the student portal
- inspect student, class, exam, question, criterion, and concept analytics
- ask the assistant questions grounded in selected PRISM records

### Student

Students can:

- sign in with a teacher-provisioned account
- replace a temporary password on first sign-in
- view only results explicitly released by a teacher
- inspect criterion marks, reasons, and review recommendations
- inspect a learning profile calculated from released results

Students cannot view unreleased submissions or alter marks.

## Core Concepts

| Concept | Meaning |
| --- | --- |
| Exam | Assessment definition containing questions and rubrics |
| Rubric criterion | Independently scored requirement with maximum marks and a concept label |
| Submission | One student's physical answer paper for an exam |
| Page | Retained original and normalized page media |
| Answer | Transcribed content mapped to a question, with continuation support across pages |
| Evidence | Page reference and quote used to support a criterion decision |
| Evaluation | AI marks, optional teacher marks, reasoning, confidence, and review state |
| Review suggestion | Unapplied AI proposal created after a teacher challenge |
| Teacher override | Auditable teacher-authored change to the effective mark |

## Implemented Workflow

1. Create a class and add students, or create an exam without a class.
2. Create an exam and define questions and rubric criteria.
3. Upload one PDF or ordered image pages, or preview a Google Drive folder import.
4. PRISM normalizes pages, transcribes visible writing, maps answers, and evaluates each mapped criterion.
5. The backend validates every mark and calculates totals.
6. The teacher reviews original paper evidence and resolves required reviews.
7. The teacher can challenge, override, release, or withdraw the result.
8. Released evidence contributes to the student's portal; completed assessment evidence contributes to teacher analytics according to each endpoint's scope.

## Evidence And Confidence

The original page is ground evidence. Transcription helps navigation and grading but is not assumed to be infallible. The perception operation preserves student spelling, grammar, incorrect statements, and incorrect formulas. It uses `[ILLEGIBLE]` and `[UNCERTAIN: option | option]` rather than silently correcting ambiguous writing.

Criterion confidence below the configured threshold creates a review recommendation. A blocking issue creates a required review. Neither signal automatically changes or rejects a mark.

## Current Boundaries

- Processing runs as an in-process FastAPI background task, not a durable external worker.
- Media uses local filesystem cache plus database blobs; configured S3 values are not implemented.
- Exam questions and rubrics cannot be edited from the current frontend after creation.
- The assistant is single-turn and receives selected records plus deterministic statistics, not the entire database.
- Student and class narrative AI analysis is not implemented; numerical learning profiles are deterministic.
- Frontend automated tests are not currently present.

See [architecture](../reference/architecture.md) for system details and [teacher guide](teacher-guide.md) for the complete workflow.
