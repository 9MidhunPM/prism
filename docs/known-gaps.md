# Known Gaps

This page records implementation gaps that documentation must not hide. These are not claims that the product is unusable; they identify where operational or product expectations exceed the current source.

## Processing Is Not Durable

Submission processing runs in FastAPI `BackgroundTasks`. `ProcessingJob` stores state, but there is no external queue, worker, stale-job recovery loop, or enforced attempt limit. API restarts can interrupt live processing, and multiple backend replicas can schedule conflicting work.

## Configured Controls Not Fully Wired

The following settings exist but are not fully active in runtime behavior:

- `AI_CONCURRENCY` is unused; perception and grading are sequential.
- `JOB_POLL_INTERVAL_SECONDS`, `JOB_MAX_ATTEMPTS`, and `JOB_STALE_AFTER_SECONDS` do not create durable worker behavior.
- `LOG_LEVEL` is not connected to a structured logging setup.
- S3 settings have no storage adapter behind them.
- Cache identity does not include model name.

## Review And Frontend Mutation Risk

Some evidence-review mutation handlers use raw `fetch` and do not consistently surface non-2xx failures. The backend requires CSRF for unsafe authenticated requests. Inspect the network response and reload persisted state after review actions.

## Rescan State Inconsistency

Unreadable-page processing can record page-level `rescan_required` while storing submission-level `review_required`. Retry and replacement routes do not accept every resulting combination. Treat unreadable-paper recovery as an operational issue until the transitions are aligned.

## Analytics Scope Differences

Teacher profile, student profile, dashboard, class analytics, and exam analytics do not all use identical status, archive, primary-class, and secondary-membership filters. Interpret aggregates using the endpoint-specific implementation and source-paper population.

## Evaluation Row Omissions

Questions without mapped answer fragments currently do not create criterion evaluation rows. Their score contribution is effectively zero, but evaluation-based analytics may undercount omissions.

## Reprocessing History

Reprocessing clears derived evaluations, evidence, review suggestions, overrides, and AI artifacts for the submission. Existing teacher decisions are not preserved as an immutable reprocessing history.

## Frontend Test Coverage

The frontend has no committed unit, integration, accessibility, or end-to-end test suite. `npm run build` passes; Biome lint reports existing source findings.

## Account Provisioning

Teacher creation is disabled in production. `BOOTSTRAP_TOKEN` and `ENABLE_HTTP_BOOTSTRAP` are validated as settings, but the current bootstrap route does not compare the supplied token. Use an approved administrative provisioning process.

## Documentation Freshness

When source changes, recheck routes, model routing, prompt versions, processing states, deletion/media retention, analytics scopes, screenshots, and deployment assumptions. Record the observed commit and date for hosted behavior.
