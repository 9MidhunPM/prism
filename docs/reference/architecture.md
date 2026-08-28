# Architecture

PRISM is a two-process web application: a Next.js frontend and a FastAPI backend. The backend owns authentication, authorization, persistence, file normalization, AI orchestration, scoring, review, and analytics.

## Runtime Topology

```text
Browser
  |
  | HTTPS, same-origin /api requests
  v
Next.js :3000
  |
  | rewrite /api/* to BACKEND_INTERNAL_URL
  v
FastAPI :8080 production / :8000 local
  |              |                  |
  v              v                  v
PostgreSQL   OpenAI API      local upload cache
production                    + page blobs in DB
```

The browser always calls relative `/api` routes. Next.js chooses its rewrite destination in this order:

1. `BACKEND_INTERNAL_URL`
2. `NEXT_PUBLIC_API_URL`
3. `http://localhost:8000`

This keeps session cookies same-origin at the browser while allowing private container networking between frontend and backend.

## Frontend

The frontend uses Next.js App Router 16, React 19, TypeScript, Tailwind CSS 4, and React Compiler.

Key boundaries:

- `frontend/app/`: client-rendered route pages and global styles
- `frontend/components/session-provider.tsx`: session lookup and role-based navigation guard
- `frontend/components/app-shell.tsx`: teacher navigation and processing-job polling
- `frontend/components/drive-import-panel.tsx`: Google Identity Services, Picker, preview, and commit UI
- `frontend/lib/api.ts`: same-origin fetch wrapper, cookie credentials, CSRF header, and normalized errors
- `frontend/next.config.ts`: API rewrite and browser security headers

All current application pages are client components. The frontend guard improves navigation but is not the security boundary; backend role checks authorize every protected operation.

## Backend

The backend is one FastAPI application with routes declared in `backend/app/main.py`.

Key modules:

- `main.py`: middleware, API routes, file handling, orchestration, scoring, analytics, and deletion
- `models.py`: SQLAlchemy tables and processing enums
- `ai.py`: versioned prompts, Pydantic structured outputs, and OpenAI calls
- `settings.py`: root `.env` configuration and production validation
- `database.py`: SQLAlchemy engine and sessions
- `auth.py`: password hashing plus legacy signed-session helpers
- `migrate.py`: Alembic upgrade with a PostgreSQL advisory lock
- `demo.py` and `seed_demo.py`: optional demo account setup

The API uses SQLAlchemy directly and manually orders deep deletes. Models do not define ORM relationships or database cascades.

## Request Security

```text
login/bootstrap
  -> account verification
  -> random opaque session token + CSRF token
  -> hashes persisted in auth_sessions
  -> HttpOnly session cookie + readable CSRF cookie

unsafe authenticated request
  -> origin/fetch-site check
  -> session validation
  -> X-CSRF-Token equality check
  -> role and ownership authorization
```

Teacher and student accounts use the same login route. Student sessions with a temporary password are restricted to identity lookup, password change, and logout.

## Submission Pipeline

```text
upload
  -> validate MIME, magic bytes, count, and size
  -> preserve original bytes
  -> render normalized JPEG previews
  -> persist submission, pages, hashes, and processing job
  -> FastAPI background task
      -> clear derived results
      -> transcribe each page
      -> map question fragments and page continuations
      -> grade each mapped criterion
      -> clamp marks and calculate totals
      -> flag required/recommended review
      -> persist completed or review-required state
```

Page requests and criterion grading run sequentially despite the configured `AI_CONCURRENCY` value. Processing executes inside the API process with `BackgroundTasks`; there is no external queue or worker. A restart can interrupt active work, and horizontal scaling requires additional job coordination not present today.

## Storage

Each `SubmissionPage` stores:

- original source key and content type
- normalized preview key
- original source bytes
- processed preview bytes
- source and image hashes
- page quality and rescan metadata

The filesystem under `UPLOAD_ROOT` is a cache and working location. Missing local files can be restored from database blobs. For a PDF, the original PDF bytes are currently repeated on each rendered page record.

S3-related settings exist but no S3 client or signed-URL implementation exists. Do not deploy on ephemeral filesystem storage without accounting for current media behavior and database size.

## Data And Scoring

The database stores typed records for identities, classes, students, exams, rubrics, submissions, pages, answers, evidence, evaluations, teacher overrides, review suggestions, AI artifacts, jobs, and Drive batches.

The backend, never the model, calculates:

- criterion bounds
- question and exam maxima
- submission totals
- percentages and averages
- concept mastery
- question and criterion performance
- review rates

The effective mark is `teacher_marks` when present, otherwise `ai_marks`.

## AI Boundaries

AI operations are separate and versioned:

| Operation | Default model | Prompt version |
| --- | --- | --- |
| Page perception and mapping | `gpt-5.6-luna` | `perception_v2` |
| Criterion grading | `gpt-5.6-luna` | `grading_v3` |
| Teacher-requested re-evaluation | `gpt-4o` | `review_v3` |
| Exam paper import | `gpt-4o` | `exam_import_v1` |
| Answer-key import | `gpt-4o` | `answer_key_import_v1` |
| Teacher assistant prose | `gpt-4o-mini` | `teacher_chat_v1` |

Each operation returns a Pydantic structured output. See [AI pipeline](ai-pipeline.md) for schema and cache behavior.

## Deployment Components

The repository contains separate backend and frontend Dockerfiles but no Compose, Kubernetes, reverse-proxy, CI, or platform manifest. Production requires externally managed:

- TLS and public routing
- container networking
- PostgreSQL
- persistent storage policy
- secrets
- backups and restore testing
- health checks and rollout strategy

See [deployment](../operations/deployment.md) for the supported container contract.

## Known Architectural Constraints

- Processing jobs are not durable across API restarts.
- Rate limits are process-local and reset at restart.
- Cache lookup does not include the configured model name.
- Only perception and exam import have artifact cache lookup.
- Some configured job, logging, AI concurrency, and S3 controls are not wired into runtime behavior.
- Analytics endpoints do not all apply identical archive, status, and secondary-membership filters.
- Reprocessing deletes existing derived evaluations, reviews, overrides, evidence, and AI artifacts for the submission.

These constraints should remain visible in design and operations decisions until the implementation changes.
