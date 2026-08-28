# Security And Privacy

PRISM processes student identities, handwritten papers, marks, and educational evidence. Treat every environment as an educational-record system, even during a demo.

## Authentication

- Passwords use `scrypt` with a random salt.
- Successful login creates a random opaque session and CSRF token.
- Only SHA-256 token hashes are stored in `auth_sessions`.
- The session cookie is `HttpOnly` and `SameSite=Lax`.
- Production requires the cookie `Secure` flag.
- Sessions expire and can be revoked.
- Disabling a student account revokes active sessions.
- Changing a password revokes all older sessions and creates a new one.

Teacher and student routes enforce role and ownership on the backend. Client-side redirects are not authorization.

## CSRF And Origin Checks

Unsafe requests require the readable CSRF cookie value in `X-CSRF-Token`. Middleware also validates request origin and `Sec-Fetch-Site`. Login and initial bootstrap are exempt.

Custom clients must preserve the session cookie and send the CSRF header. Do not disable CSRF to simplify scripts.

## Secrets

Keep these values in a secret manager or protected deployment environment:

- `OPENAI_API_KEY`
- `SESSION_SECRET`
- `DATABASE_URL` credentials
- any future S3 secret access key
- demo passwords if a private demo environment uses them

Never expose server secrets through `NEXT_PUBLIC_*`. Google browser client IDs, project numbers, and a referrer-restricted API key are intentionally public, but still require platform restrictions.

Rotate secrets after accidental exposure. Rotating database or OpenAI credentials requires service restart. Rotating session-related policy should include revoking existing `auth_sessions` if compromise is suspected.

For a suspected session compromise, revoke all active sessions in an approved
administrative procedure, rotate `SESSION_SECRET` if it is exposed, restart the
backend, and require affected users to sign in again. Do not delete audit or
assessment records as a substitute for session revocation.

## Production Requirements

The settings validator enforces:

- `APP_ENV=production`
- a session secret of at least 32 characters
- `SESSION_COOKIE_SECURE=true`
- PostgreSQL `DATABASE_URL`
- `DEMO_MODE=false`
- HTTPS CORS origins without localhost

Teacher HTTP bootstrap is unavailable in detected production. Although bootstrap token settings exist, the current route does not validate the supplied token; use an approved administrative provisioning process.

## Rate Limiting

Login and general request limits use in-memory sliding windows. They are basic abuse controls, not a distributed defense:

- limits reset at restart
- limits are independent per API replica
- keys depend on observed client address/path category

Apply reverse-proxy or edge rate limits for an internet-facing deployment, especially for login and AI-expensive routes.

## Uploads

The backend validates declared MIME type, file signatures, total bytes, and normalized page count. It accepts JPEG, PNG, and PDF. Pillow and PyMuPDF parse untrusted content inside the API container.

Operational controls should include:

- non-root containers
- CPU/memory/request limits
- current parser dependencies
- restricted filesystem permissions
- no public access to upload paths
- backup encryption and retention policy

Media endpoints authorize every page request. Do not serve `UPLOAD_ROOT` as a public static directory.

## Educational Data

Permitted profile interpretations are limited to assessment evidence:

- mastered, developing, and weak concepts
- recurring misconceptions
- score trends
- rubric performance
- linked evidence

Do not infer IQ, intelligence, personality, laziness, motivation, mental health, cheating tendency, honesty, or unrelated personal traits.

Use synthetic or explicitly approved demo data in screenshots and public presentations. The committed screenshots were captured from the supplied demo workspace and exclude credentials and tokens, but they still show names and assessment content visible to that account.

## AI Data Handling

Relevant page images, transcription, rubric, answer key, and scoped teacher context may be sent to OpenAI. Before production use:

- obtain required institutional approval and notices
- verify provider retention and regional requirements
- minimize included records
- avoid sending the entire database to assistant queries
- document deletion and data-subject procedures
- restrict API-key access and billing limits

The teacher assistant receives resolved records and calculated concept statistics rather than an unrestricted database dump.

## Teacher Authority

AI marks are suggestions. A review model returns an unapplied proposal. A teacher must accept it before it becomes an override. Direct teacher marks take precedence in effective-score calculation.

Do not implement automatic application of re-evaluated marks without changing the product's authority and audit requirements.

## Browser Security

Next.js sets Content Security Policy, anti-framing, referrer, content-type, and permissions headers. Google APIs and account frames receive narrowly listed exceptions for Drive Picker.

Cloudflare analytics injection is currently blocked by CSP. Prefer disabling unnecessary injection or adding only the exact required origins after review. Do not add broad wildcards or `unsafe-eval` as a shortcut.

## Logging

Never log:

- passwords
- session or CSRF tokens
- Google OAuth access tokens
- `OPENAI_API_KEY`
- full database URLs with credentials
- full paper bytes or unnecessary transcription

The repository's desired AI observability fields include submission, operation, model, duration, result, usage, and estimated cost, but structured logging and usage persistence are incomplete in the current implementation.

## Deletion And Backups

Application deletion deeply removes active database records and attempts media cleanup. Backups can retain prior copies. Publish a retention schedule that explains archive behavior, hard deletion, backup expiration, and restore access.

See [backups and recovery](backups-and-recovery.md) for operational data copies.

## Incident Checklist

1. Contain public access or disable affected credentials.
2. Preserve relevant logs without copying secrets into tickets.
3. Revoke sessions and rotate compromised credentials.
4. Identify affected teacher, student, exam, submission, and media records.
5. Notify the responsible educational-data owner.
6. Restore from verified backups only when integrity is compromised.
7. Record remediation and update tests/runbooks.

If the incident involves a live paper or student identity, limit the incident
record to the minimum identifiers needed for response and use the organization's
educational-data notification process.
