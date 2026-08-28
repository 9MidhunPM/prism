# Configuration

Backend settings load from environment variables and the repository-root `.env`. Frontend `NEXT_PUBLIC_*` values are embedded during the Next.js build.

## Application And Security

| Variable | Default | Purpose | Status |
| --- | --- | --- | --- |
| `APP_ENV` | `development` | Environment policy switch | Implemented |
| `APP_NAME` | `PRISM` | Display/service name | Implemented |
| `APP_URL` | `http://localhost:3000` | Public frontend URL | Implemented |
| `API_URL` | `http://localhost:8000` | Public API metadata URL | Implemented |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed browser origins | Implemented |
| `LOG_LEVEL` | `INFO` | Intended log level | Configured, not wired into logging setup |
| `SESSION_SECRET` | insecure development value | Production secret validation | Required strong value in production; active sessions are opaque tokens |
| `SESSION_COOKIE_SECURE` | `false` | Mark cookies HTTPS-only | Must be `true` in production |
| `SESSION_TTL_SECONDS` | `604800` | Session lifetime | Implemented; add to local overrides when needed |
| `ENABLE_HTTP_BOOTSTRAP` | `false` | Intended bootstrap control | Not consulted by current route |
| `BOOTSTRAP_TOKEN` | empty | Intended bootstrap token | Validated in settings when enabled, but not compared by route |

Production requires a session secret of at least 32 characters, secure cookies, HTTPS non-local CORS origins, PostgreSQL, and disabled demo mode.

## Demo Accounts

| Variable | Default | Purpose |
| --- | --- | --- |
| `DEMO_MODE` | `false` | Permit demo account seeding |
| `DEMO_TEACHER_NAME` | `Demo Teacher` | Seeded teacher name |
| `DEMO_TEACHER_EMAIL` | empty | Seeded teacher email |
| `DEMO_TEACHER_PASSWORD` | empty | Seeded teacher password |
| `DEMO_STUDENT_NAME` | `Demo Student` | Seeded student name |
| `DEMO_STUDENT_EMAIL` | empty | Seeded student email |
| `DEMO_STUDENT_PASSWORD` | empty | Seeded student password |

Never commit actual demo or production credentials. `DEMO_MODE` must be false in production.

## Database And Media

| Variable | Default | Purpose | Status |
| --- | --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/prism.db` | SQLAlchemy database URL | SQLite local, PostgreSQL required in production |
| `UPLOAD_ROOT` | `data/uploads` | Original/processed filesystem cache | Implemented |
| `MAX_UPLOAD_MB` | `20` | Total upload byte limit | Implemented |
| `MAX_SUBMISSION_PAGES` | `10` | Maximum normalized pages | Implemented |
| `MAX_IMAGE_DIMENSION` | `2400` | Conservative preview dimension | Implemented |
| `PROCESSED_IMAGE_QUALITY` | `88` | Preview JPEG quality | Implemented |

## OpenAI

| Variable | Default | Purpose | Status |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | empty | Server-side OpenAI credential | Required for live AI |
| `OPENAI_MODEL` | `gpt-5.6-luna` | Health/display compatibility value | Implemented |
| `LUNA_MODEL` | `gpt-5.6-luna` | Perception and grading | Implemented |
| `GPT4O_MODEL` | `gpt-4o` | Review and document import | Implemented |
| `GPT4O_MINI_MODEL` | `gpt-4o-mini` | Teacher assistant prose | Implemented |
| `OPENAI_TIMEOUT_SECONDS` | `90` | SDK request timeout | Implemented |
| `OPENAI_MAX_RETRIES` | `2` | SDK bounded retry count | Implemented |
| `AI_CONCURRENCY` | `3` | Intended concurrent requests | Configured but unused; current calls are sequential |
| `AI_REVIEW_THRESHOLD` | `0.75` | Review recommendation threshold | Implemented |

Application runtime models must remain within repository policy: `gpt-5.6-luna`, `gpt-4o`, and `gpt-4o-mini`.

## Processing And Rate Limits

| Variable | Default | Purpose | Status |
| --- | --- | --- | --- |
| `JOB_POLL_INTERVAL_SECONDS` | `2` | Intended worker polling interval | Configured but no worker loop exists |
| `JOB_MAX_ATTEMPTS` | `3` | Intended retry cap | Configured but not enforced |
| `JOB_STALE_AFTER_SECONDS` | `600` | Intended stale-job threshold | Configured but not enforced |
| `RATE_LIMIT_PER_MINUTE` | `120` | General per-client/path limit | Implemented in process memory |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | Login-category limit | Implemented in process memory |

Rate limits are not shared across replicas and reset at process restart.

## S3-Compatible Storage

| Variable | Default |
| --- | --- |
| `S3_ENDPOINT_URL` | empty |
| `S3_REGION` | `auto` |
| `S3_BUCKET` | `prism-private` |
| `S3_ACCESS_KEY_ID` | empty |
| `S3_SECRET_ACCESS_KEY` | empty |
| `S3_FORCE_PATH_STYLE` | `true` |
| `S3_SIGNED_URL_TTL_SECONDS` | `300` |

These values are placeholders. No S3 dependency, upload, restore, or signed-URL code is implemented. Current storage is filesystem cache plus database blobs.

## Google Drive

| Variable | Scope | Purpose |
| --- | --- | --- |
| `GOOGLE_DRIVE_CLIENT_ID` | Backend | Enables Drive routes and validates intended client configuration |
| `NEXT_PUBLIC_GOOGLE_DRIVE_CLIENT_ID` | Frontend build | OAuth web client ID |
| `NEXT_PUBLIC_GOOGLE_DRIVE_API_KEY` | Frontend build | Restricted browser API key |
| `NEXT_PUBLIC_GOOGLE_DRIVE_APP_ID` | Frontend build | Google Cloud project number |
| `NEXT_PUBLIC_GOOGLE_DRIVE_SCOPE` | Frontend build | Defaults to Drive read-only |

See [Google Drive import](../guides/google-drive-import.md) for setup.

## Frontend Routing

| Variable | Priority | Purpose |
| --- | --- | --- |
| `BACKEND_INTERNAL_URL` | First | Private backend origin used by Next rewrite |
| `NEXT_PUBLIC_API_URL` | Second | Fallback backend origin; Docker build argument |

A trailing `/api` is removed before Next creates the `/api/:path*` rewrite. Prefer `BACKEND_INTERNAL_URL=http://backend:8080` in a container network.

## Example Environments

Local SQLite:

```dotenv
APP_ENV=development
APP_URL=http://localhost:3000
API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
SESSION_SECRET=local-development-secret-change-this
SESSION_COOKIE_SECURE=false
DATABASE_URL=sqlite:///./data/prism.db
```

Production shape:

```dotenv
APP_ENV=production
APP_URL=https://prism.your-domain.invalid
API_URL=https://prism.your-domain.invalid/api
CORS_ORIGINS=https://prism.your-domain.invalid
SESSION_SECRET=generate-a-random-secret-of-at-least-32-characters
SESSION_COOKIE_SECURE=true
DATABASE_URL=postgresql+psycopg://prism_user:replace-me@postgres:5432/prism
DEMO_MODE=false
BACKEND_INTERNAL_URL=http://backend:8080
```

Replace all illustrative secrets before use and keep the resulting environment outside version control.
