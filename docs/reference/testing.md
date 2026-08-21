# Testing

PRISM currently has backend automated tests plus frontend lint and production-build verification. There is no committed frontend unit or browser test suite.

## Backend Tests

Create the backend environment as described in [local development](../guides/local-development.md), then run from the repository root:

```bash
backend/.venv/bin/python -m pytest backend/tests
```

Tests use temporary SQLite databases and `Base.metadata.create_all()` unless a test explicitly exercises Alembic.

### Coverage Areas

| File | Main coverage |
| --- | --- |
| `test_settings.py` | Development/production configuration validation |
| `test_migrations.py` | Fresh SQLite migration to current Alembic head |
| `test_auth.py` | Bootstrap uniqueness, login/logout, role isolation, released results, demo seeding |
| `test_ai_schemas.py` | Perception uncertainty/regions, unmapped fragments, import mark warnings |
| `test_scoring.py` | Deterministic totals, upload validation, PDF normalization, media restore, deletion, review, cache, continuations |

### Important Gaps

The backend suite does not directly cover every production path. Notable gaps include:

- CSRF and origin middleware
- process-local rate limiting
- full processing with mocked OpenAI
- evidence persistence and mark clamping through a complete job
- review accept/reject and direct override history
- page replacement and release transitions
- Google Drive API failure/commit behavior
- assistant data scoping
- all analytics archive/status/membership filters

## Frontend Checks

Install locked dependencies:

```bash
cd frontend
npm ci
```

Run Biome:

```bash
npm run lint
```

Build the production application:

```bash
npm run build
```

The build validates TypeScript and Next.js compilation. It does not exercise login, CSRF mutation, upload, polling, review, release, or role-isolation workflows.

## Manual Browser Smoke Test

Use an isolated development or demo environment. Never modify production assessment records only to complete a smoke test.

1. Load `/login` and sign in as a teacher.
2. Verify workspace, classes, exams, papers, and assistant navigation.
3. Open an exam and confirm rubric and existing submissions render.
4. Open one submission and switch paper pages/questions.
5. Confirm original preview, criterion reasoning, transcription, and evidence render.
6. Open exam insights and verify metrics and tables render.
7. Sign out and verify protected routes return to login.
8. Sign in as a student and verify only released owned results appear.

Use Playwright or browser devtools to inspect failed network calls and console errors. Do not capture credentials, cookies, tokens, or confidential paper content in test artifacts.

## Health Verification

After deployment:

```bash
curl --fail https://prism.your-domain.invalid/api/health
curl --fail https://prism.your-domain.invalid/api/health/ready
```

Readiness must return success only after the database reaches the expected Alembic revision.

## Migration Verification

The backend container applies migrations before Uvicorn. For local verification:

```bash
cd backend
.venv/bin/python -m app.migrate
.venv/bin/alembic current
```

The expected revision in the current application is `0016_production_hardening`.

## Documentation Verification

Check for stale placeholders and broken relative links whenever docs change:

```bash
rg -n 'TODO|Lorem ipsum|\{\{' README.md docs frontend/README.md
```

Inspect image paths and render Markdown in a GitHub-compatible viewer. Product screenshots should contain no credentials or browser storage values.
