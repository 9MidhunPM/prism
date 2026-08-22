# Architecture

The full architecture reference is maintained in [reference/architecture.md](reference/architecture.md). This page provides the short version for readers coming from the original documentation layout.

```text
Browser
  -> Next.js frontend :3000
     -> same-origin /api rewrite
        -> FastAPI backend :8000 local / :8080 container
           -> SQLite local or PostgreSQL production
           -> local media cache plus page blobs in the database
           -> OpenAI runtime operations
```

Important implementation boundaries:

- The backend owns authentication, authorization, persistence, scoring, AI orchestration, and analytics.
- The frontend is client-rendered and its route guard is not a security boundary.
- Processing uses FastAPI `BackgroundTasks` in the API process; there is no durable external worker.
- Page perception and grading are currently sequential; `AI_CONCURRENCY` is configured but unused.
- S3 settings are placeholders. No S3 client or signed-URL implementation exists.
- The original page remains ground evidence beside normalized media and transcription.
- Teacher marks take precedence over AI marks, and backend code calculates all totals.

Read [domain model](reference/domain-model.md), [AI pipeline](reference/ai-pipeline.md), and [processing states](reference/processing-states.md) for details.
