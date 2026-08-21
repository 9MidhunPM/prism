# Deployment

The repository builds separate frontend and backend containers. It does not include Compose, Kubernetes, reverse-proxy, or platform-specific deployment manifests.

## Required Services

```text
Public HTTPS
  -> Next.js container :3000
      -> private /api rewrite
          -> FastAPI container :8080
              -> PostgreSQL
              -> OpenAI API
              -> persistent upload cache
```

Production configuration rejects SQLite, insecure cookies, localhost/non-HTTPS CORS origins, weak session secrets, and demo mode.

## Build Images

Backend:

```bash
docker build -t prism-backend:current backend
```

Frontend, with a backend address reachable from the frontend container:

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_URL=http://prism-backend:8080/api \
  -t prism-frontend:current \
  frontend
```

For Google Drive, also provide the documented `NEXT_PUBLIC_GOOGLE_DRIVE_*` build arguments. Public frontend variables are baked into the bundle.

Prefer setting `BACKEND_INTERNAL_URL=http://prism-backend:8080` for the frontend runtime/platform when supported. Confirm the resulting Next.js rewrite in the built deployment because `next.config.ts` is evaluated during the build.

## Backend Contract

The backend image:

- uses Python 3.13
- runs as UID `10001`
- exposes port `8080`
- sets `UPLOAD_ROOT=/app/data/uploads`
- declares `/app/data/uploads` as a volume
- executes `python -m app.migrate` before Uvicorn
- starts `uvicorn app.main:app --host 0.0.0.0 --port 8080`

PostgreSQL migration execution takes a singleton advisory lock so concurrently starting containers do not apply migrations simultaneously.

## Frontend Contract

The frontend image:

- uses Node.js 22 Alpine
- installs with `npm ci`
- builds Next.js standalone output
- runs as the unprivileged `node` user
- exposes port `3000`
- starts `node server.js`

Route security still belongs to the backend; frontend session guards are navigation behavior only.

## Production Environment

Set at minimum:

```dotenv
APP_ENV=production
APP_URL=https://prism.your-domain.invalid
API_URL=https://prism.your-domain.invalid/api
CORS_ORIGINS=https://prism.your-domain.invalid
SESSION_SECRET=generate-a-random-secret-of-at-least-32-characters
SESSION_COOKIE_SECURE=true
DATABASE_URL=postgresql+psycopg://prism_user:replace-me@postgres:5432/prism
UPLOAD_ROOT=/app/data/uploads
DEMO_MODE=false
OPENAI_API_KEY=replace-with-secret-manager-value
BACKEND_INTERNAL_URL=http://prism-backend:8080
```

See [configuration](../reference/configuration.md) for the full matrix. Inject secrets through the deployment platform; do not bake them into images.

## Database

Use externally persistent PostgreSQL. The readiness route requires the exact application migration revision. The current head is `0016_production_hardening`.

The startup migration is forward-only in normal operation. Before deploying a migration:

1. Back up PostgreSQL.
2. Confirm the new backend image contains the complete Alembic chain.
3. Deploy one backend instance and wait for readiness.
4. Verify application behavior before replacing additional instances.

Do not assume every Alembic downgrade is safe for production data. Restore from a verified backup when a destructive migration must be reversed.

## Media Persistence

Mount persistent storage at `/app/data/uploads`. Page bytes are also stored in PostgreSQL and can restore missing local files, but that duplicates media and can make the database large. S3 configuration is currently not implemented.

Back up both PostgreSQL and the upload volume. See [backups and recovery](backups-and-recovery.md).

## Health Checks

Configure liveness:

```text
GET /api/health
```

Configure readiness:

```text
GET /api/health/ready
```

Readiness verifies database connectivity and migration head. The Dockerfiles do not define an image-level `HEALTHCHECK`; configure these paths in the platform.

## Scaling

Run one live-processing backend replica unless job orchestration is redesigned. Processing uses FastAPI in-process background tasks, rate limits are process-local, and job scheduling is not atomic across replicas.

The frontend can scale independently when all instances share the same backend and build-time configuration. Session state lives in PostgreSQL, not frontend memory.

## Rollout

1. Run backend tests and frontend lint/build.
2. Back up PostgreSQL and media.
3. Build immutable backend and frontend image tags.
4. Deploy PostgreSQL-compatible backend configuration.
5. Wait for `/api/health/ready` success.
6. Deploy the frontend with the correct internal backend target.
7. Smoke-test teacher login, dashboard, exam detail, evidence review, and student release visibility.
8. Inspect failed/active processing jobs and application logs.

Avoid restarting the API while papers are processing. If unavoidable, record active submission IDs and follow the recovery procedure.

## Reverse Proxy And Headers

Terminate TLS before requests reach the frontend. Preserve `Host`, scheme, and client-address headers according to the platform's trusted-proxy model. The frontend emits CSP, clickjacking, referrer, content-type, and permissions headers.

Cloudflare Browser Insights currently injects a script that the application CSP does not allow, producing a blocked-script console error. Either disable that injection or deliberately update and test CSP; do not weaken CSP broadly to hide the error.

## Account Provisioning

Public teacher creation is disabled in production. Provision the initial teacher through an approved database/administrative process before launch. The current HTTP bootstrap token setting is not enforced by route code and must not be treated as a secure production provisioning path.

Student accounts are created or reset by authenticated teachers from a class roster.
