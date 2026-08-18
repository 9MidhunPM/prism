# AGENTS.md

## Project

PRISM

PRISM is a hackathon MVP for AI-assisted evaluation of physical handwritten examination papers.

The product:

1. accepts scanned/photographed answer papers
2. transcribes handwriting
3. maps responses to questions
4. evaluates answers against teacher-defined rubrics
5. provides evidence and confidence for every criterion
6. lets teachers challenge and override AI decisions
7. creates student learning profiles
8. provides class-level misconception analytics

The project must remain achievable within a 24-hour hackathon.

---

# 1. Primary Rule

BUILD THE SIMPLEST RELIABLE VERSION THAT DEMONSTRATES THE COMPLETE USER FLOW.

Do not over-engineer.

Whenever choosing between:

A. architecturally elegant but unfinished

and

B. simple but working

choose B.

---

# 2. Runtime AI Model

The application uses ONLY:

```text
gpt-5.6-luna
```

through the OpenAI API.

Do NOT introduce runtime calls to:

- GPT-5.6 Terra
- GPT-5.6 Sol
- GPT-4.x
- Gemini
- Claude
- Qianfan
- PaddleOCR
- Unlimited-OCR
- other external AI providers

unless the project owner explicitly changes this requirement.

Codex itself may use whatever coding model is available for development.

This restriction applies to the application runtime.

---

# 3. AI Responsibilities

Use Luna only for tasks requiring semantic or visual reasoning.

Allowed:

- handwriting transcription
- document understanding
- question/answer mapping
- formula interpretation
- visual interpretation
- rubric evaluation
- evidence explanation
- teacher Q&A
- student learning summaries
- class teaching recommendations

Do NOT use Luna for:

- arithmetic
- percentages
- averages
- database filtering
- sorting
- score totals
- file conversion
- image resizing
- basic validation
- authentication
- routing

Those must use deterministic code.

---

# 4. Separate AI Tasks

Never use one giant prompt for the entire pipeline.

Implement separate operations:

```text
perception
grading
review
student analysis
class analysis
```

Each operation should have:

- dedicated input schema
- dedicated output schema
- dedicated prompt
- version identifier

---

# 5. Structured Outputs

Prefer strict structured outputs whenever the Luna endpoint supports them.

Do not parse conversational text with fragile regex.

All production AI responses should ideally map into typed application models.

Example grading object:

```json
{
  "question_id": "Q4",
  "criteria": [
    {
      "criterion_id": "C1",
      "max_marks": 2,
      "awarded_marks": 1,
      "reason": "",
      "evidence": [],
      "confidence": 0.82
    }
  ],
  "needs_review": true
}
```

---

# 6. Never Trust Model Arithmetic

The backend calculates:

```text
question total
exam total
percentage
averages
concept mastery
class statistics
```

Never accept a model-generated total without recalculation.

Validate:

```text
0 <= awarded_marks <= max_marks
```

for every criterion.

---

# 7. Perception Rules

The handwriting extraction prompt must explicitly instruct the model:

- preserve grammar
- preserve spelling
- preserve incorrect statements
- preserve incorrect formulas
- do not answer the exam
- do not improve wording
- do not infer invisible content

For unreadable content use:

```text
[ILLEGIBLE]
```

For ambiguous content prefer structured uncertainty such as:

```text
[UNCERTAIN: covid | cold]
```

Never silently correct student mistakes.

---

# 8. Original Image Is Ground Evidence

Never discard the source image after transcription.

The source image must remain linked to:

- page
- answer
- visual region
- criterion evidence where applicable

During grading, provide the original relevant image/crop alongside the transcription when practical.

The transcription is an aid, not absolute ground truth.

---

# 9. Teacher Authority

AI grades are suggestions.

Teacher decisions override AI.

Never automatically apply a re-evaluated mark.

Re-evaluation flow must be:

```text
current mark
    â
AI suggestion
    â
teacher accepts/rejects
```

Store both versions.

---

# 10. Educational Profile Rules

Student profiles may contain:

- mastered concepts
- developing concepts
- weak concepts
- recurring misconceptions
- score trends
- rubric performance
- evidence references

Never infer:

- IQ
- intelligence level
- personality
- laziness
- motivation
- mental health
- cheating tendency
- honesty

Use educational evidence only.

---

# 11. Recommended Stack

Unless the repository already establishes another stack:

## Frontend

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Recharts
```

## Backend

Prefer:

```text
FastAPI
Python
```

if image processing and AI orchestration are easier there.

A Next.js-only architecture is acceptable if already implemented.

Do not create unnecessary services.

## Database

Hackathon:

```text
SQLite
```

or existing PostgreSQL.

Do not add Redis unless a concrete requirement appears.

## Files

Use local filesystem for hackathon unless storage is already configured.

---

# 12. Repository Structure

Suggested structure:

```text
prism/
âââ frontend/
â   âââ app/
â   âââ components/
â   âââ lib/
â   âââ types/
â
âââ backend/
â   âââ app/
â   â   âââ api/
â   â   âââ ai/
â   â   â   âââ perception.py
â   â   â   âââ grading.py
â   â   â   âââ review.py
â   â   â   âââ student_analysis.py
â   â   â   âââ class_analysis.py
â   â   âââ models/
â   â   âââ schemas/
â   â   âââ services/
â   â   âââ main.py
â   âââ tests/
â
âââ sample-data/
âââ scripts/
âââ AGENTS.md
âââ README.md
```

Do not reorganize an existing repository unnecessarily.

---

# 13. Core Domain Objects

Maintain clear models for:

```text
Teacher
Student
Exam
Question
RubricCriterion
Submission
SubmissionPage
Answer
EvidenceRegion
CriterionEvaluation
TeacherOverride
ConceptPerformance
```

Avoid generic JSON blobs where typed structure is straightforward.

AI raw responses may be stored separately for debugging.

---

# 14. Core Processing Pipeline

Implement:

```text
upload
  â
normalize pages
  â
transcribe pages
  â
map answers
  â
grade questions
  â
validate scores
  â
flag uncertain criteria
  â
save assessment
  â
update analytics
```

Each stage should be independently debuggable.

---

# 15. Processing Status

Use explicit states.

Example:

```text
uploaded
preprocessing
transcribing
grading
review_required
completed
failed
```

Frontend should display progress based on these states.

---

# 16. Concurrency

Luna page requests may be run concurrently in a controlled manner.

Do not fire an unlimited number of API requests.

Use a small configurable concurrency limit.

Example:

```text
2â4 concurrent page requests
```

respecting API rate limits.

---

# 17. Caching

Avoid repeating paid inference.

Cache successful processing where appropriate.

A useful cache identity may include:

```text
image hash
model
prompt version
operation
```

Do not regenerate identical transcription on every page refresh.

---

# 18. Prompt Versioning

Every important AI prompt should have a stable identifier.

Example:

```text
perception_v1
grading_v1
review_v1
student_profile_v1
class_analysis_v1
```

Store prompt version alongside model output.

This makes results reproducible and debuggable.

---

# 19. Error Handling

OpenAI failures must not crash the entire processing job.

Handle:

- timeout
- rate limit
- malformed response
- invalid image
- connection failure
- refusal
- schema validation error

Use bounded retries.

Never infinite-loop.

---

# 20. Logging

Log:

```text
submission_id
operation
model
duration
success/failure
token usage
estimated cost where available
```

NEVER log:

```text
OPENAI_API_KEY
```

Do not print secrets.

---

# 21. API Key

Read:

```text
OPENAI_API_KEY
```

from environment.

Never:

- hardcode the key
- commit `.env`
- expose it to frontend JavaScript
- return it from API endpoints

Ensure `.env` is gitignored.

---

# 22. Image Handling

Preserve originals.

For preprocessing:

- orientation correction
- conservative resizing
- optional cropping
- optional deskewing

Do not aggressively denoise or sharpen handwritten strokes.

Store original and processed images separately if preprocessing is used.

---

# 23. Evidence Design

Every criterion should ideally contain references to evidence.

Evidence object:

```text
page number
region
quoted transcription
visual reference
```

Exact OCR bounding-box precision is not mandatory for the hackathon.

Approximate page/crop reference is acceptable.

Do not block grading implementation because perfect pixel highlighting is unavailable.

---

# 24. Review Threshold

Use a configurable confidence threshold.

Suggested MVP:

```text
0.75
```

Do not pretend this represents calibrated statistical probability.

Present it as model confidence / review signal.

Low-confidence results should become:

```text
review recommended
```

not automatically rejected.

---

# 25. Analytics

Compute numerical analytics in code.

Examples:

```text
concept mastery
average question score
criterion failure rate
review rate
student score trend
```

Use Luna only to turn those statistics into human-readable observations or recommendations.

---

# 26. Teacher Chat

Do not dump the entire database into Luna.

Resolve the teacher's query to relevant entities first.

Example:

```text
"Why did Arun lose marks in Q3?"
```

Retrieve:

```text
Arun submission
Q3
rubric
evaluation
evidence
```

Then invoke Luna.

For:

```text
"What topic should I revise tomorrow?"
```

retrieve class concept statistics.

---

# 27. Tests

Prioritize tests for critical logic.

At minimum test:

## Score validation

Criterion cannot exceed max marks.

## Total calculation

Question and exam totals are deterministic.

## Override logic

Teacher override persists.

## AI schema validation

Malformed output is rejected safely.

## Upload validation

Unsupported file types are rejected.

Do not chase 100% coverage during the hackathon.

---

# 28. Demo Reliability Rules

The live demo is a product requirement.

Prepare:

- preprocessed example exams
- cached completed submissions
- one fresh paper for live processing

If the live Luna request fails, the presenter must still be able to continue using cached data.

Never make the entire demo dependent on one live request.

---

# 29. UI Priorities

Spend design effort on:

1. paper viewer
2. rubric marks
3. evidence
4. review interaction
5. class analytics

Do not spend excessive time on:

- landing page animations
- elaborate settings
- authentication screens
- decorative dashboards with no function

---

# 30. Visual Design Direction

The application should feel like:

```text
academic
precise
trustworthy
modern
```

not:

```text
generic AI chatbot
neon cyberpunk
```

Use clear status colors and typography.

Avoid clutter.

---

# 31. No Scope Expansion Without Reason

Do NOT spontaneously add:

- Redis
- Celery
- Kafka
- RabbitMQ
- Kubernetes
- GraphQL
- microservices
- Neo4j
- vector databases
- agent frameworks
- LangChain
- complex RAG systems

unless a concrete product requirement cannot be satisfied without them.

This project has a 24-hour build window.

---

# 32. Development Order

Implement in this exact priority unless blocked:

## Phase 1

Core data models.

## Phase 2

Exam + rubric creation.

## Phase 3

Paper upload.

## Phase 4

Luna perception.

## Phase 5

Question grading.

## Phase 6

Results UI.

## Phase 7

Evidence/review.

## Phase 8

Teacher challenge.

## Phase 9

Student profile.

## Phase 10

Class analytics.

## Phase 11

Demo polish.

---

# 33. When Something Is Hard

Prefer graceful simplification.

Examples:

If exact bounding boxes are difficult:

use page-level evidence.

If automatic question mapping is unreliable:

allow manual mapping.

If diagram understanding is uncertain:

flag for review.

If bulk processing is difficult:

demo five students.

Do not sacrifice the complete end-to-end flow for one technically impressive subproblem.

---

# 34. Definition of Done

The project is demo-ready when a teacher can:

```text
create exam
â define rubric
â upload handwriting
â receive transcription
â receive criterion-level grading
â inspect evidence
â challenge a decision
â accept/reject revision
â view student profile
â view class insights
```

If that works reliably, STOP ADDING CORE FEATURES.

Polish the demo.

---

# 35. Final Engineering Principle

PRISM's value is not:

```text
AI reads handwriting.
```

Its value is:

```text
Physical assessment
        â
explainable evidence
        â
teacher-controlled grading
        â
learning intelligence
```

Every engineering decision should support that story.