# Domain Model

PRISM persists assessment data as typed SQLAlchemy models in `backend/app/models.py`. IDs are UUID strings and timestamps are UTC.

## Identity And Roster

| Entity | Purpose | Key relationships |
| --- | --- | --- |
| `Teacher` | Owns the educational workspace | Has classes, exams, Drive batches, and a login account |
| `Account` | Login identity and password state | Belongs to one intended teacher or student |
| `AuthSession` | Opaque browser session and CSRF state | Belongs to an account; supports expiration and revocation |
| `ClassCohort` | Teacher-owned roster container | Has a primary student roster and exams |
| `Student` | Learner identity and primary class | Has submissions, optional account, and secondary memberships |
| `ClassMembership` | Adds a student to another class | Unique class/student pair |

A student's `class_id` is the primary class. Secondary classes use `ClassMembership`. Some current analytics scope only the primary class, so the distinction affects results.

## Assessment Definition

| Entity | Purpose | Key relationships |
| --- | --- | --- |
| `Exam` | Assessment metadata and optional class | Belongs to a teacher; has questions and submissions |
| `Question` | Ordered prompt and optional answer key | Belongs to an exam; has rubric criteria |
| `RubricCriterion` | Independently scored requirement | Belongs to a question; stores maximum marks and concept |

Exam and question maxima are derived by summing criterion maxima. They are not trusted from AI output.

## Paper And Evidence

| Entity | Purpose | Key relationships |
| --- | --- | --- |
| `Submission` | One student's paper for one exam | Has pages, answers, processing job, status, score, and release state |
| `SubmissionPage` | Original and normalized page media | Belongs to a submission; may carry quality and rescan metadata |
| `Answer` | Transcribed fragment mapped to a question | Belongs to a submission and page; question may be null when unmapped |
| `EvidenceRegion` | Perception-time visual/text region | Belongs to an answer and page |
| `CriterionEvaluation` | AI and teacher mark state for one criterion | Belongs to an answer and rubric criterion |
| `EvaluationEvidence` | Evidence quote and page reference for a decision | Belongs to an evaluation and page |

One question can have answer fragments on multiple pages. Continuation mapping is accepted only when the referenced question was accepted on the immediately preceding page.

## Teacher Authority And Audit

| Entity | Purpose | Application behavior |
| --- | --- | --- |
| `TeacherOverride` | Records a teacher-authored mark transition | Created by direct override or accepted AI proposal |
| `ReviewSuggestion` | Stores a pending AI re-evaluation | Does not alter marks until accepted |
| `AIArtifact` | Stores selected structured AI results and cache identity | Used for perception and exam-import cache lookup |
| `ProcessingJob` | Tracks submission processing stage and attempts | One-to-one with a submission; execution remains in-process |

An evaluation's effective mark is:

```text
teacher_marks when present
otherwise ai_marks
```

Reprocessing clears derived submission data, including evaluations, evidence, review suggestions, teacher overrides, and artifacts. It is therefore not an immutable historical replay operation in the current implementation.

## Google Drive Import

| Entity | Purpose |
| --- | --- |
| `DriveImportBatch` | Teacher/exam-scoped persisted preview and batch state |
| `DriveImportItem` | Student-folder match, assignment choice, and JSON page manifest |

OAuth access tokens are request inputs and are not persisted in these entities.

## Lifecycle Fields

Many teacher-owned records support archive state. Submission also tracks:

- processing status
- calculated total marks
- source hash for deduplication
- release state and release time
- latest processing error
- created and updated time

Deletion is implemented as manually ordered deep deletion because the models do not define ORM cascades or database `ON DELETE` rules.

## Relationship Overview

```text
Teacher
|-- ClassCohort
|   |-- Student (primary roster)
|   `-- ClassMembership -- Student
|-- Exam
|   |-- Question
|   |   `-- RubricCriterion
|   `-- Submission -- Student
|       |-- SubmissionPage
|       |-- Answer -- Question
|       |   `-- EvidenceRegion
|       |-- CriterionEvaluation -- RubricCriterion
|       |   |-- EvaluationEvidence -- SubmissionPage
|       |   |-- TeacherOverride
|       |   `-- ReviewSuggestion
|       |-- ProcessingJob
|       `-- AIArtifact
`-- DriveImportBatch
    `-- DriveImportItem

Account
`-- AuthSession
```

## Data Integrity

Application code validates ownership, mark bounds, and delete order. The schema contains foreign keys and uniqueness constraints but does not contain check constraints for all domain invariants. Service logic and tests are therefore part of the integrity boundary.
