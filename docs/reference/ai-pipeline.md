# AI Pipeline

PRISM separates perception, grading, review, import, and assistant work into versioned structured operations. Runtime calls use only the configured OpenAI models allowed by repository policy.

## Model Routing

| Operation | Default model | Prompt | Output |
| --- | --- | --- | --- |
| Perception | `gpt-5.6-luna` | `perception_v2` | Page quality, mapped fragments, uncertainty, regions, formulas, confidence |
| Grading | `gpt-5.6-luna` | `grading_v3` | One criterion's marks, reason, evidence, confidence, blocking reason |
| Review | `gpt-4o` | `review_v3` | Unapplied proposed marks, reason, evidence, confidence |
| Exam import | `gpt-4o` | `exam_import_v1` | Exam metadata, questions, proposed criteria, clarification warnings |
| Answer-key import | `gpt-4o` | `answer_key_import_v1` | Reference answers matched to expected question identifiers |
| Teacher assistant | `gpt-4o-mini` | `teacher_chat_v1` | Grounded prose and named sources |

The code defines `student_profile_v1` and `class_analysis_v1` constants but does not implement corresponding AI calls. Current profile and class numerical analytics are deterministic.

## Perception

Each normalized page is submitted with expected question identifiers and limited continuation context. The prompt requires the model to:

- preserve spelling and grammar
- preserve incorrect statements and formulas
- avoid answering the exam
- avoid improving wording
- avoid inferring invisible content
- use `[ILLEGIBLE]` for unreadable content
- use structured alternatives such as `[UNCERTAIN: covid | cold]` for ambiguity

The output can contain mapped answer fragments, unmapped visible writing, page quality, a rescan recommendation, visual regions, formulas, uncertainty, and confidence.

The backend accepts exact normalized question identifiers. A continuation can attach to a question only when that question appeared on the immediately preceding page. Visible writing that cannot be mapped creates a blocking submission review signal.

## Grading

Grading runs once per rubric criterion for each mapped question answer. Inputs include:

- question text
- criterion title, description, concept, and maximum marks
- transcribed answer fragments
- original relevant page images
- optional answer key

The backend clamps `awarded_marks` to the inclusive range from zero to criterion maximum. It stores the reason, confidence, blocking reason, and evidence references. It then recalculates totals from effective criterion marks.

Questions with no mapped answer currently receive no criterion evaluation rows. Their absent marks contribute zero to the submission total, but analytics based on evaluation rows can undercount omissions.

## Review

A teacher challenge includes the current decision, teacher comment, original relevant pages, transcription, rubric, and optional answer key. The model returns a proposal.

```text
current effective mark
    -> AI review suggestion stored as pending
    -> teacher accepts or rejects
    -> accepted suggestion creates a teacher override
```

The review operation never directly modifies an official mark. Rejecting keeps the current mark. A teacher can also enter a direct bounded override or complete a review without changing the mark.

## Confidence And Review State

`AI_REVIEW_THRESHOLD` defaults to `0.75`.

- A criterion-level blocking reason creates `review_required`.
- Low confidence or transcription uncertainty creates `review_recommended`.
- Recommended review does not block completion.
- Required unresolved reviews and unmapped writing block a clean completed state.

Confidence is model-reported and is not presented as a calibrated statistical probability.

## Caching

Perception cache identity includes:

- image hash
- operation and prompt version
- page number
- expected question identifiers
- continuation context

Exam import cache identity includes the raw file hash, operation, and prompt version.

Current limitations:

- cache lookup does not include model name
- grading, review, answer-key import, and assistant queries have no artifact cache
- token usage and estimated cost are not persisted
- artifact duration exists as a field but is not populated

## Retries And Concurrency

The OpenAI client uses `OPENAI_TIMEOUT_SECONDS` and `OPENAI_MAX_RETRIES`. A processing exception is caught and persisted as a failed submission/job state.

`AI_CONCURRENCY` is configured but not used. Page perception and criterion grading are sequential in the current implementation. There is no application-level retry loop beyond explicit retry routes and OpenAI SDK retries.

## Deterministic Boundaries

AI does not calculate or own:

- criterion bounds
- question and exam maximum marks
- submission totals and percentages
- class or exam averages
- concept mastery
- filtering, sorting, authentication, or routing

The backend calculates these values after validating structured model output.

## Original Image Contract

Original source bytes remain linked to every page. Grading and review receive original relevant image data when practical. The transcription is an aid, not ground truth. Evidence can be page-level or region-linked; perfect OCR bounding boxes are not required.

## Failure Behavior

Malformed structured outputs and OpenAI request errors fail the active processing operation. The submission records an error and transitions to `failed` instead of crashing the API process. Because processing runs as an in-process background task, API restarts can still interrupt work before failure state is persisted.
