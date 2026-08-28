# Screenshots And Visual Evidence

The repository contains both real hosted captures and illustrative wireframes. Do not treat them as interchangeable.

## Real Captures

These screenshots were captured with Playwright from `https://prism.midhunpm.in` on August 21, 2026 using an approved demo teacher session. They contain no passwords, session cookies, CSRF tokens, OAuth tokens, or API keys, but they may show assessment data visible to that account. Treat the images as demo evidence, not as a guarantee that hosted data or deployment code remains unchanged.

| Screen | File | Evidence |
| --- | --- | --- |
| Teacher workspace | `docs/assets/screenshots/dashboard.png` | Teacher navigation and workspace |
| Exam catalogue | `docs/assets/screenshots/exams.png` | Assessment list |
| Exam detail | `docs/assets/screenshots/exam-detail.png` | Upload, Drive import, marking plan, submissions |
| Evidence review | `docs/assets/screenshots/review-workbench.png` | Original pages, criteria, evidence, confidence |
| Exam analytics | `docs/assets/screenshots/exam-insights.png` | Deterministic exam metrics and performance tables |

## Wireframes

The SVGs in `docs/screenshots/` are illustrative only:

- [Evidence review wireframe](screenshots/evidence-review-wireframe.svg)
- [Class analytics wireframe](screenshots/class-analytics-wireframe.svg)

They do not prove that a screen exists in the current deployment.

## Capture Checklist

Use a safe local or staging environment, or an approved hosted demo account.

1. Record deployment URL, commit SHA, date, and viewport.
2. Use synthetic or consented assessment data.
3. Capture the route and state that prove the intended behavior.
4. Redact emails, student identifiers, private paper content, API URLs containing secrets, and signed URLs.
5. Never include passwords, session cookies, CSRF tokens, OAuth tokens, or API keys in pixels, alt text, filenames, or commit messages.
6. Caption whether the image is live, seeded, cached, or illustrative.
7. Recheck the image after export and before commit.

## Suggested Frames

| Frame | Route | What it should prove |
| --- | --- | --- |
| 01 | `/login` | Sign-in surface, without filled credentials |
| 02 | `/exams/new` | Question and rubric authoring |
| 03 | `/exams/:id` | Paper intake and marking plan |
| 04 | `/submissions/:id` | Original page, transcription, evidence, confidence |
| 05 | `/submissions/:id` | Review suggestion before teacher decision |
| 06 | `/submissions/:id` | Override/history distinction |
| 07 | `/students/:id` | Evidence-backed student profile |
| 08 | `/classes/:id` | Class concepts and aggregate statistics |
| 09 | `/assistant` | Grounded teacher question and answer |
