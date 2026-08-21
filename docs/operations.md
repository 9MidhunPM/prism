# Operations and configuration

## 1. Local prerequisites

- Python 3.11+ with a working virtual-environment module;
- Node.js and npm compatible with the checked-in lockfile;
- SQLite for the simplest demo, or PostgreSQL for production-like deployment;
- an OpenAI API key only when running live inference;
- optional Google Drive and S3-compatible credentials for those integrations.

## 2. Environment configuration

Copy `.env.example` to a local `.env` and set only the values needed for the
environment. Keep `.env` ignored and out of logs.

### Application

| Variable | Meaning |
| --- | --- |
| `APP_ENV` | `development`, `test`, or `production` |
| `APP_URL` / `API_URL` | public and API origins |
| `CORS_ORIGINS` | comma-separated allowed browser origins |
| `SESSION_SECRET` | strong secret for signed sessions |
| `SESSION_COOKIE_SECURE` | `true` when served over HTTPS |
| `DATABASE_URL` | SQLite or PostgreSQL SQLAlchemy URL |

Production startup validates a strong session secret, HTTPS origins, secure
cookies, PostgreSQL, and disabled demo mode.

### AI

| Variable | Meaning |
| --- | --- |
| `OPENAI_API_KEY` | server-only API secret |
| `OPENAI_MODEL` | intended runtime model, required to be `gpt-5.6-luna` |
| `OPENAI_TIMEOUT_SECONDS` | per-call timeout |
| `OPENAI_MAX_RETRIES` | bounded retry count |
| `AI_CONCURRENCY` | concurrent page requests, maximum four |
| `AI_REVIEW_THRESHOLD` | review signal, default `0.75` |

Never expose `OPENAI_API_KEY` to `NEXT_PUBLIC_*` variables or frontend code.

Before enabling live inference, confirm that every operation resolves to Luna.
The latest fetched source still contains legacy GPT-4o/GPT-4o-mini configuration
fields and dispatch branches; this is documented in [Known gaps](known-gaps.md)
and must be removed or disabled before production claims Luna-only compliance.

### Upload and jobs

`MAX_UPLOAD_MB`, `MAX_SUBMISSION_PAGES`, `MAX_IMAGE_DIMENSION`, and
`PROCESSED_IMAGE_QUALITY` define conservative upload limits. Job polling,
attempts, stale timeout, and API/login rate limits are also configurable.

### Demo accounts

`DEMO_MODE` is for local seeded data only. Supply demo teacher and student
values through local environment configuration. Do not put personal or shared
production credentials into `.env.example`, test fixtures, screenshots, or
commits.

## 3. Start, migrate, and verify

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.migrate
.venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

Run the gates:

```bash
cd backend && .venv/bin/pytest
cd frontend && npm run lint
cd frontend && npm run build
```

Use `/api/health` for liveness and `/api/health/ready` for database/schema
readiness. A healthy process is not proof that AI is enabled; inspect the
reported configuration and the server logs without printing secrets.

## 4. Storage and backups

Development defaults to SQLite and a local upload root. Production should use
PostgreSQL and private S3-compatible media with short signed URLs. Back up the
database and original media together: database rows without the source page
cannot support defensible evidence.

Before deleting an exam or submission, confirm the scope. The current app
cascades dependent papers, evaluations, evidence, reviews, and unreferenced
media according to the model relationships. Restore from a database/media
backup rather than attempting to reconstruct deleted evidence.

## 5. Failure handling

| Symptom | Check |
| --- | --- |
| API cannot start | database URL, migrations, upload directory permissions |
| Frontend redirects to login | API URL, CORS, cookie, and `/api/auth/me` |
| Upload rejected | MIME, file signature, file size, page count |
| Paper remains processing | job status, retry count, stale timeout, API logs |
| AI unavailable | API key, model setting, timeout, rate limit, cached demo paper |
| Evidence missing | original/processed media availability and page ownership |
| Student sees no result | teacher has not released the submission |
| Assistant answer is vague | select relevant mentions and inspect retrieved statistics |

AI errors should be visible as a failed or review-required job. Never mark a
paper complete because a network call timed out.

## 6. Logging and privacy

Useful structured log fields are submission ID, operation, model, duration,
success/failure, token usage, and estimated cost where available. Do not log:

- API keys;
- session secrets or raw cookies;
- passwords;
- full student papers when an ID or page reference is sufficient;
- unsupported psychological or disciplinary inferences.

## 7. Production checklist

- [ ] Set a random `SESSION_SECRET` of at least 32 characters.
- [ ] Set `SESSION_COOKIE_SECURE=true` behind HTTPS.
- [ ] Use PostgreSQL and run migrations before serving traffic.
- [ ] Use private media storage and short signed URLs.
- [ ] Set exact HTTPS CORS origins.
- [ ] Disable demo mode and HTTP bootstrap after provisioning.
- [ ] Set bounded AI timeout, retry, concurrency, and review threshold.
- [ ] Confirm `.env` and data directories are excluded from version control.
- [ ] Test upload, review, override, release, backup, and restore flows.
- [ ] Keep a cached completed demo paper separate from production student data.
