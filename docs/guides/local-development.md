# Local Development

This guide starts the current repository with SQLite and a Next.js development server. Use Python 3.13 and Node.js 22 to match the container images.

## Prerequisites

- Python 3.13 with `venv`
- Node.js 22 and npm
- Git
- An OpenAI API key for live AI processing
- PostgreSQL only when testing production-like configuration; SQLite is the default local database

## Setup

From the repository root:

```bash
cp .env.example .env
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend
npm ci
cd ..
```

The settings loader reads `.env` from the repository root. Do not place production secrets in this file or commit it.

## Local Environment

The smallest useful local configuration is:

```dotenv
APP_ENV=development
APP_URL=http://localhost:3000
API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
SESSION_SECRET=local-development-secret-change-this
SESSION_COOKIE_SECURE=false
DATABASE_URL=sqlite:///./data/prism.db
DEMO_MODE=false
OPENAI_API_KEY=
```

`OPENAI_API_KEY` may remain empty for authentication and UI work. Live transcription, grading, review, imports, and assistant prose require a key.

## Migrate And Run

Run migrations before starting the API:

```bash
cd backend
.venv/bin/python -m app.migrate
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The frontend calls relative `/api` paths. Next.js rewrites them to `BACKEND_INTERNAL_URL`, then `NEXT_PUBLIC_API_URL`, then `http://localhost:8000`.

## Create A Local Teacher

The bootstrap route is available for the first teacher outside production. Use a local-only request:

```bash
curl -i -X POST http://localhost:8000/api/auth/bootstrap \
  -H 'Content-Type: application/json' \
  --data '{"name":"Local Teacher","email":"teacher@localhost.invalid","password":"local-teacher-password-123"}'
```

Then sign in at `http://localhost:3000/login`. The route permits only one initial teacher in a database. New teacher account creation is disabled in production.

## Seed Demo Accounts

To seed configured demo teacher and student accounts:

```bash
cd backend
DEMO_MODE=true \
DEMO_TEACHER_NAME='Demo Teacher' \
DEMO_TEACHER_EMAIL='teacher@localhost.invalid' \
DEMO_TEACHER_PASSWORD='demo-teacher-password-123' \
DEMO_STUDENT_NAME='Demo Student' \
DEMO_STUDENT_EMAIL='student@localhost.invalid' \
DEMO_STUDENT_PASSWORD='demo-student-password-123' \
.venv/bin/python -m app.seed_demo
```

Seeding is idempotent for those account values. It does not create the synthetic exam and five submissions described by an old README; that behavior is not present in the current startup path.

## Verify

Run backend tests:

```bash
backend/.venv/bin/python -m pytest backend/tests
```

Run frontend checks:

```bash
npm --prefix frontend run lint
npm --prefix frontend run build
```

Check API health:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/ready
```

Readiness checks database connectivity and, outside tests, requires migration revision `0016_production_hardening`.

## Useful Local Paths

| Path | Purpose |
| --- | --- |
| `data/prism.db` | Ignored SQLite database when using the default URL |
| `data/uploads/` | Ignored original and processed upload cache |
| `backend/alembic/versions/` | Versioned schema migrations |
| `backend/tests/` | Backend tests |
| `frontend/app/` | Next.js routes and global styles |

The database and upload directories contain educational data. Delete them only when intentionally resetting a local environment.
