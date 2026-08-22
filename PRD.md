# PRISM product requirements

**Status:** Hackathon MVP, documentation refresh
**Product:** PRISM — explainable assessment intelligence for handwritten papers
**Primary user:** Teacher or lecturer
**Runtime model:** `gpt-5.6-luna` only

## 1. Why PRISM exists

Teachers still receive answers as photographs, scans, or physical paper. The
work is not only reading handwriting. It is reconstructing what the student
wrote, deciding which rubric criteria are satisfied, assigning partial credit,
recording evidence, answering challenges, and then finding patterns across a
class.

A final score hides most of that evidence. PRISM makes the evidence inspectable
while preserving teacher authority:

```text
physical paper
    -> visible answer evidence
    -> rubric-aligned suggestions
    -> teacher decision
    -> learning signal
```

## 2. Product promise

For every meaningful mark, a teacher should be able to ask:

1. What did the student actually write?
2. Which criterion was applied?
3. Which page or answer supports the suggestion?
4. How certain is the suggestion?
5. What can I change, and is the change recorded?

The product is **AI-assisted evaluation**, not autonomous grading.

## 3. Goals and non-goals

### Goals

- Create an exam with questions, marks, concepts, and rubric criteria.
- Upload a JPEG, PNG, or PDF paper while retaining the original.
- Normalize pages conservatively and produce a preview without destroying the
  source image.
- Transcribe handwriting, map answers to questions, and evaluate rubric
  criteria through separate typed AI operations.
- Show evidence, confidence, processing status, and review recommendations.
- Let a teacher request a criterion-specific review and accept, reject, or
  override it explicitly.
- Calculate totals and class/student analytics deterministically.
- Ground teacher assistant answers in selected assessment data.
- Keep the demo usable if a paid inference call fails.

### Non-goals for the hackathon

- Fully autonomous or legally binding grading.
- Perfect handwriting recognition or pixel-perfect bounding boxes.
- Student social graphs, personality scoring, or predictive discipline.
- A general-purpose LMS, attendance system, or content authoring suite.
- Redis, queues, vector databases, agent frameworks, or microservices without a
  demonstrated requirement.

## 4. Users and permissions

### Teacher

The teacher can create exams, classes, rosters, submissions, reviews,
overrides, analytics, and grounded assistant questions. Teacher data is scoped
to the authenticated teacher.

### Student

A student can view only released results and their own profile. A student
cannot edit a teacher rubric, change marks, or see another student's paper.

### Demo operator

The presenter uses a configured local account or seeded demo account. Demo
credentials are configuration, never source code. A cached completed paper is
the fallback when live inference is unavailable.

## 5. Functional requirements

### 5.1 Authentication

- Login accepts an email and password over the API.
- Sessions are signed and stored in an HTTP-only cookie.
- Unsafe requests are protected by origin and CSRF checks.
- Login is rate limited.
- A temporary password may require a password change before normal work.
- The API never returns a password, API key, or session secret.

### 5.2 Exam authoring

An exam contains a title, subject, optional date/class, questions, and rubric
criteria. A question contains a number, prompt, optional teacher answer key,
maximum marks, and one or more criteria. Each criterion contains a positive
mark allocation, description, concept label, and stable code.

The teacher may import an exam draft or answer key from a PDF, but imported
content is a draft. The teacher reviews it before saving or using it as the
scoring authority.

### 5.3 Classes and rosters

Teachers can create, rename, archive, and delete classes; add students one at a
time; import a roster; archive students; and provision student access. A paper
can be associated with a roster student or remain temporarily unassigned.

### 5.4 Paper intake

Accepted types are JPEG, PNG, and PDF. Upload validation checks both declared
MIME type and file signature. The MVP limits file size and page count through
configuration. Original bytes remain linked to the submission page.

For PDF input, each page is rendered to an image for processing. Orientation,
dimension, and image quality may be normalized conservatively. Preprocessing
never silently replaces the retained original.

### 5.5 Perception and mapping

The perception operation reads one or more pages and returns typed data for:

- page-level transcription
- question identifiers
- answer regions
- formulas, tables, and visible diagrams
- uncertainty segments
- quality status and reason

The prompt must preserve spelling, grammar, incorrect statements, and incorrect
formulas. It must not answer the exam or improve the student's wording. Use
`[ILLEGIBLE]` for unreadable content and a structured uncertainty value when
two readings remain plausible.

Question mapping is separate from grading. If the system cannot map visible
writing responsibly, the submission enters review rather than receiving a
quietly invented mapping.

### 5.6 Grading

The grading operation receives the question, rubric criterion, transcription,
and relevant original/processed page evidence. It returns awarded marks,
reasoning, exact evidence quotes, page references, confidence, and a blocking
reason when a responsible mark cannot be finalized.

The model does not calculate totals. Backend code validates every criterion:

```text
0 <= awarded_marks <= max_marks
```

Then backend code calculates question totals, exam totals, percentages, review
rates, and aggregate statistics.

### 5.7 Review and override

Confidence below the configurable review signal, currently `0.75`, recommends
teacher attention. It is not a calibrated probability and does not reject a
mark automatically.

The review sequence is always:

```text
current evaluation
    -> AI review suggestion
    -> teacher accepts or rejects
    -> optional explicit teacher override
    -> immutable history remains available
```

The teacher may override a criterion with a new mark and reason. The original
AI mark and accepted teacher mark remain distinguishable.

### 5.8 Learning profiles and analytics

The application computes concept performance from saved criterion evaluations.
It can show mastered, developing, and weak concepts, score trends, rubric
performance, recurring misconceptions, and evidence references.

Class analytics include average performance, concept mastery, criterion failure
rate, review rate, and review concentration. Luna may turn retrieved statistics
into a concise instructional observation, but it may not invent a statistic or
infer a student's character.

### 5.9 Teacher assistant

Before a question reaches Luna, the backend resolves relevant entities. A
question about a student and Q3 receives that student's submission, Q3 rubric,
evaluation, and evidence. A question about tomorrow's revision receives class
concept statistics. The entire database is never dumped into a prompt.

## 6. AI operation contract

Each operation owns its input schema, prompt, output schema, and version:

| Operation | Version | Responsibility |
| --- | --- | --- |
| Perception | `perception_v2` | Read pages and preserve uncertainty |
| Grading | `grading_v3` | Score one rubric criterion with evidence |
| Review | `review_v3` | Re-evaluate one disputed criterion |
| Student profile | `student_profile_v1` | Summarize retrieved learning signals |
| Class analysis | `class_analysis_v1` | Explain computed class statistics |
| Teacher chat | `teacher_chat_v1` | Answer a grounded teacher question |
| Exam import | `exam_import_v1` | Suggest draft questions and criteria |
| Answer-key import | `answer_key_import_v1` | Extract teacher reference answers |

Successful raw artifacts should retain the operation, model, prompt version,
input identity, duration, and token usage where available. Malformed output is
rejected safely and never treated as a valid grade.

## 7. Processing states

```text
uploaded
  -> preprocessing
  -> transcribing
  -> structured
  -> grading
  -> completed
        or review_required
        or failed
```

The API exposes the current stage and attempt information. A bounded retry can
be requested for a failed job. The frontend uses the same state to show the
teacher what is happening instead of implying that a result is ready.

## 8. Acceptance criteria

A teacher can complete this path in a fresh local environment:

```text
create class
  -> create exam and rubric
  -> upload paper
  -> see processing state
  -> inspect transcription and evidence
  -> inspect criterion mark and total
  -> request a review
  -> accept/reject or override
  -> inspect student profile
  -> inspect class analytics
  -> ask a grounded assistant question
```

At minimum, automated verification covers score bounds, deterministic totals,
override persistence, malformed AI schema rejection, and unsupported upload
rejection.
