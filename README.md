# PRISM

PRISM is an evidence-first prototype for AI-assisted handwritten assessment review. Teachers retain final authority over every mark.

## Run locally

Start the API:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Start the frontend in a second terminal:

```bash
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

The first API start creates a SQLite database and seeds a machine-learning exam with five synthetic student submissions. Set `OPENAI_API_KEY` before uploading a live paper; live processing uses only `gpt-5.6-luna`.

## Verification

```bash
cd backend && .venv/bin/pytest
cd frontend && npm run build
```
