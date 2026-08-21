# PRISM Frontend

Next.js teacher and student interface for evidence-linked handwritten assessment review.

## Responsibilities

- teacher session navigation and role-aware route guards
- classes, rosters, student access, and learning profiles
- manual and AI-assisted exam/rubric creation
- direct and Google Drive paper imports
- processing progress and paper lists
- original-page evidence review, challenge, override, and release
- exam/class analytics and grounded assistant queries
- released student results and concept profile

The FastAPI backend remains the authorization, scoring, persistence, and AI boundary.

## Requirements

- Node.js 22
- npm
- running PRISM backend on port `8000` locally

## Getting Started

From `frontend/`:

```bash
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The browser calls relative `/api` routes. `next.config.ts` rewrites them to the first configured value:

1. `BACKEND_INTERNAL_URL`
2. `NEXT_PUBLIC_API_URL`
3. `http://localhost:8000`

## Environment Variables

| Variable | Purpose | Required |
| --- | --- | --- |
| `BACKEND_INTERNAL_URL` | Private backend origin for the Next.js rewrite | Production |
| `NEXT_PUBLIC_API_URL` | Fallback API origin/build argument | Optional locally |
| `NEXT_PUBLIC_GOOGLE_DRIVE_CLIENT_ID` | Google OAuth web client ID | Drive import |
| `NEXT_PUBLIC_GOOGLE_DRIVE_API_KEY` | Origin/API-restricted browser key | Drive import |
| `NEXT_PUBLIC_GOOGLE_DRIVE_APP_ID` | Google Cloud project number | Drive import |
| `NEXT_PUBLIC_GOOGLE_DRIVE_SCOPE` | OAuth scope; defaults to Drive read-only | Optional |

`NEXT_PUBLIC_*` values are visible in the browser and compiled during build. Never place private credentials in them.

## Commands

```bash
npm run dev
npm run lint
npm run format
npm run build
npm run start
```

## Route Map

| Route | Role | Purpose |
| --- | --- | --- |
| `/login` | Public | Teacher/student sign-in |
| `/` | Teacher | Workspace and review queue |
| `/classes` | Teacher | Class catalogue and creation |
| `/classes/[id]` | Teacher | Roster, access, and class analytics |
| `/students/[id]` | Teacher | Student profile and evidence sources |
| `/exams` | Teacher | Exam catalogue |
| `/exams/new` | Teacher | Exam, rubric, question-paper, and answer-key setup |
| `/exams/[id]` | Teacher | Upload/Drive import, marking plan, and submissions |
| `/exams/[id]/insights` | Teacher | Exam analytics |
| `/submissions` | Teacher | Filtered paper catalogue |
| `/submissions/[id]` | Teacher | Evidence review workbench |
| `/assistant` | Teacher | Scoped single-turn assistant |
| `/student` | Student | Released results and learning profile |

## Authentication And CSRF

`SessionProvider` loads `/api/auth/me`. `SessionGuard` handles role-aware redirects but is not a security boundary. Protected requests must be authorized by FastAPI.

`lib/api.ts` sends cookies and copies the `prism_csrf` cookie into `X-CSRF-Token` for unsafe requests. Use it for authenticated mutations rather than a raw `fetch` unless the caller implements the same behavior.

## Project Layout

```text
frontend/
|-- app/                       App Router pages and global CSS
|-- components/                Session, shell, account, and Drive UI
|-- lib/                       API client, types, and display helpers
|-- public/                    Static assets
|-- next.config.ts             Rewrite and security headers
|-- biome.json                 Lint/format configuration
`-- Dockerfile                 Node 22 standalone production image
```

## Verification

```bash
npm run lint
npm run build
```

No frontend unit or end-to-end suite is currently committed. Use the repository [testing guide](../docs/reference/testing.md) for the manual browser smoke test and known coverage gaps.

## Documentation

- [Local development](../docs/guides/local-development.md)
- [Teacher guide](../docs/guides/teacher-guide.md)
- [Architecture](../docs/reference/architecture.md)
- [Configuration](../docs/reference/configuration.md)
- [Deployment](../docs/operations/deployment.md)
