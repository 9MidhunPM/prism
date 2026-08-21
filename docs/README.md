# PRISM documentation

PRISM is an evidence-first assessment workspace for teachers who still receive
handwritten examination papers. This documentation describes the current
hackathon implementation at the latest fetched commit, `e280661`.

## Start here

| Need | Read |
| --- | --- |
| Understand the product and its boundaries | [Product requirements](../PRD.md) |
| Understand the smallest complete demo | [MVP specification](../MVP.md) |
| Install and configure the application | [Operations guide](operations.md) |
| Understand the code and data flow | [Architecture](architecture.md) |
| Follow a teacher through the product | [Workflows](workflows.md) |
| Integrate with the API | [API reference](api.md) |
| Prepare a reliable presentation | [Demo runbook](demo-runbook.md) |
| Capture or refresh UI evidence | [Screenshot guide](screenshots.md) |
| Check source-vs-contract mismatches | [Known gaps](known-gaps.md) |

## Documentation contract

- Examples use placeholder credentials such as `teacher@example.com`. Never
  copy a real password into this repository.
- Claims about the runtime are based on the checked-out source. If a deployed
  environment differs, record the deployment URL, commit SHA, and date next to
  the observation.
- AI output is treated as a suggestion. A teacher owns the final mark.
- Numeric totals, percentages, mastery values, and review rates are calculated
  by application code, not accepted from model prose.
- Source paper images are evidence. A transcription is an aid and may be
  uncertain or incomplete.

## Current surface map

The teacher-facing frontend currently exposes:

| Route | Purpose |
| --- | --- |
| `/login` | Teacher or student sign-in |
| `/` | Teacher assessment-review dashboard |
| `/exams` | Exam list and archive controls |
| `/exams/new` | Create an exam and rubric |
| `/exams/:id` | Upload papers, inspect processing, manage roster |
| `/exams/:id/insights` | Exam-level analytics |
| `/submissions` | Search papers and processing states |
| `/submissions/:id` | Evidence-first paper review |
| `/classes` | Teacher class and roster management |
| `/classes/:id` | Class detail and membership |
| `/students/:id` | Student profile and evidence-backed trends |
| `/assistant` | Grounded teacher questions |

The student-facing surface is intentionally smaller: `/student` exposes only
released results and `/student/profile` exposes the student's own learning
profile.

## The product sentence

> Physical assessment evidence becomes explainable, teacher-controlled grading
> and useful learning intelligence.
