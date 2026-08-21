# Backups And Recovery

PRISM has two persistence surfaces: the SQL database and the upload cache. Back up both even though original and processed page bytes are also stored in database columns.

## Backup Scope

### PostgreSQL

The database contains:

- teacher and student identities
- password hashes and active sessions
- classes and memberships
- exams, questions, rubrics, and answer keys
- submissions, page metadata, and page blobs
- transcription, evidence, evaluations, reviews, and overrides
- processing jobs and AI artifacts
- Google Drive import manifests

Use managed point-in-time recovery or scheduled encrypted dumps. Protect backups as educational records.

### Upload Volume

Back up `UPLOAD_ROOT`, `/app/data/uploads` in the backend container by default. It contains original and normalized media cache files. Database blobs can restore missing page files, but relying on that alone increases recovery load and does not replace a tested media backup.

## PostgreSQL Example

Create a compressed logical backup from a trusted administrative environment:

```bash
pg_dump --format=custom --file=prism.dump "$DATABASE_URL"
```

Restore into an empty database:

```bash
pg_restore --clean --if-exists --no-owner --dbname="$RESTORE_DATABASE_URL" prism.dump
```

Do not run a destructive restore against production without a change plan, current backup, and owner approval.

## Consistency

For a consistent snapshot:

1. Stop new uploads and Drive commits.
2. Wait for active processing jobs to finish when possible.
3. Record active job and submission IDs.
4. Back up PostgreSQL.
5. Snapshot or archive the upload volume immediately afterward.
6. Resume traffic.

Page blobs reduce but do not eliminate the need for database/media consistency.

## Retention

Define and enforce:

- backup frequency
- retention duration
- encryption at rest and in transit
- permitted backup operators
- geographic/storage requirements
- deletion expiration for student records
- restore-test frequency

Repository code does not implement a backup scheduler or retention policy.

## Restore Verification

Restore into an isolated environment, never directly into the live database for testing.

1. Restore PostgreSQL and media to isolated resources.
2. Set `APP_ENV` and URLs for the isolated environment.
3. Run `python -m app.migrate` to move the restored schema forward if required.
4. Verify `/api/health/ready`.
5. Sign in with an approved test account.
6. Open an exam, submission, original page, evidence, and analytics.
7. Confirm teacher overrides and release state survived.
8. Confirm student access cannot see unreleased or other-student results.
9. Destroy the isolated restore according to data policy.

Record restore duration and failures so recovery objectives are evidence-based.

## Interrupted Processing

Processing runs inside the FastAPI process. After an API restart:

1. Query the teacher UI or database for jobs left in `uploaded`, `preprocessing`, `transcribing`, `structured`, or `grading`.
2. Confirm no process is still working on the submission.
3. Inspect stored pages and latest error.
4. Use the supported process/retry route only when the current submission state allows it.
5. If the state is stuck in an active stage, resolve it through a reviewed administrative procedure before retrying.
6. Verify derived evaluations are complete before releasing results.

Do not blindly schedule every active record. Scheduling is not protected by a durable queue lock, and duplicate processing can conflict.

## Missing Media

Authorized media access attempts to restore missing filesystem files from `SubmissionPage.original_data` or `processed_data`.

If restoration fails:

- verify volume mount and ownership for UID `10001`
- verify database blob presence
- verify available disk space
- compare stored checksum/source hash where applicable
- restore the matching volume backup

Never substitute a different page without using the application replacement flow and recording the teacher's intent.

## Database Migration Failure

The backend entrypoint does not start Uvicorn if migration fails.

1. Keep the failed image out of service.
2. Preserve migration logs without exposing the database URL.
3. Check database reachability and permissions.
4. Confirm only one expected migration chain is present.
5. Restore the pre-deployment backup if schema/data integrity changed.
6. Fix forward with a new reviewed migration where possible.

Treat Alembic downgrade support as migration-specific; it is not a general production rollback guarantee.

## Disaster Recovery Priorities

1. Protect student data from further exposure or corruption.
2. Restore PostgreSQL integrity and authentication state.
3. Restore original page evidence and normalized media.
4. Validate rubric, evaluations, reviews, and teacher overrides.
5. Validate release isolation and analytics.
6. Resume live AI processing last.
