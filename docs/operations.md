# Operations

Use the detailed runbooks for current operational behavior:

- [Local development](guides/local-development.md)
- [Configuration](reference/configuration.md)
- [Deployment](operations/deployment.md)
- [Security and privacy](operations/security.md)
- [Backups and recovery](operations/backups-and-recovery.md)
- [Troubleshooting](operations/troubleshooting.md)
- [Testing](reference/testing.md)

## Runtime Facts

- Local API: `http://localhost:8000`; frontend: `http://localhost:3000`.
- Production backend container: port `8080`; frontend container: port `3000`.
- Production requires PostgreSQL, secure cookies, HTTPS CORS origins, a strong session secret, and `DEMO_MODE=false`.
- Migrations run before backend startup in the container and readiness requires revision `0016_production_hardening`.
- Uploads use local filesystem cache plus database page blobs. S3-related settings are not implemented.
- Processing runs in-process and should remain single-replica unless job coordination is redesigned.
- Live AI requires `OPENAI_API_KEY`; runtime routing currently uses configured Luna, GPT-4o, and GPT-4o-mini operations as documented in [AI pipeline](reference/ai-pipeline.md).

## Verification

```bash
cd backend
.venv/bin/python -m pytest
.venv/bin/python -m app.migrate
cd ../frontend
npm run lint
npm run build
```

The frontend production build passes. Biome lint currently reports existing source findings; this is tracked in [known gaps](known-gaps.md).
