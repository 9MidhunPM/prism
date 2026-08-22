# API reference

The API is served by FastAPI under `/api`. Examples use `http://localhost:8000`
and placeholder credentials. The browser client sends cookies and the CSRF
header required by unsafe authenticated requests.

## 1. Common rules

- JSON responses use typed Pydantic models or explicit dictionaries.
- Mutating requests require an authenticated session, trusted origin, and the
  CSRF token returned by the session flow when applicable.
- Teacher resources are scoped to the current teacher.
- Student resources are scoped to the current student.
- `401` means no valid session, `403` means insufficient role or request
  protection failure, `404` means the owned resource was not found, `409` means
  a state conflict, `422` means validation failure, and `429` means rate limit.

## 2. Health and authentication

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness, configured model, AI enabled flag |
| `GET` | `/api/health/ready` | Database/schema readiness |
| `POST` | `/api/auth/bootstrap` | Protected first teacher setup |
| `POST` | `/api/auth/login` | Create signed session |
| `POST` | `/api/auth/logout` | Revoke current session |
| `GET` | `/api/auth/me` | Return current account and role |
| `POST` | `/api/auth/change-password` | Change a temporary/current password |

Example login shape (use a local placeholder, never a real committed secret):

```json
{
  "email": "teacher@example.com",
  "password": "replace-with-local-secret"
}
```

The successful response is intentionally small. The password is never echoed.

## 3. Classes and students

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/classes` | List teacher-owned classes |
| `POST` | `/api/classes` | Create a class |
| `GET` | `/api/classes/{class_id}` | Read class and roster |
| `PATCH` | `/api/classes/{class_id}` | Rename a class |
| `PATCH` | `/api/classes/{class_id}/archive` | Archive/unarchive class |
| `DELETE` | `/api/classes/{class_id}` | Delete class and dependent data |
| `POST` | `/api/classes/{class_id}/students` | Add one student |
| `POST` | `/api/classes/{class_id}/students/import` | Import a roster |
| `POST` | `/api/classes/{class_id}/memberships` | Add an existing student |
| `GET` | `/api/students` | Search teacher-owned students |
| `PATCH` | `/api/students/{student_id}/archive` | Archive/unarchive student |
| `DELETE` | `/api/students/{student_id}` | Delete a student |
| `PUT` | `/api/students/{student_id}/account` | Provision a student account |
| `PATCH` | `/api/students/{student_id}/account` | Disable/un-disable account |
| `GET` | `/api/students/{student_id}/profile` | Read teacher-side profile |

## 4. Exams and imports

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/exams` | List exams |
| `POST` | `/api/exams` | Create exam with questions and criteria |
| `GET` | `/api/exams/{exam_id}` | Read exam details |
| `PATCH` | `/api/exams/{exam_id}/archive` | Archive/unarchive exam |
| `DELETE` | `/api/exams/{exam_id}` | Delete exam and dependent papers |
| `POST` | `/api/exam-drafts/import` | Parse a draft exam PDF |
| `POST` | `/api/answer-keys/import` | Parse teacher answer-key pages |
| `POST` | `/api/exams/{exam_id}/imports/drive/preview` | Preview Drive import |
| `POST` | `/api/imports/{batch_id}/commit` | Commit selected Drive items |
| `GET` | `/api/exams/{exam_id}/analytics` | Read exam statistics |
| `GET` | `/api/exams/{exam_id}/insights` | Frontend-facing insight data |

Exam creation validates positive criterion marks and stores the rubric before a
paper can be graded.

## 5. Submissions and media

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/submissions` | Filter teacher-owned papers |
| `POST` | `/api/exams/{exam_id}/submissions` | Upload one paper |
| `POST` | `/api/submissions/{submission_id}/process` | Start or resume processing |
| `POST` | `/api/submissions/{submission_id}/retry` | Retry a failed job |
| `GET` | `/api/submissions/{submission_id}/status` | Read current stage |
| `GET` | `/api/submissions/{submission_id}` | Read paper, answers, evaluations |
| `PATCH` | `/api/submissions/{submission_id}/release` | Release or hold student results |
| `PATCH` | `/api/submissions/{submission_id}/archive` | Archive/unarchive paper |
| `DELETE` | `/api/submissions/{submission_id}` | Delete paper and unreferenced media |
| `PATCH` | `/api/submissions/{submission_id}/student` | Reassign paper to roster student |
| `PUT` | `/api/submissions/{submission_id}/pages/{page_id}` | Replace one page |
| `GET` | `/api/pages/{page_id}` | Return original page bytes |
| `GET` | `/api/pages/{page_id}/preview` | Return processed preview |
| `GET` | `/api/processing-jobs` | List active or recent jobs |

Upload uses multipart form data. The page list, original availability, preview
availability, quality, and dimensions are returned with submission details.

## 6. Evaluation and teacher control

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/evaluations/{evaluation_id}/review` | Ask Luna to review one criterion |
| `POST` | `/api/reviews/{review_id}/accept` | Accept review suggestion |
| `POST` | `/api/reviews/{review_id}/reject` | Reject review suggestion |
| `POST` | `/api/evaluations/{evaluation_id}/complete-review` | Mark review workflow resolved |
| `PATCH` | `/api/evaluations/{evaluation_id}` | Apply explicit teacher marks/reason |
| `GET` | `/api/evaluations/{evaluation_id}/history` | Read evaluation history |

An override request contains a non-negative mark and optional reason. Backend
validation still ensures it does not exceed the criterion maximum. The response
must make the effective teacher value distinguishable from the AI suggestion.

## 7. Analytics, student views, and assistant

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/classes/{class_id}/analytics` | Class aggregates |
| `GET` | `/api/student/submissions` | Released student papers |
| `GET` | `/api/student/submissions/{submission_id}` | One released paper |
| `GET` | `/api/student/profile` | Own learning profile |
| `GET` | `/api/student/pages/{page_id}/preview` | Own evidence preview |
| `GET` | `/api/assistant/mentions` | Resolve mention candidates |
| `POST` | `/api/assistant/query` | Ground and answer teacher query |

The assistant request has a question and optional typed mentions:

```json
{
  "question": "Which concept should I revise tomorrow?",
  "mentions": [{"type": "class", "id": "class-id"}]
}
```

The API retrieves the relevant evidence before invoking Luna. It does not send
the entire database.

## 8. Testing API behavior

The most important API invariants are tested in `backend/tests/`:

- `test_scoring.py` checks bounds and deterministic totals;
- `test_ai_schemas.py` checks typed response rejection;
- `test_auth.py` checks login, roles, sessions, and password behavior;
- `test_migrations.py` checks schema upgrades;
- `test_settings.py` checks development/production configuration.
