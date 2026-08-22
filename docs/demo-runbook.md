# Demo Runbook

This runbook presents the complete PRISM story while keeping a cached paper available if live AI processing fails. It does not assume that a new checkout contains five synthetic submissions; seed or prepare the demo dataset explicitly.

## Before The Demo

1. Start the API and frontend, or open the hosted deployment.
2. Check `/api/health` and `/api/health/ready`.
3. Sign in with an approved teacher account.
4. Confirm an exam has questions and a complete rubric.
5. Confirm at least one completed paper, one review-required/recommended paper where available, a student profile, and class/exam analytics.
6. Open the completed paper and verify original page, normalized preview, transcription, evidence, and criterion reasoning.
7. Ask one assistant question using a selected class, student, exam, or paper.
8. Keep a cached completed submission or database snapshot ready.

## Five-Minute Story

### 0:00: The problem

“A paper score tells a teacher what happened numerically, but not what the student understood or why a mark was lost.”

### 0:30: Create the assessment

Open an exam and show that questions are decomposed into criteria and concepts before paper processing.

### 1:00: Bring in paper evidence

Open the upload flow and show the page preview. Explain that PRISM preserves the original and creates a separate normalized representation.

### 1:30: Show processing

Show the status panel. Perception, question mapping, and criterion grading are separate operations. Low confidence or uncertainty creates a review signal.

### 2:15: Inspect a decision

Open a paper and compare original page, transcription, criterion, evidence quote, source page, and confidence. Say: “The model suggests a mark. The teacher still owns the decision.”

### 3:00: Challenge it

Submit a criterion-specific challenge, inspect the unapplied AI suggestion, then accept or reject it. If required, apply a direct teacher override and show history.

### 3:45: Turn marks into learning

Open student profile and class/exam analytics. Explain that percentages and mastery values come from backend calculations.

### 4:30: Ask what to teach next

Ask “Which concept should I revise tomorrow?” using a selected class or concept. Explain that the backend resolves relevant statistics rather than sending the entire database.

### 4:50: Close the loop

“PRISM connects paper evidence to explainable grading, teacher control, and the next teaching action.”

## Fallback

If live inference fails:

1. State that the live request failed.
2. Open the cached completed submission.
3. Continue with evidence, review, override, profile, analytics, and assistant.
4. Do not present cached output as the result of the failed request.

## Visual Evidence

Use the real captures in [the screenshot guide](screenshots.md) and the hosted screenshots under `docs/assets/screenshots/`. Redact account emails, student identifiers, private paper content, URLs containing secrets, cookies, and tokens.
