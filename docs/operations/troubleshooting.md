# Troubleshooting

Start with the API health endpoints and browser network panel. Avoid placing credentials, cookies, OAuth tokens, database URLs, or paper content in shared logs.

## API Does Not Start

### Migration Failure

Run from `backend/`:

```bash
.venv/bin/python -m app.migrate
.venv/bin/alembic current
```

Check database reachability, credentials, and migration logs. Production readiness expects `0016_production_hardening` in the current revision.

### Production Configuration Rejected

Confirm:

- PostgreSQL URL, not SQLite
- session secret has at least 32 characters
- secure cookies are enabled
- demo mode is disabled
- all CORS origins are HTTPS and not localhost

## Frontend Cannot Reach API

The browser should request same-origin `/api/...`, not a private backend hostname. Confirm the Next rewrite target:

```text
BACKEND_INTERNAL_URL
  -> NEXT_PUBLIC_API_URL
  -> http://localhost:8000
```

In containers, `localhost` points to the frontend container. Use the backend service name and port `8080`.

Rebuild the frontend after changing public build-time variables.

## Login Fails

- `401`: verify email/password, account enabled state, and temporary-password flow.
- `429`: wait for the process-local login window or check edge limits.
- Cookie not retained: verify same-origin proxying, HTTPS, and `Secure` policy.
- Redirect loop: inspect `/api/auth/me` and browser cookies.

There is no public password-reset email flow. Teachers reset student access; production teacher provisioning is administrative.

## Unsafe Request Returns 403

Confirm the request includes:

- session cookie
- `prism_csrf` cookie
- matching `X-CSRF-Token` header
- permitted `Origin`

Use `frontend/lib/api.ts` for browser mutations. Raw `fetch` calls must implement the same CSRF behavior. The current frontend review accept/reject request uses raw fetch and may fail CSRF validation; inspect the network response before assuming the proposal changed marks.

## Readiness Returns 503

`/api/health/ready` checks database connectivity and exact migration head.

1. Check PostgreSQL availability.
2. Run migrations.
3. Compare `alembic current` with application expected revision.
4. Verify the deployment did not start mixed backend versions against one database.

## Upload Rejected

- Use JPEG, PNG, or PDF.
- Upload one PDF or ordered image pages.
- Stay under `MAX_UPLOAD_MB` and `MAX_SUBMISSION_PAGES`.
- Ensure the file signature matches its declared content type.
- Check disk space and upload-volume permissions.

## Processing Stuck

Processing is an in-process background task. Check whether the API restarted and inspect `/api/processing-jobs` plus the submission status endpoint.

Do not deploy/restart during active assessment when avoidable. Stale jobs are not automatically recovered, and configured job attempt/staleness values are not enforced.

## Processing Failed

Inspect the persisted error without exposing paper content. Common causes include:

- missing/invalid `OPENAI_API_KEY`
- OpenAI timeout or rate limit
- malformed structured output
- invalid/corrupt image
- lost database connection
- API process restart

Retry only when the submission status supports the retry route.

## Unreadable Page Cannot Be Replaced

Current state handling has a known mismatch: unreadable perception stores page-level rescan state but submission-level `review_required`, while retry/replacement expects another status. Preserve the original and use a reviewed administrative workaround until code aligns the transitions.

## Original Page Is Missing

Media routes can restore local files from database blobs. Verify:

- persistent volume is mounted at `UPLOAD_ROOT`
- backend UID `10001` can write it
- blob columns contain data
- disk has free space

Then follow [backups and recovery](backups-and-recovery.md).

## Google Drive Picker Fails

- Confirm Drive API and Picker API are enabled.
- Confirm exact frontend origin is registered.
- Confirm all `NEXT_PUBLIC_GOOGLE_DRIVE_*` values were supplied at build time.
- Restrict but do not disable the browser API key for required APIs/origins.
- Use numeric page filenames.
- Reauthorize after token expiry.

See [Google Drive import](../guides/google-drive-import.md).

## Google Drive Preview Is Empty

Only JPEG/PNG files with numeric basenames are pages. Confirm files resemble `1.jpg`, `2.png`, and `10.jpg`, are within recursion depth, and are located under the selected student folder.

## Student Cannot See Result

Confirm:

- account belongs to the submission student
- temporary password has been replaced
- account is enabled
- teacher explicitly released the submission
- submission remains active

Teacher visibility does not imply student release.

## Analytics Look Incomplete

Questions without mapped answer fragments currently create no criterion evaluation rows, which can undercount attempts in evaluation-based analytics. Class and exam endpoints also apply different status/archive/membership scopes. Inspect source submissions before interpreting aggregates.

## Browser Console CSP Error

Cloudflare Browser Insights injection is blocked by the current CSP. The application can continue to work, but the console reports the blocked script. Disable the injection or make a narrowly reviewed CSP change; do not add broad script/connect wildcards.

## Frontend Mutation Appears To Do Nothing

Several paper-review handlers do not surface every non-2xx error. Inspect the request in the network panel, especially CSRF status. Reload the submission to verify persisted state instead of trusting local UI state.

## Collecting A Support Report

Include:

- deployment version/commit
- route and method
- HTTP status and sanitized error detail
- submission/exam ID when policy permits
- processing state and timestamps
- backend model and prompt operation name
- whether the issue reproduces locally

Exclude secrets, tokens, passwords, database credentials, and full student paper/transcription content.
