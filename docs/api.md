# API Reference

The complete implemented route inventory is maintained in [reference/api.md](reference/api.md).

## Common Rules

- The FastAPI service is available locally at `http://localhost:8000`.
- Browser authentication uses an opaque session token and a separate CSRF token; it is not a signed-cookie API.
- Login and bootstrap are CSRF-exempt. Other unsafe authenticated requests require the matching `X-CSRF-Token` header.
- Teacher routes enforce teacher ownership. Student routes enforce student ownership and release state.
- Numeric totals and percentages are calculated by backend code.
- Review suggestions remain unapplied until a teacher accepts them.

## Main Route Groups

| Area | Reference |
| --- | --- |
| Health and authentication | [reference/api.md#health](reference/api.md#health) |
| Classes and students | [reference/api.md#dashboard-and-classes](reference/api.md#dashboard-and-classes) |
| Exams and imports | [reference/api.md#exams-and-imports](reference/api.md#exams-and-imports) |
| Submissions and pages | [reference/api.md#submissions-and-pages](reference/api.md#submissions-and-pages) |
| Review and overrides | [reference/api.md#review-and-overrides](reference/api.md#review-and-overrides) |
| Student portal | [reference/api.md#student-routes](reference/api.md#student-routes) |
| Jobs and assistant | [reference/api.md#jobs-and-assistant](reference/api.md#jobs-and-assistant) |

FastAPI's generated `/docs` and `/openapi.json` are available when the deployment exposes them. Treat the source route definitions in `backend/app/main.py` as authoritative.
