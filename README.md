# PRISM

PRISM is an evidence-first workspace for AI-assisted review of handwritten
examinations. It helps a teacher move from a paper scan to a defensible,
criterion-level assessment without handing final authority to an AI system.

```text
paper or scan
    -> conservative normalization
    -> Luna perception and question mapping
    -> rubric criterion suggestions
    -> deterministic score validation
    -> evidence and confidence review
    -> teacher override or accepted review
    -> student and class learning signals
```

The current implementation is a small Next.js frontend backed by a FastAPI
service, SQLite for local development, Alembic migrations, and local durable
media with an optional S3-compatible storage adapter. The product contract
requires `gpt-5.6-luna` for every runtime AI operation; the latest source still
contains legacy model selectors for some operations, which is recorded as a
release-blocking documentation gap in [Known gaps](docs/known-gaps.md).

## Documentation

The full documentation set is in [`docs/`](docs/README.md):

- [Product requirements](PRD.md)
- [MVP specification](MVP.md)
- [Architecture and data flow](docs/architecture.md)
- [Teacher and student workflows](docs/workflows.md)
- [API reference](docs/api.md)
- [Operations and configuration](docs/operations.md)
- [Demo runbook](docs/demo-runbook.md)
- [Screenshot guide](docs/screenshots.md)
- [Known gaps and release notes](docs/known-gaps.md)

## Quick start

### 1. Start the API

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.migrate
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

Open `http://localhost:3000/login`. Configure a teacher through the protected
bootstrap flow or use a deliberately configured local demo account. Do not
place real credentials in `.env.example`, shell history, screenshots, or
documentation.

### 3. Verify the checkout

```bash
cd backend && .venv/bin/pytest
cd frontend && npm run build
```

The health endpoints are:

```text
GET http://localhost:8000/api/health
GET http://localhost:8000/api/health/ready
```

## Scope and safety

PRISM is a hackathon MVP. It deliberately keeps the architecture small and
keeps the teacher in the loop. It does not infer intelligence, personality,
motivation, honesty, cheating, or mental health. It must preserve visible
student mistakes and use `[ILLEGIBLE]` or structured uncertainty when the paper
does not support a confident reading.

## Latest source baseline

The documentation refresh is based on the latest fetched `main` commit at the
start of this work:

```text
e2806612fbb05d7d2d50057070d32a9e5bfeae93
Cascade exam deletion through imported papers
```
