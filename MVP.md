# PRISM MVP specification

The MVP demonstrates one complete story: a teacher creates an assessment,
reviews a handwritten paper with explainable AI suggestions, makes the final
decision, and learns what to teach next. The build remains intentionally small
enough for a 24-hour hackathon.

## 1. Demo outcome

```text
exam and rubric
    -> paper upload
    -> page processing
    -> transcription and question mapping
    -> criterion marks with evidence
    -> teacher challenge and decision
    -> student profile
    -> class insight
```

The visible product value is not simply “AI reads handwriting.” It is the
combination of original evidence, explainable suggestions, and teacher control.

## 2. MVP feature slices

### Slice A — Exam and rubric

Create a title, subject, optional date/class, question text, marks, concepts,
and criteria. A criterion is the unit of grading and the unit of review.

### Slice B — Paper intake

Upload a JPEG, PNG, or PDF. Show the selected pages before submit. Retain the
original bytes and create a conservative preview for downstream processing.

### Slice C — Perception

Read pages with `gpt-5.6-luna` using a dedicated perception prompt. Preserve
errors and uncertainty. Return typed page results and stable prompt metadata.

### Slice D — Evaluation

Grade each criterion independently. Show awarded marks, maximum marks,
reasoning, evidence quote, source page, and confidence. Compute totals in code.

### Slice E — Review

Let the teacher request a review for one criterion, inspect the suggestion, and
accept or reject it. Allow an explicit teacher override with a reason. Preserve
the evaluation history.

### Slice F — Learning intelligence

Show a student profile and class analytics derived from saved evaluations. Use
the model only to explain retrieved statistics in plain language.

### Slice G — Assistant

Allow a teacher to ask a grounded question such as “Which concept should I
revise tomorrow?” Resolve class statistics first, then call the teacher-chat
operation with only the relevant context.

## 3. Hard reliability rules

- The application runtime uses `gpt-5.6-luna` only.
- Every model response maps to a typed schema or the operation fails safely.
- No model-generated total is trusted.
- `awarded_marks` is clamped or rejected if it cannot satisfy the criterion
  bounds; the stored result must never exceed `max_marks`.
- Review suggestions never change a teacher mark automatically.
- Original paper images remain available wherever evidence is shown.
- Inference is bounded by a small concurrency limit and bounded retries.
- A cached completed submission is always available for a live demo fallback.

## 4. Recommended demo dataset

Use one assessment with four or five questions and five synthetic students.
Include at least:

- a clean answer with a high-confidence full mark;
- a partially correct answer with a visible misconception;
- a formula or diagram that needs a page reference;
- one low-confidence or ambiguous answer that triggers review;
- a class pattern that supports a clear teaching recommendation.

Synthetic data must be clearly labeled as synthetic. Do not use a real student's
name or paper in a public demo without permission.

## 5. What can be simplified

| Hard problem | MVP simplification |
| --- | --- |
| Exact handwriting boxes | Page-level evidence plus approximate region |
| Perfect question mapping | Manual correction or review-required state |
| Bulk processing | Five demo students and controlled concurrency |
| Live AI outage | Cached completed submission |
| Complex file storage | Local filesystem in development |
| Advanced analytics | Deterministic aggregates over criterion rows |
| Rich student portal | Released results and profile only |

## 6. Definition of done

The MVP is done when a teacher can perform the full path without leaving the
application:

1. Sign in.
2. Create or open a class.
3. Create an exam and rubric.
4. Upload a paper.
5. Watch processing status change.
6. Inspect original page, transcription, rubric decision, evidence, and
   confidence.
7. Challenge one criterion.
8. Accept/reject the suggestion or override the mark.
9. See the saved history.
10. Open a student profile and class analytics.
11. Ask one grounded teaching question.

Once this path is reliable, spend remaining time on copy, loading states,
empty states, accessibility, and demo rehearsal rather than new infrastructure.
