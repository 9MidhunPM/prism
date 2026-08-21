# API Reference

The FastAPI application exposes JSON and media routes under `/api`. Interactive OpenAPI documentation is available at `/docs` and the schema at `/openapi.json` when those FastAPI defaults are reachable in the deployment.

## Authentication

PRISM uses an opaque session cookie and a separate CSRF cookie. Browser clients must send credentials. Unsafe authenticated methods must copy the `prism_csrf` cookie value into `X-CSRF-Token`.

```text
Cookie: prism_session=<opaque token>; prism_csrf=<token>
X-CSRF-Token: <same csrf token>
```

Login and initial bootstrap are CSRF-exempt. Backend teacher/student role and ownership checks are authoritative.

## Health

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/health` | Public | Process health, display model, and AI-key presence |
| `GET` | `/api/health/ready` | Public | Database connectivity and exact migration revision |

## Authentication Routes

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/auth/bootstrap` | Public, non-production | Create the first teacher |
| `POST` | `/api/auth/login` | Public | Create a teacher or student session |
| `POST` | `/api/auth/logout` | Session/CSRF | Revoke the current session and clear cookies |
| `GET` | `/api/auth/me` | Authenticated | Return current identity and role |
| `POST` | `/api/auth/change-password` | Authenticated | Verify old password, replace it, and rotate sessions |

Production rejects teacher bootstrap regardless of the documented bootstrap configuration values. The accepted `X-Bootstrap-Token` parameter is not validated by current route code; do not rely on it as a production provisioning mechanism.

## Dashboard And Classes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/dashboard` | Teacher metrics, recent submissions, concept attention, and review queue |
| `GET` | `/api/classes` | List teacher-owned classes |
| `POST` | `/api/classes` | Create a class |
| `GET` | `/api/classes/{class_id}` | Class detail, roster, and memberships |
| `PATCH` | `/api/classes/{class_id}` | Rename/update a class |
| `PATCH` | `/api/classes/{class_id}/archive` | Archive or restore a class |
| `DELETE` | `/api/classes/{class_id}` | Delete an empty class |
| `POST` | `/api/classes/{class_id}/students` | Create a primary student |
| `POST` | `/api/classes/{class_id}/memberships` | Add an existing student membership |
| `POST` | `/api/classes/{class_id}/students/import` | Atomically import up to 200 roster rows |
| `GET` | `/api/classes/{class_id}/analytics` | Deterministic class analytics |

## Students

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/students` | Search active teacher-owned students |
| `PUT` | `/api/students/{student_id}/account` | Create/reset student access |
| `PATCH` | `/api/students/{student_id}/account` | Enable or disable access |
| `PATCH` | `/api/students/{student_id}/archive` | Archive or restore a student |
| `DELETE` | `/api/students/{student_id}` | Deep-delete a student and dependent data |
| `GET` | `/api/students/{student_id}/profile` | Teacher-facing deterministic profile |

## Exams And Imports

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/exams` | Create an exam with questions and rubrics |
| `GET` | `/api/exams` | List exams |
| `GET` | `/api/exams/{exam_id}` | Retrieve exam and marking plan |
| `PATCH` | `/api/exams/{exam_id}/archive` | Archive or restore an exam |
| `DELETE` | `/api/exams/{exam_id}` | Deep-delete exam and papers unless actively processing |
| `POST` | `/api/exam-drafts/import` | Extract an editable exam draft from JPEG/PNG/PDF |
| `POST` | `/api/answer-keys/import` | Extract answer-key entries for supplied question numbers |
| `GET` | `/api/exams/{exam_id}/analytics` | Deterministic exam analytics |

### Drive Import

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/exams/{exam_id}/imports/drive/preview` | Discover folder/page matches and persist preview batch |
| `POST` | `/api/imports/{batch_id}/commit` | Download selected pages, create papers, and queue processing |

## Submissions And Pages

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/submissions` | List/filter teacher-owned papers |
| `POST` | `/api/exams/{exam_id}/submissions` | Upload and queue a paper |
| `POST` | `/api/submissions/{submission_id}/process` | Queue initial processing |
| `POST` | `/api/submissions/{submission_id}/retry` | Retry eligible failed/rescan paper |
| `GET` | `/api/submissions/{submission_id}/status` | Return stage, attempts, error, and update time |
| `GET` | `/api/submissions/{submission_id}` | Complete teacher evidence-review representation |
| `PATCH` | `/api/submissions/{submission_id}/release` | Release or withdraw student visibility |
| `PATCH` | `/api/submissions/{submission_id}/archive` | Archive or restore a paper |
| `DELETE` | `/api/submissions/{submission_id}` | Deep-delete paper data and media |
| `PATCH` | `/api/submissions/{submission_id}/student` | Reassign an active paper and revoke release |
| `PUT` | `/api/submissions/{submission_id}/pages/{page_id}` | Replace an eligible image page and reprocess |
| `GET` | `/api/pages/{page_id}` | Return teacher-authorized original media |
| `GET` | `/api/pages/{page_id}/preview` | Return normalized preview media |

Upload accepts multipart form data. Supported files are JPEG, PNG, and PDF, subject to configured byte and page limits.

## Review And Overrides

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/evaluations/{evaluation_id}/review` | Create an unapplied AI review suggestion |
| `POST` | `/api/reviews/{review_id}/{decision}` | Accept or reject a pending suggestion |
| `POST` | `/api/evaluations/{evaluation_id}/complete-review` | Resolve review while retaining current mark |
| `PATCH` | `/api/evaluations/{evaluation_id}` | Apply a direct bounded teacher override |
| `GET` | `/api/evaluations/{evaluation_id}/history` | Return override and suggestion history |

`decision` is `accept` or `reject`. Acceptance records a teacher override; the review model never directly applies a mark.

## Student Routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/student/submissions` | List released papers belonging to current student |
| `GET` | `/api/student/submissions/{submission_id}` | Return one released result |
| `GET` | `/api/student/pages/{page_id}/preview` | Authorized preview for a released owned paper |
| `GET` | `/api/student/profile` | Profile calculated from released submissions |

## Jobs And Assistant

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/processing-jobs` | List active and failed teacher-owned jobs |
| `POST` | `/api/assistant/query` | Answer one grounded query over resolved records/statistics |
| `GET` | `/api/assistant/mentions` | Search mention candidates across records |

## Common Responses

- `400`: invalid input or unsupported state transition
- `401`: missing, expired, revoked, or temporary-password-restricted session
- `403`: role, ownership, origin, or CSRF failure
- `404`: record not found in authorized scope
- `409`: conflicting state, duplicate, pending review, or active processing
- `413`: upload exceeds configured size
- `422`: schema validation failure
- `429`: process-local rate limit exceeded
- `500`: unhandled server failure
- `503`: readiness failure or unavailable configured operation

Error bodies generally contain a FastAPI `detail` field. Media routes return binary responses rather than JSON.
