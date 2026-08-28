# Processing States

Submission and processing-job states are defined by `ProcessingStatus` in `backend/app/models.py`.

## State Reference

| State | Meaning | Expected next action |
| --- | --- | --- |
| `uploaded` | Submission and page records exist | Queue or begin preprocessing |
| `preprocessing` | Page validation/normalization stage | Continue to perception |
| `transcribing` | AI is reading and mapping page content | Continue through all pages |
| `structured` | Reserved structured-answer stage | Defined but not currently assigned by processing code |
| `grading` | Mapped answers are evaluated against criteria | Validate and persist result |
| `review_required` | Assessment finished with unresolved blocking evidence | Teacher reviews and resolves issues |
| `completed` | Processing finished without unresolved blocking review | Teacher verifies and may release |
| `rescan_required` | Submission-level rescan state | Replace/retry when supported |
| `failed` | Processing ended with an error | Inspect error and retry when supported |

## Normal Flow

```text
uploaded
  -> preprocessing
  -> transcribing
  -> grading
  -> completed
```

The task may instead end in `review_required` or `failed`.

## Review State Versus Processing State

Criterion evaluations separately track review signals:

- `none`
- `review_recommended`
- `review_required`
- teacher-resolved/reviewed state represented by stored resolution and override fields

Low confidence can recommend review without changing a completed submission into a blocking state. Unmapped writing or a grading blocking reason can produce submission-level `review_required`.

## Release State

Release is independent from processing status. A teacher can release eligible completed or review-required results. `released_at` controls student visibility; withdrawing release does not reprocess or delete the submission.

## Retry And Replacement

The retry route accepts failed or submission-level rescan-required records. Page replacement clears derived results and requeues processing only for statuses allowed by the backend.

Current implementation has a rescan inconsistency: an unreadable page records page-level `rescan_required` but the submission is stored as `review_required`. The retry route does not accept that submission state, and page replacement rejects review-required submissions. Operators should treat unreadable-paper recovery as a known issue until the status transitions are aligned.

## Job Execution

`ProcessingJob` stores status, attempts, error, and timestamps, but it does not act as a queue consumer. FastAPI schedules `process_submission` in its own process.

Operational consequences:

- an API restart can interrupt an active job
- stale jobs are not automatically recovered
- configured maximum attempts and stale-job timeout are not enforced
- multiple API replicas can schedule conflicting work without additional coordination
- deployment should remain single-replica for live processing unless job execution is redesigned

See [backups and recovery](../operations/backups-and-recovery.md) for interrupted-job handling.
