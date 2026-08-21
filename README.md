# PRISM

PRISM turns scanned handwritten exam papers into evidence-linked, teacher-controlled assessments and learning analytics.

![PRISM evidence review workbench](docs/assets/screenshots/review-workbench.png)

## Features

- **Evidence-first grading:** keeps each original page beside its transcription, criterion decision, confidence signal, and quoted evidence.
- **Teacher authority:** lets teachers override marks or request an AI re-evaluation, then accept or reject the suggestion.
- **Complete assessment flow:** supports class rosters, rubric-based exams, PDF/image uploads, Google Drive imports, processing, review, and release.
- **Learning analytics:** calculates student, class, exam, question, criterion, and concept performance deterministically.
- **Role-separated access:** gives teachers an assessment workspace and students a portal containing only released results.

## Documentation

| Start here | Purpose |
| --- | --- |
| [Documentation index](docs/README.md) | Navigate every guide and reference |
| [Local development](docs/guides/local-development.md) | Run the API and web app locally |
| [Teacher guide](docs/guides/teacher-guide.md) | Complete the assessment workflow |
| [Architecture](docs/reference/architecture.md) | Understand components, data, and request flow |
| [API reference](docs/reference/api.md) | Find the implemented HTTP endpoints |
| [Deployment](docs/operations/deployment.md) | Configure and operate production |

Planning documents remain available in [PRD.md](PRD.md) and [MVP.md](MVP.md). They describe product intent and may include capabilities that are not implemented. The `docs/` directory describes the current codebase.

## Getting Started

PRISM uses Python 3.13, Node.js 22, SQLite for local development, and PostgreSQL in production.

```bash
git clone git@github.com:9MidhunPM/prism.git
cd prism
cp .env.example .env
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python -m app.migrate
```

Run the API from `backend/`:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Run the web app in a second terminal from `frontend/`:

```bash
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Create the first local teacher through `POST /api/auth/bootstrap`, or configure demo accounts as described in the [local development guide](docs/guides/local-development.md). Set `OPENAI_API_KEY` before processing live papers.

## Common Commands

```bash
backend/.venv/bin/python -m pytest backend/tests
npm --prefix frontend run lint
npm --prefix frontend run build
```

## Tech Stack

- [Next.js](https://nextjs.org/) 16 and React 19 for the teacher and student interfaces
- [FastAPI](https://fastapi.tiangolo.com/) and SQLAlchemy for the API and domain logic
- SQLite locally and PostgreSQL in production
- OpenAI structured outputs for perception, grading, review, import, and grounded teacher assistance
- Alembic for schema migrations

## Project Layout

```text
prism/
|-- frontend/        Next.js application
|-- backend/         FastAPI application, migrations, and tests
|-- docs/            Current product and engineering documentation
|-- data/            Ignored local database and uploaded media
|-- PRD.md           Product requirements and long-term intent
|-- MVP.md           MVP planning record
`-- AGENTS.md        Repository engineering constraints
```

## Security

Never commit `.env`, API keys, access tokens, passwords, or student paper data. Browser authentication uses opaque server-side sessions and CSRF protection. Review [security and privacy](docs/operations/security.md) before exposing an environment publicly.

## License

No software license has been granted yet. Treat the repository as all rights reserved until the owner adds a license file.
