# PRISM Product Requirements Document

## Version

0.1 Hackathon MVP

## Product

PRISM

## Category

AI in Education / Assessment Intelligence

---

# 1. Executive Summary

PRISM is an AI-assisted assessment intelligence platform designed for physical, handwritten examinations.

Traditional paper evaluation requires teachers to manually read, interpret, grade and aggregate every student response.

Existing digital grading tools reduce some of this workload, but the key challenge remains:

> transforming handwritten assessment evidence into trustworthy educational intelligence.

PRISM addresses this through a multimodal workflow powered by GPT-5.6 Luna.

It transforms photographed or scanned exam papers into structured student answers, evaluates those answers against teacher-defined rubrics, provides evidence for each mark, flags uncertain decisions, allows teachers to interrogate and override AI judgments, and converts assessment results into longitudinal learning profiles and class-wide teaching insights.

PRISM is intentionally designed as:

**AI-assisted evaluation**

rather than:

**autonomous grading.**

The teacher remains the final decision-maker.

---

# 2. Problem Statement

Teachers evaluating physical examinations repeatedly perform several expensive tasks:

1. reading handwriting
2. interpreting incomplete answers
3. checking diagrams and formulas
4. mapping responses to marking rubrics
5. assigning partial credit
6. writing feedback
7. manually entering marks
8. identifying patterns across students
9. remembering recurring weaknesses over multiple exams

The final numeric score captures only a fraction of the educational information contained in the paper.

A student may score:

```text
68%
```

but this does not directly reveal:

- what they understand
- what misconceptions they have
- which prerequisite concept is weak
- which mistakes are repeated
- which concepts the whole class struggles with

PRISM turns assessment evidence into actionable teaching intelligence.

---

# 3. Product Vision

PRISM aims to make every evaluated paper answer three questions:

### For the teacher

> What did this student actually understand?

### For the student

> What specifically should I improve?

### For the class

> What should be taught differently next?

---

# 4. Product Principles

## 4.1 Evidence Before Authority

Every AI grading decision should have:

- a rubric criterion
- supporting student evidence
- an explanation
- confidence information

---

## 4.2 Teacher in Control

No disputed mark changes without explicit teacher confirmation.

---

## 4.3 Uncertainty Is a Feature

The system must be allowed to say:

```text
I am not confident.
```

rather than fabricate certainty.

---

## 4.4 Preserve Student Errors

The perception layer must not correct:

- grammar
- formulas
- terminology
- conceptual mistakes

The evaluator must grade what was actually written.

---

## 4.5 Separate Perception and Evaluation

Reading the paper and grading the paper are independent operations.

This improves:

- explainability
- debugging
- reliability
- auditing

---

## 4.6 Deterministic Where Possible

Use ordinary software for:

- arithmetic
- statistics
- validation
- database queries
- file manipulation

Use the language model only when semantic interpretation is necessary.

---

# 5. Target Users

## Primary User

Teacher / lecturer.

## Secondary Users

- teaching assistants
- department coordinators
- academic reviewers

## Future Users

Students receiving assessment feedback.

Students are not required as authenticated users in the MVP.

---

# 6. Primary Persona

## Lecturer

Handles:

- 30â100 students
- multiple written examinations
- descriptive answers
- formulas
- diagrams
- partial-credit marking

Pain points:

- repetitive grading
- inconsistent partial credit
- limited time for detailed feedback
- difficulty spotting class-wide patterns
- difficulty tracking misconception recurrence

---

# 7. User Stories

## Exam Setup

As a teacher, I want to create an examination and define marking criteria so that AI grading follows my assessment expectations.

## Upload

As a teacher, I want to photograph or upload handwritten answer sheets so that I do not have to manually digitize responses.

## Evaluation

As a teacher, I want PRISM to score each criterion separately so that I understand how the final score was determined.

## Evidence

As a teacher, I want every mark to reference evidence from the student's paper so that I can verify it.

## Review

As a teacher, I want uncertain decisions flagged automatically so I can focus my attention where it matters.

## Challenge

As a teacher, I want to ask why a mark was deducted so I can interrogate the model.

## Override

As a teacher, I want to override an AI recommendation so I remain the assessment authority.

## Student Insight

As a teacher, I want to see a student's recurring weaknesses across exams.

## Class Insight

As a teacher, I want to identify concepts the class struggles with.

## Teaching Recommendation

As a teacher, I want PRISM to suggest what to revise next based on assessment evidence.

---

# 8. Functional Requirements

## FR-01 Exam Creation

Teacher must be able to create an exam containing:

- exam name
- subject
- optional course
- total marks
- date
- questions
- question marks
- rubric criteria

---

## FR-02 Rubric Creation

Each question supports one or more rubric criteria.

Fields:

```text
criterion_id
title
description
maximum_marks
concept_tags
```

---

## FR-03 Submission Upload

Teacher must be able to upload:

- JPEG
- PNG
- PDF

A submission belongs to:

- student
- exam

---

## FR-04 Page Processing

System converts uploaded input into normalized page images.

Each page must retain:

```text
page_number
original_file
processed_file
width
height
```

---

## FR-05 Perception Extraction

Luna must extract structured answer information.

Required output:

```json
{
  "page_number": 1,
  "question_blocks": [
    {
      "question_id": "Q1",
      "transcription": "",
      "uncertain_segments": [],
      "visual_regions": [],
      "formula_regions": []
    }
  ]
}
```

---

## FR-06 Uncertainty Representation

Uncertain transcription should include:

```json
{
  "text": "covid",
  "alternatives": ["cold"],
  "confidence": 0.62
}
```

or comparable structured representation.

---

## FR-07 Original Evidence Retention

Every extracted answer must remain linked to:

- original page
- page number
- optional bounding box or crop

---

## FR-08 Grading

Each question is evaluated against its rubric.

Required output per criterion:

```text
maximum marks
awarded marks
reason
evidence
confidence
```

---

## FR-09 Score Validation

Backend must guarantee:

```text
0 <= awarded_marks <= maximum_marks
```

Question totals must equal the sum of criterion scores.

Final total must be calculated programmatically.

---

## FR-10 Review Flagging

A criterion should be flagged when:

- confidence below threshold
- transcription uncertainty exists
- missing visual evidence exists
- model explicitly requests human review

---

## FR-11 Teacher Re-Evaluation

Teacher may select a criterion and request re-evaluation.

The model receives:

- original image
- answer
- rubric
- existing evaluation
- teacher comment

Only selected criterion may change.

---

## FR-12 Teacher Override

Teacher may manually modify awarded marks.

Store:

```text
original_ai_marks
teacher_marks
override_reason
timestamp
```

---

## FR-13 Learning Profile

System aggregates rubric/concept performance by student.

Fields may include:

```text
concept
attempt_count
average_score
trend
frequent_errors
evidence_sources
```

---

## FR-14 Class Analytics

Aggregate:

- concept mastery
- question difficulty
- rubric failure frequency
- common misconceptions
- review frequency

---

## FR-15 Teacher Chat

Natural-language interface should answer questions using structured assessment data.

Example:

> Which students struggled with Bayes theorem?

Backend retrieves matching student/concept records before invoking Luna.

---

# 9. AI Architecture

## Runtime Model

Only:

**GPT-5.6 Luna**

---

# 10. AI Task 1: Perception

### Input

- page image
- optional exam structure

### Purpose

Faithfully convert physical writing into structured information.

### Constraints

Do not:

- solve questions
- improve student writing
- correct errors
- infer invisible text

---

# 11. AI Task 2: Evaluation

### Input

- question
- rubric
- transcription
- original answer crop
- associated visuals

### Purpose

Evaluate only according to rubric.

### Required behavior

- criterion-by-criterion assessment
- evidence-backed reasoning
- uncertainty
- no arithmetic beyond criterion score suggestion

---

# 12. AI Task 3: Assessment Q&A

Provide teacher-facing explanations grounded only in:

- submission
- rubric
- AI evaluation
- original evidence
- teacher overrides

---

# 13. AI Task 4: Student Learning Analysis

Luna receives summarized historical performance.

It must identify only educational patterns.

Prohibited classifications include:

- intelligence
- IQ
- laziness
- personality
- motivation
- mental health
- honesty

---

# 14. AI Task 5: Class Analysis

Input should preferably be aggregated backend statistics rather than all raw papers.

Example:

```json
{
  "concepts": [
    {
      "name": "Bayes theorem",
      "students_attempted": 30,
      "mean_score": 0.51,
      "common_errors": []
    }
  ]
}
```

Luna converts this into readable teaching insights.

---

# 15. Data Model

## Teacher

```text
id
name
email
```

Authentication may be mocked for MVP.

---

## Student

```text
id
name
identifier
```

---

## Exam

```text
id
title
subject
date
total_marks
created_at
```

---

## Question

```text
id
exam_id
number
text
max_marks
```

---

## RubricCriterion

```text
id
question_id
title
description
max_marks
concept
```

---

## Submission

```text
id
exam_id
student_id
status
created_at
total_score
```

---

## SubmissionPage

```text
id
submission_id
page_number
original_path
processed_path
```

---

## Answer

```text
id
submission_id
question_id
transcription
confidence
```

---

## EvidenceRegion

```text
id
answer_id
page_id
bbox
text
type
```

---

## CriterionEvaluation

```text
id
answer_id
criterion_id
ai_marks
teacher_marks
reason
confidence
needs_review
```

---

## TeacherOverride

```text
id
evaluation_id
previous_marks
new_marks
reason
created_at
```

---

# 16. Suggested API

## Exams

```text
POST /api/exams
GET /api/exams
GET /api/exams/:id
```

## Questions

```text
POST /api/exams/:id/questions
```

## Submissions

```text
POST /api/exams/:id/submissions
GET /api/submissions/:id
```

## Processing

```text
POST /api/submissions/:id/process
```

## Grading

```text
POST /api/submissions/:id/grade
```

## Re-Evaluation

```text
POST /api/evaluations/:id/review
```

## Override

```text
PATCH /api/evaluations/:id
```

## Students

```text
GET /api/students/:id/profile
```

## Class Analytics

```text
GET /api/exams/:id/analytics
```

## Assistant

```text
POST /api/assistant/query
```

---

# 17. Processing State Machine

```text
UPLOADED
   â
PREPROCESSING
   â
TRANSCRIBING
   â
STRUCTURED
   â
GRADING
   â
REVIEW_REQUIRED
   â
COMPLETED
```

Possible failure state:

```text
PROCESSING_FAILED
```

Allow retry.

---

# 18. UI Requirements

## Dashboard

Display:

- exams
- pending reviews
- recently evaluated submissions
- class alerts

---

## Submission Review

Two-column desktop layout.

Left:

- original paper

Right:

- question
- transcription
- rubric
- score
- confidence
- explanation

---

## Visual Confidence Language

Avoid false precision.

Recommended:

```text
High confidence
Medium confidence
Review recommended
```

The raw numeric confidence may exist internally.

---

# 19. Teacher Chat Context Rules

Teacher chat must not receive the entire database blindly.

Backend should first determine intent.

Examples:

```text
"Why did John lose marks in Q4?"
```

Retrieve:

- John
- Q4
- grading
- evidence
- rubric

For:

```text
"What was the weakest class topic?"
```

Retrieve aggregate concept statistics.

---

# 20. Non-Functional Requirements

## Performance

Target:

- page transcription approximately 15â30 seconds
- pages may process concurrently
- grading should begin as soon as relevant pages are ready

---

## Reliability

Failed Luna calls:

- retry with exponential backoff
- maximum sensible retry count
- preserve processing state

---

## Cost

Cache successful AI results.

Never repeat Luna processing unnecessarily.

Use hashes of:

```text
image
+
prompt version
+
model
```

where practical.

---

## Auditability

Store:

- model name
- prompt version
- response
- timestamp
- teacher overrides

---

# 21. Security

For hackathon MVP:

- API key server-side only
- never expose API key to browser
- uploaded exams should not be public
- sanitize filenames
- validate MIME types
- restrict upload size

---

# 22. Privacy

Avoid exposing real student identifiers during demos.

Prefer synthetic names.

Do not send unnecessary student metadata to the model.

For example, Luna does not need:

```text
student phone number
email
address
```

to grade an answer.

---

# 23. Failure Handling

## Unreadable Paper

Show:

```text
Some regions could not be confidently transcribed.

Teacher review required.
```

## Missing Question Mapping

Allow teacher to manually assign answer to question.

## Model Failure

Retry.

If repeated:

```text
Processing failed.
Manual review required.
```

---

# 24. Metrics for Hackathon Demo

Track:

- pages processed
- processing time
- questions evaluated
- criteria evaluated
- percentage flagged for review
- teacher overrides
- common misconceptions

These make the prototype feel like a system rather than a single API call.

---

# 25. MVP Acceptance Tests

## Test 1

Given a handwritten page, Luna returns meaningful transcription.

## Test 2

Incorrect student terminology is preserved rather than corrected.

## Test 3

Question rubric produces criterion scores.

## Test 4

Criterion marks never exceed maximum.

## Test 5

Teacher can inspect original paper.

## Test 6

Teacher can ask why marks were deducted.

## Test 7

Teacher can request criterion re-evaluation.

## Test 8

Teacher can reject AI recommendation.

## Test 9

Student profile derives concept performance.

## Test 10

Class analytics identifies weakest concepts.

---

# 26. Demo Dataset

Prepare before judging:

- 1 exam
- 4â5 questions
- 5â10 students
- 3â5 pages per student

At least one response should contain:

- normal prose
- an equation
- a table or structured response
- a diagram/graph
- intentionally ambiguous handwriting

Pre-process most demo papers before the pitch.

Keep one unseen paper for live processing.

This protects the demo from internet latency while still proving real functionality.

---

# 27. Demo Sequence

### 0:00â0:30

Problem.

> Teachers spend hours converting rich assessment evidence into a single number.

### 0:30â1:00

Upload handwritten paper.

### 1:00â1:30

Show PRISM reading it.

### 1:30â2:30

Show criterion-based evaluation.

### 2:30â3:30

Challenge AI decision.

### 3:30â4:15

Show student learning profile.

### 4:15â5:00

Show class misconception analytics.

Finish with:

> PRISM doesn't just grade what students wrote. It helps teachers understand what students learned.

---

# 28. Future Scope

After hackathon:

- optimized local OCR
- Paddle/Qianfan benchmark continuation
- LMS integration
- institutional calibration
- teacher-specific grading examples
- model ensembles
- second-pass verification
- handwritten mathematical reasoning engine
- advanced diagram evaluation
- bulk scanner integration
- mobile scanning app
- production identity/access controls
- encrypted document storage
- student feedback portal

---

# 29. Core Differentiator

PRISM should not compete primarily on:

> "Our AI can OCR handwriting."

OCR is infrastructure.

The differentiator is:

> **Every mark is interrogable, evidence-backed and transformed into learning intelligence.**

That is the product.