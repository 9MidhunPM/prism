# PRISM Documentation

This documentation describes the current implementation at the checked-out commit. Product planning and historical intent live in `PRD.md` and `MVP.md`; known source-versus-contract mismatches are listed in [Known gaps](known-gaps.md).

## Reading Order

1. Start with [Product overview](guides/product-overview.md) if you are learning PRISM.
2. Follow the [Teacher guide](guides/teacher-guide.md) to use the application.
3. Use [Local development](guides/local-development.md) to run it.
4. Read [Architecture](reference/architecture.md) and [API reference](reference/api.md) before changing code.
5. Read [Deployment](operations/deployment.md), [Security](operations/security.md), and [Backups](operations/backups-and-recovery.md) before operating a public environment.

## Start Here

| Need | Read |
| --- | --- |
| Understand the product and boundaries | [Product overview](guides/product-overview.md) |
| Understand the smallest complete demo | [MVP specification](../MVP.md) |
| Install and configure the application | [Local development](guides/local-development.md) |
| Understand code and data flow | [Architecture](reference/architecture.md) |
| Follow a teacher through the product | [Teacher guide](guides/teacher-guide.md) |
| Follow the student portal | [Student guide](guides/student-guide.md) |
| Integrate with the API | [API reference](reference/api.md) |
| Prepare a reliable presentation | [Demo runbook](demo-runbook.md) |
| Operate a deployment | [Operations](operations.md) and [deployment runbook](operations/deployment.md) |
| Check source-versus-contract mismatches | [Known gaps](known-gaps.md) |

## Product Guides

- [Product overview](guides/product-overview.md): capabilities, roles, and core concepts
- [Teacher guide](guides/teacher-guide.md): classes, exams, imports, review, release, and analytics
- [Student guide](guides/student-guide.md): first sign-in, released results, and learning profile
- [Local development](guides/local-development.md): prerequisites, setup, demo accounts, and commands
- [Google Drive import](guides/google-drive-import.md): Cloud setup, folder structure, preview, and commit behavior
- [Workflows](workflows.md): concise end-to-end teacher and student flow

## Engineering Reference

- [Architecture](reference/architecture.md): system boundaries, request flow, and deployment topology
- [Domain model](reference/domain-model.md): persisted entities and relationships
- [API reference](reference/api.md): implemented routes, authorization, and common behavior
- [AI pipeline](reference/ai-pipeline.md): operations, models, prompts, schemas, evidence, and scoring
- [Configuration](reference/configuration.md): environment variables and implementation status
- [Processing states](reference/processing-states.md): lifecycle and review signals
- [Testing](reference/testing.md): automated coverage and verification commands

## Operations

- [Operations overview](operations.md): compact operations and configuration reference
- [Deployment](operations/deployment.md): container topology, migrations, health checks, and rollout
- [Security and privacy](operations/security.md): authentication, CSRF, secrets, and educational-data constraints
- [Backups and recovery](operations/backups-and-recovery.md): databases, media, restore checks, and job recovery
- [Troubleshooting](operations/troubleshooting.md): common local and production failures

## Source Of Truth

When documents disagree, use this order:

1. Executable source and tests
2. [Known gaps](known-gaps.md)
3. Canonical guides and references in this directory
4. Product planning in `PRD.md` and `MVP.md`

Documentation changes should identify whether a statement is implemented, observed in a deployment, or planned.

## Demo And Visual Evidence

- [Demo runbook](demo-runbook.md): reliable presentation flow and fallback plan
- [Screenshot guide](screenshots.md): how to capture sanitized product evidence
- [Captured screenshots](assets/screenshots/): hosted product screens captured with Playwright
- [Wireframes](screenshots/): illustrative future/demo visuals, not claims about rendered UI

Captured screenshots were taken from the hosted application with Playwright on August 21, 2026. They contain assessment data visible to the supplied demo teacher account, but no passwords, session cookies, CSRF tokens, OAuth tokens, or API keys.

## Documentation Contract

- Describe current code as fact; label proposed work explicitly.
- Never place production credentials or private student data in documentation.
- Examples use placeholders such as `teacher@example.com`; never copy real credentials into this repository.
- If a deployed environment differs from source, record URL, commit SHA, and observation date.
- AI output is a suggestion; a teacher owns the final mark.
- Numeric totals, percentages, mastery values, and review rates are calculated by application code.
- Source paper images are evidence; transcription is an aid and may be uncertain.
- Recheck commands, endpoint names, prompt versions, environment variables, and screenshots when behavior changes.
