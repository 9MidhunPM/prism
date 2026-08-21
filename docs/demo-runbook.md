# Demo runbook

This runbook is designed for a short hackathon presentation. The presenter
should be able to finish the story even if a live Luna request fails.

## 1. Before the audience arrives

1. Start the API and frontend.
2. Check `/api/health` and `/api/health/ready`.
3. Sign in with a configured local teacher account.
4. Confirm one exam has a complete rubric.
5. Confirm five synthetic papers exist, including one `review_required` paper.
6. Open one completed paper and verify that the original/preview image and
   criterion evidence load.
7. Confirm a student profile and class analytics page have data.
8. Ask one assistant question and verify that the answer is grounded in the
   expected class statistics.
9. Keep a cached paper or seeded database snapshot ready.

## 2. Five-minute story

### 0:00 — The problem

“A paper score tells a teacher what happened numerically, but not what the
student understood or why a mark was lost.”

### 0:30 — Create the assessment

Open the exam and show the rubric. Point out that each question is decomposed
into criteria and concepts before any student paper is uploaded.

### 1:00 — Bring in paper evidence

Open the paper intake flow. Select a JPEG, PNG, or PDF and show the page preview.
Explain that PRISM retains the original and creates a separate processed
preview.

### 1:30 — Show the pipeline

Show the processing state moving through preprocessing, transcription,
structured mapping, and grading. Emphasize that perception and grading are
separate operations and that a low-confidence result becomes a review signal.

### 2:15 — Inspect a mark

Open a paper with a partial mark. Compare the original page, transcription,
criterion, exact evidence quote, source page, and confidence. Say explicitly:

> “The model suggests a mark. The teacher still owns the decision.”

### 3:00 — Challenge it

Ask a criterion-specific review with a concrete teacher comment. Show the AI
suggestion, then accept or reject it. If the criterion still needs a change,
apply an explicit override with a reason and open history to show both values.

### 3:45 — Turn marks into learning

Open the student profile and class analytics. Point to a concept that appears
across criteria and explain that the percentage and mastery values came from
backend calculations.

### 4:30 — Ask what to teach next

Open the assistant and ask, “Which concept should I revise tomorrow?” Show that
the request is grounded in selected class statistics rather than the entire
database.

### 4:50 — Close the loop

“PRISM connects paper evidence to explainable grading, teacher control, and the
next teaching action.”

## 3. Failure fallback

If live inference fails:

1. Show the captured upload and the processing status.
2. Open the cached completed submission.
3. Continue with evidence, review, override, profile, analytics, and assistant.
4. State that the demo is continuing from a previously processed paper; do not
   pretend the failed request completed.

## 4. Screenshot checklist

Capture only after the current source and environment are known. Suggested
frames are listed in [the screenshot guide](screenshots.md): sign-in, rubric,
paper intake, processing, evidence review, override history, profile, and class
analytics. Crop out account emails, student identifiers, API URLs, and browser
session details before publishing.
