# PRISM Documentation

The documentation in this directory describes the behavior implemented in the current repository. Product planning and historical design decisions live in the root `PRD.md` and `MVP.md` files.

## Product Guides

- [Product overview](guides/product-overview.md): capabilities, roles, and core concepts
- [Teacher guide](guides/teacher-guide.md): classes, exams, imports, review, release, and analytics
- [Student guide](guides/student-guide.md): first sign-in, released results, and learning profile
- [Local development](guides/local-development.md): prerequisites, setup, demo accounts, and commands
- [Google Drive import](guides/google-drive-import.md): Cloud setup, folder structure, preview, and commit behavior

## Engineering Reference

- [Architecture](reference/architecture.md): system boundaries, request flow, and deployment topology
- [Domain model](reference/domain-model.md): persisted entities and relationships
- [API reference](reference/api.md): implemented routes, authorization, and common behavior
- [AI pipeline](reference/ai-pipeline.md): operations, models, prompts, schemas, evidence, and scoring
- [Configuration](reference/configuration.md): environment variables and implementation status
- [Processing states](reference/processing-states.md): lifecycle and review signals
- [Testing](reference/testing.md): automated coverage and verification commands

## Operations

- [Deployment](operations/deployment.md): container topology, migrations, health checks, and rollout
- [Security and privacy](operations/security.md): authentication, CSRF, secrets, and educational-data constraints
- [Backups and recovery](operations/backups-and-recovery.md): databases, media, restore checks, and job recovery
- [Troubleshooting](operations/troubleshooting.md): common local and production failures

## Screenshots

Screenshots were captured from the hosted application with Playwright on August 21, 2026. They contain assessment data visible to the supplied demo teacher account, but no passwords, session cookies, CSRF tokens, OAuth tokens, or API keys.

| Screen | Preview |
| --- | --- |
| Teacher workspace | [dashboard.png](assets/screenshots/dashboard.png) |
| Exam catalogue | [exams.png](assets/screenshots/exams.png) |
| Exam and upload workflow | [exam-detail.png](assets/screenshots/exam-detail.png) |
| Evidence review workbench | [review-workbench.png](assets/screenshots/review-workbench.png) |
| Exam analytics | [exam-insights.png](assets/screenshots/exam-insights.png) |

## Documentation Rules

- Describe current code as fact; label proposed work explicitly.
- Never place production credentials or private student data in documentation.
- Recheck commands, endpoint names, prompt versions, and environment variables when behavior changes.
- Update the relevant guide in the same change as a user-facing or operational change.
