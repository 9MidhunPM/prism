# Architecture and data flow

## 1. Runtime shape

PRISM uses two application processes during local development:

```text
browser
   |
   | Next.js pages and client fetches
   v
frontend :3000
   |
   | JSON, multipart uploads, cookie session
   v
FastAPI :8000
   |                 \
   |                  \ optional S3-compatible media
   v
SQLite/PostgreSQL       retained original and processed pages
```

The frontend is in `frontend/`. The API, models, migrations, AI orchestration,
and tests are in `backend/`. No separate worker service is required for the MVP;
background tasks and a durable processing-job table provide the small amount of
asynchronous work the product needs.

## 2. Main domain objects

| Object | Meaning |
| --- | --- |
| `Teacher` / `Account` | Owner and authenticated identity |
| `ClassCohort` | Teacher-owned class or roster group |
| `Student` | Learner record and optional student account |
| `Exam` | Assessment definition and ownership boundary |
| `Question` | Prompt, visible marks, concept tags, answer key |
| `RubricCriterion` | Criterion-level scoring authority |
| `Submission` | One student's paper for one exam |
| `SubmissionPage` | Original and processed page media |
| `Answer` | Mapped transcription for a question |
| `CriterionEvaluation` | AI suggestion plus effective review state |
| `EvaluationEvidence` | Exact quote and page link supporting a criterion |
| `ReviewSuggestion` | Criterion-specific AI re-evaluation |
| `TeacherOverride` | Explicit teacher decision and reason |
| `ProcessingJob` | Current stage, attempts, and failure detail |
| `AIArtifact` | Versioned raw operation output and metadata |

## 3. Upload-to-result pipeline

```text
1. Validate MIME and file signature
2. Save original bytes
3. Create submission and page rows
4. Normalize orientation and dimensions
5. Create a processing job
6. Perceive pages concurrently, within configured limit
7. Map perceived answers to known questions
8. Grade each criterion independently
9. Validate mark bounds and evidence page references
10. Recalculate totals in backend code
11. Set completed, review_required, or failed
12. Aggregate student and class signals from stored evaluations
```

Failures are attached to the job and submission. A bounded retry clears the
old result where appropriate and restarts the relevant stage. A model timeout,
refusal, malformed response, invalid image, or schema error must not crash the
API process or silently produce a mark.

## 4. AI boundaries

### Perception

`perceive_page` reads page evidence. It does not evaluate correctness. The
prompt explicitly forbids grammar correction, answer completion, and invisible
content inference.

### Grading

`grade_criterion` sees the question, criterion, transcription, and relevant
page images. It returns a bounded suggestion and exact evidence references. It
does not calculate question or exam totals.

### Review

`review_criterion` receives only the disputed criterion and teacher comment. It
returns a suggestion; the teacher's accept/reject decision is a separate API
operation. The product contract requires this call to use Luna. The current
source still selects a legacy GPT-4o setting here; see [Known gaps](known-gaps.md).

### Analysis and chat

Student/profile and class/assistant operations receive computed rows and
selected evidence. They explain learning signals; they do not create new
numeric facts or psychological labels. The current teacher-chat selector also
needs to be made Luna-only before release.

## 5. Deterministic boundaries

Ordinary application code owns:

- file type and size validation;
- orientation, PDF rendering, resizing, and hashing;
- authentication, authorization, rate limits, and CSRF;
- database filtering and entity resolution;
- mark bounds and all totals;
- percentages, averages, mastery, failure rates, and review rates;
- state transitions, retries, and deletion cascades.

This separation makes AI behavior inspectable and keeps arithmetic reproducible.

## 6. Media lifecycle

The original upload is never treated as disposable. A page can have:

- original key and MIME type;
- processed preview key;
- durable binary fallback data;
- dimensions and image hash;
- page-level quality status.

The preview is used for model input and UI convenience. The original remains
the ground evidence for a teacher. When a file is deleted, the backend removes
only unreferenced media after dependent submission data is removed.

## 7. State and review model

Processing state and evaluation state are separate:

```text
processing: uploaded -> preprocessing -> transcribing -> structured -> grading
                                                            |             |
                                                            v             v
                                                         failed     completed/review_required
```

Criterion review keeps the current evaluation, the review suggestion, the
teacher decision, and optional override history. This lets the UI say exactly
which value is AI-suggested and which value is teacher-owned.

## 8. Code map

```text
backend/app/main.py       HTTP routes, orchestration, validation
backend/app/ai.py         typed AI schemas, prompts, model calls
backend/app/models.py     SQLAlchemy domain models
backend/app/auth.py       password and signed-session helpers
backend/app/settings.py   environment configuration and production checks
backend/app/database.py   SQLAlchemy engine/session setup
backend/alembic/          schema migrations
backend/tests/            scoring, auth, settings, schema, migration tests
frontend/app/             route-level teacher/student screens
frontend/components/      shell, sessions, import controls
frontend/lib/api.ts       browser API wrapper
```
