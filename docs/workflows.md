# Workflows

Detailed product instructions live in [Teacher guide](guides/teacher-guide.md) and [Student guide](guides/student-guide.md). This page keeps the end-to-end flow visible.

## Teacher Flow

1. Sign in at `/login`.
2. Create a class and roster, or create an unlinked exam.
3. Create an exam with questions and criterion-level rubric marks.
4. Upload one PDF or up to ten JPEG/PNG pages, or preview a Google Drive import.
5. Watch processing move through `uploaded`, `preprocessing`, `transcribing`, and `grading`.
6. Open the evidence workbench when the paper is `completed` or `review_required`; a `failed` paper needs retry or operational investigation first.
7. Compare original page, transcription, rubric criterion, reasoning, evidence, and confidence.
8. Challenge a criterion if necessary; the returned AI proposal is pending and does not alter the current mark.
9. Accept/reject the proposal or apply a bounded direct teacher override.
10. Release the result only after teacher review.
11. Inspect student, class, and exam analytics. Question, criterion, and concept rows appear within the relevant analytics views.
12. Ask the assistant a scoped question using selected records or concepts.

## Student Flow

1. Sign in with a teacher-provisioned account.
2. Change the temporary password if required.
3. Open `/student`.
4. View only released submissions belonging to the authenticated student.
5. Review criterion marks, reasons, review signals, and the deterministic learning profile.

## Processing And Release Rules

- `review_recommended` is a signal for teacher attention and does not block completion.
- `review_required` indicates unresolved blocking evidence or mapping and needs teacher action.
- Release is independent of processing status and is explicitly reversible.
- A student cannot see teacher-only original paper media through the student portal.

## Authority Rules

- The original page image is ground evidence when it conflicts with transcription.
- The backend validates `0 <= awarded_marks <= max_marks`.
- Teacher marks override AI marks in effective totals.
- A teacher must accept a review suggestion before it changes the effective mark.
- Student profile language must remain educational and evidence-based.
