# Teacher and student workflows

This guide describes what the user does, what PRISM does, and what should be
visible at each step.

## 1. Teacher sign-in

1. Open `/login`.
2. Enter a configured teacher email and password.
3. The API creates a signed `prism_session` cookie.
4. The frontend refreshes `/api/auth/me` and redirects teachers to `/`.

If authentication fails, the UI shows a generic error. Do not expose whether an
email exists. A first-use temporary account may be redirected to password
change before other actions.

## 2. Set up a class

1. Open `/classes`.
2. Create a named class or open an existing class.
3. Add students individually or import a roster.
4. Confirm identifiers and archive stale records rather than reusing a student
   identity.

The class is an ownership boundary. Teachers can see only their own classes and
students through the authenticated API.

## 3. Create an exam and rubric

1. Open `/exams/new`.
2. Enter title, subject, date, and class.
3. Add question number and prompt.
4. Add one or more criteria with maximum marks, description, and concept.
5. Optionally add a teacher answer key.
6. Save and review the resulting exam summary.

The rubric is the scoring authority. A teacher answer key is supporting context,
not a requirement for exact phrase matching.

## 4. Import a draft when useful

The exam page can import a draft exam PDF or answer-key PDF. The importer
returns warnings for missing, ambiguous, or unmatched question identifiers.
Review the draft and save only what is correct. A marking-scheme import must
not silently become a new rubric.

## 5. Upload a paper

1. Open an exam.
2. Choose a roster student or enter a temporary student name.
3. Select page images or a PDF.
4. Inspect the local preview and submit.
5. Watch the status panel for `uploaded`, `preprocessing`, `transcribing`,
   `structured`, and `grading`.

The upload retains the original. A processed JPEG is a separate convenience
representation. Unsupported types, invalid signatures, oversized files, and
too many pages are rejected before inference.

## 6. Inspect an evaluated paper

Open `/submissions/:id` after the paper reaches `completed` or
`review_required`. The review surface should make these relationships obvious:

```text
original page -> transcription -> question -> criterion -> mark -> evidence
```

For each criterion inspect:

- current mark and maximum;
- the criterion description;
- reason for the suggestion;
- exact transcription quote;
- source page or approximate region;
- confidence and review signal;
- whether a teacher decision already exists.

The original page is the source of truth if the transcription and image appear
to disagree.

## 7. Challenge a criterion

1. Select the criterion's review action.
2. Write a specific teacher comment, such as “The diagram labels the missing
   process on page 2.”
3. PRISM invokes the review operation for that criterion only.
4. Inspect the suggested marks, reason, and evidence.
5. Accept or reject the suggestion.
6. If needed, apply an explicit teacher override with a mark and reason.

The application must never change a mark just because a review response
arrived. The history endpoint lets a reviewer distinguish AI marks, review
suggestions, and teacher decisions.

## 8. Read the student profile

Open `/students/:id` after evaluations have been saved. Use the profile to see
evidence-backed concept performance, score trend, rubric patterns, and recent
assessment references. Use educational language: mastered, developing, weak,
or needs another check. Avoid intelligence or personality claims.

## 9. Read class analytics

Open `/classes/:id` or an exam's insights page. Analytics are calculated from
criterion rows and can include average score, concept mastery, failure rate,
and review rate. Treat high review rate as a workflow signal, not proof that a
teacher or model is wrong.

## 10. Ask the assistant

Open `/assistant`. Select relevant mentions when available, then ask a bounded
question:

- “Which concept should I revise tomorrow?”
- “Why did Arun lose marks in Q3?”

The API resolves the mentions and supplies only relevant records. The answer
should cite the evidence or statistic it used and avoid unsupported claims.

## 11. Release student results

Teacher-facing evaluation can remain in review. When ready, use the release
control. Student routes show only released content and only the authenticated
student's records. A release is a visibility decision, not a replacement for
teacher review.
