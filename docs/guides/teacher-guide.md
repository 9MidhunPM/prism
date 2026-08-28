# Teacher Guide

This guide follows the current teacher workflow from roster setup through released results. Sign in at the deployment's `/login` route with a teacher account provisioned by the operator.

![Teacher workspace](../assets/screenshots/dashboard.png)

## 1. Prepare A Class

Open **Classes** and create a class with a name and optional academic year or section. Inside the class, add students individually, add an existing student to the class, or paste roster rows in this format:

```csv
Ananya Rao,STU-001
Dev Menon,STU-002
Farah Ali,STU-003
```

The importer accepts up to 200 rows. It performs a simple comma split, so names and identifiers must not contain commas and the input must not include a header row.

### Student Access

Each student record can exist without a login. To enable portal access:

1. Open the student in the class roster.
2. Set an email address and a temporary password of at least 12 characters.
3. Give the credentials to the student through an approved private channel.
4. The student must change the temporary password before accessing results.

Resetting access creates a new temporary password requirement. Disabling an account revokes its active sessions.

## 2. Create An Exam

Open **Exams**, select **Create exam**, then choose a class if the exam belongs to a roster. Add each question and its rubric criteria. Every criterion needs:

- a title
- a description of what earns the mark
- maximum marks
- a concept label used by analytics

PRISM calculates question and exam maxima from criterion marks. The saved rubric is the grading source of truth and is read-only in the current frontend.

### Import A Question Paper

Instead of transcribing an exam manually, upload one JPEG, PNG, or PDF under **Import question paper**. The AI creates an editable draft. Review every question, criterion, mark, and extraction warning before creating the exam. Required clarification checkboxes must be acknowledged.

### Import An Answer Key

Upload a JPEG, PNG, or PDF answer key after question numbers exist in the draft. The extracted answers are editable and become reference answers supplied during criterion grading. They do not replace the rubric.

## 3. Add Student Papers

Open an exam to see its upload panel and immutable marking plan.

![Exam upload and marking plan](../assets/screenshots/exam-detail.png)

### Direct Upload

Supported input:

- one PDF, or
- up to 10 JPEG/PNG pages
- up to 20 MB total by default

For images, place pages in reading order before uploading. The application preserves originals and creates conservative normalized previews. If the exam belongs to a class, select a roster student. For an unlinked exam, type the student's name.

Select **Upload and begin assessment**. The page polls processing until the submission reaches a terminal state and then links to evidence review.

### Google Drive

Choose either a main folder containing student folders or one student folder directly. PRISM previews matches before downloading files or creating submissions. See [Google Drive import](google-drive-import.md) for setup and folder rules.

## 4. Monitor Processing

The global navigation polls for active and failed jobs. The upload screen shows the current submission stage. Typical stages are:

```text
uploaded -> preprocessing -> transcribing -> grading -> completed
                                                   -> review_required
```

Failed processing can be retried from the paper flow when the backend status allows it. Processing is tied to the API process, so an operator may need to recover interrupted work after a deployment restart.

## 5. Review Evidence

Open a submitted paper from the exam, paper list, dashboard review queue, or student profile.

![Evidence review workbench](../assets/screenshots/review-workbench.png)

The workbench keeps two responsibilities visible:

- **Original paper:** navigate retained page images and select quoted evidence.
- **Question review:** inspect criterion marks, effective total, reasoning, confidence, transcription, and review state.

Use **Previous**, **Next**, or the Left and Right arrow keys to move between questions. Select evidence quotes to move to their page.

### Review Signals

| Signal | Meaning | Teacher action |
| --- | --- | --- |
| No flag | The criterion has no unresolved review signal | Verify as needed |
| Review recommended | Confidence or transcription uncertainty crossed the configured threshold | Inspect evidence; no blocking action is required |
| Review required | A blocking grading or mapping issue remains | Resolve before treating the paper as final |
| Teacher reviewed | A teacher override or review resolution exists | Use the effective teacher-controlled mark |

Model confidence is a review signal, not a calibrated probability.

### Challenge An AI Decision

1. Enter a concise teacher comment explaining what should be reconsidered.
2. Submit the challenge.
3. PRISM creates a new AI suggestion without changing the current mark.
4. Compare the current and proposed marks and reasons.
5. Accept the proposal to create a teacher override, or reject it to retain the current mark.

Never assume a re-evaluation was applied automatically. The teacher decision is the final step.

### Direct Override

Enter a mark within `0` and the criterion maximum plus an optional reason. A direct override becomes the effective mark and is retained in evaluation history.

### Complete Review Without A Change

Use the complete-review action when the existing mark is correct but a required review signal needs explicit teacher resolution.

## 6. Release Results

Use **Release results** from a completed or review-required submission. Release is explicit and reversible. Withdrawing a result removes it from the student portal without deleting teacher records.

A student sees only released submissions belonging to their account. The student portal does not expose original paper images or provide a challenge flow.

## 7. Use Analytics

Exam insights contain deterministic submission counts, average raw score, average percentage, review rate, and performance grouped by concept, question, and criterion.

![Exam analytics](../assets/screenshots/exam-insights.png)

Class pages summarize roster and class concept performance. Student profiles show strengths, developing concepts, and source-paper links. Interpret analytics as evidence from available assessment records, not as a judgment about intelligence, personality, motivation, honesty, or mental health.

## 8. Ask PRISM Assistant

Open **PRISM Assistant** and type `@` to find a student, class, exam, or paper. Select relevant records, then ask one scoped question such as:

```text
Which concepts need revision before the next assessment?
```

The backend resolves selected records and computes relevant concept statistics before asking the language model for grounded prose. The current assistant does not retain chat history.

## Destructive Actions

- Archiving hides an active class, student, exam, or submission where supported.
- Deleting a student, exam, or paper performs a deep delete of dependent assessment data.
- An exam cannot be deleted while one of its papers is actively processing.
- Backups may retain deleted records according to the operator's retention policy.

Confirm identifiers and scope before deleting educational records.
