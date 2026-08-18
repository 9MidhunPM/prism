# PRISM MVP Specification

## Product Name

**PRISM**

### Working Expansion

**Paper Recognition & Intelligent Scoring Matrix**

### Product Positioning

**Explainable Multimodal Assessment Intelligence**

PRISM converts physical handwritten examinations into structured, explainable assessment data.

It does not merely assign marks.

It allows a teacher to:

- digitize handwritten exam papers
- evaluate answers against explicit rubrics
- inspect evidence behind every awarded or deducted mark
- challenge and override AI decisions
- identify student strengths and recurring misconceptions
- analyze misconceptions across an entire class
- ask natural-language questions about assessment results

---

# 1. Hackathon Objective

Build a convincing end-to-end prototype demonstrating:

> Physical exam paper â AI understanding â rubric-based evaluation â evidence â teacher interrogation â learning intelligence.

The hackathon MVP should prioritize:

1. reliability
2. explainability
3. visual impact
4. a strong live demonstration
5. limited technical complexity

The product runtime uses only:

**GPT-5.6 Luna**

for AI inference.

No runtime calls should be made to:

- GPT-5.6 Terra
- GPT-5.6 Sol
- Gemini
- Claude
- Qianfan
- PaddleOCR
- Unlimited-OCR

Codex may use whatever coding model is available to develop the application, but the finished product must use only GPT-5.6 Luna as its AI model.

---

# 2. Core Demo Story

The ideal demo is:

1. Teacher creates an exam.
2. Teacher adds questions and marking rubrics.
3. Teacher uploads photographs or scans of a student's handwritten answer sheet.
4. PRISM reads the handwriting and reconstructs the answers.
5. PRISM evaluates each answer criterion-by-criterion.
6. Teacher sees:
   - score
   - reasoning
   - confidence
   - evidence from the handwritten response
7. Teacher asks:
   - "Why did this student lose two marks?"
8. PRISM explains.
9. Teacher challenges:
   - "Doesn't the diagram satisfy criterion C3?"
10. PRISM re-evaluates that criterion.
11. Teacher accepts or rejects the suggested revision.
12. PRISM updates the student's learning profile.
13. Teacher views class-level misconceptions.
14. Teacher asks:
   - "What should I revise with the class tomorrow?"

This is the complete hackathon narrative.

---

# 3. MVP Features

## 3.1 Exam Creation

Teacher can create an exam with:

- title
- subject
- total marks
- questions
- marks per question
- expected concepts
- rubric criteria

Example:

```text
Question 4

Explain gradient descent and discuss the effect of learning rate.

Maximum marks: 10

Rubric:
C1 - Correct definition                  2 marks
C2 - Explains gradient direction        2 marks
C3 - Describes parameter updates        2 marks
C4 - Explains learning-rate effects     2 marks
C5 - Discusses convergence              2 marks
```

---

# 3.2 Paper Upload

Support:

- JPEG
- JPG
- PNG
- PDF

For MVP:

- maximum approximately 10 pages per submission
- one student per submission
- one exam per submission

PDF pages should be rendered to images before Luna processing.

---

# 3.3 Image Preprocessing

Use deterministic code for:

- EXIF orientation
- image resizing
- page cropping
- optional deskewing
- basic contrast enhancement
- image compression
- PDF page extraction

Do not use Luna for operations normal image-processing code can perform.

Always preserve the original uploaded image.

---

# 3.4 Luna Perception Stage

Each page is sent to GPT-5.6 Luna.

Luna extracts:

- handwritten text
- question identifiers
- answer regions
- formulas
- tables
- visible diagrams
- graphs
- crossed-out content where relevant
- uncertain words
- page structure

Luna must NOT:

- correct grammar
- improve answers
- correct factual errors
- silently replace incorrect formulas
- answer exam questions itself

Unclear content should be represented as:

```text
[ILLEGIBLE]
```

or:

```text
[UNCERTAIN: covid | cold]
```

where appropriate.

---

# 3.5 Structured Exam Representation

Convert each submission into structured data.

Example:

```json
{
  "student_id": "student_001",
  "exam_id": "exam_001",
  "pages": [
    {
      "page_number": 1,
      "answers": [
        {
          "question_id": "Q1",
          "transcription": "...",
          "regions": [],
          "visuals": [],
          "uncertainties": []
        }
      ]
    }
  ]
}
```

---

# 3.6 Rubric-Based Evaluation

Each answer is evaluated independently.

Input:

- exam question
- maximum marks
- rubric criteria
- extracted transcription
- original answer image/crop
- relevant diagrams or formulas

Output:

```json
{
  "question_id": "Q4",
  "criteria": [
    {
      "criterion_id": "C1",
      "criterion": "Correct definition",
      "max_marks": 2,
      "awarded_marks": 2,
      "reason": "The student correctly describes gradient descent as an optimization procedure.",
      "evidence": [
        {
          "page": 2,
          "quote": "gradient descent minimizes the loss...",
          "region_id": "r12"
        }
      ],
      "confidence": 0.96
    }
  ],
  "overall_confidence": 0.91,
  "needs_review": false
}
```

The backend calculates totals.

The model must never be trusted to calculate final arithmetic independently.

---

# 3.7 Confidence-Aware Review

Show confidence for each criterion.

Example:

```text
Definition                     2/2    97%
Gradient direction             2/2    94%
Learning-rate effects          1/2    71% â 
Convergence                    1/2    84%
```

A criterion should be flagged when:

- transcription contains uncertainty
- visual evidence is ambiguous
- confidence is below configured threshold
- rubric interpretation is unclear

Default MVP threshold:

```text
0.75
```

---

# 3.8 Evidence Viewer

This is a critical feature.

For every rubric criterion, teacher should be able to:

- see the original handwritten page
- view extracted text
- view evidence cited by Luna
- see the grading explanation

Ideal UI:

```text
ââââââââââââââââââââââââ¬âââââââââââââââââââââââââââ
â Original Paper       â Evaluation               â
â                      â                          â
â highlighted region   â C3: 1/2                 â
â                      â                          â
â                      â Reason: ...              â
â                      â Evidence: ...            â
ââââââââââââââââââââââââ´âââââââââââââââââââââââââââ
```

Exact pixel-level highlighting is optional for the MVP.

Approximate region highlighting is sufficient.

---

# 3.9 Teacher Challenge / Re-Evaluation

Teacher can ask:

> Why was criterion C4 only awarded one mark?

PRISM answers using:

- original image
- transcription
- rubric
- current grading result

Teacher can then ask:

> Re-evaluate C4. The graph seems to demonstrate convergence.

PRISM re-evaluates ONLY that criterion.

Result:

```text
Previous:
1 / 2

Suggested:
2 / 2

Reason:
The graph provides sufficient visual evidence of oscillation and convergence behavior.

[Accept]
[Reject]
```

No score should change automatically without teacher acceptance.

---

# 3.10 Teacher Override

Teachers can manually modify:

- criterion marks
- final question marks
- comments

Store:

- previous AI mark
- teacher mark
- timestamp
- optional reason

This provides an audit trail.

---

# 3.11 Student Learning Profile

Do NOT create psychological or personality classifications.

Only represent observable educational performance.

Example:

```text
Student Learning Profile

Machine Learning

Naive Bayes              83%
Probability              61%
Regression               92%
Optimization             76%
Evaluation Metrics       54%

Strengths
- Explains algorithms clearly
- Strong formula recall

Repeated misconceptions
- Confuses precision and recall
- Weak conditional probability reasoning

Evidence
- Exam 1 Q4
- Exam 2 Q7
- Exam 3 Q2
```

---

# 3.12 Class Intelligence Dashboard

Aggregate assessment results.

Display:

```text
CLASS CONCEPT MASTERY

Linear Regression           89%
Gradient Descent            77%
Classification              74%
Probability                 48%
Bayesian Reasoning          41%
```

Show:

- weakest concepts
- strongest concepts
- most common mistakes
- questions with lowest scores
- questions with highest review rates

---

# 3.13 Teacher Analytics Chat

Teacher can ask:

- "What concept caused the most lost marks?"
- "Which students struggled with probability?"
- "Why was Q6 difficult?"
- "What misconceptions appeared repeatedly?"
- "Which students understand regression but struggle with classification?"
- "What should I revise tomorrow?"
- "Generate a 15-minute revision plan."

The backend retrieves relevant database records and supplies them to Luna.

Do NOT build vector search for the MVP unless absolutely necessary.

---

# 4. MVP Architecture

```text
                     TEACHER
                        â
                        â¼
                  Next.js Frontend
                        â
                        â¼
                   Backend API
                        â
          âââââââââââââââ´ââââââââââââââ
          â                           â
          â¼                           â¼
     File Storage                 Database
    exam images                 structured data
          â
          â¼
 Image preprocessing
          â
          â¼
     GPT-5.6 Luna
   PERCEPTION CALL
          â
          â¼
 Structured answers
          â
          â¼
     GPT-5.6 Luna
    GRADING CALL
          â
          â¼
 Rubric evaluation
 evidence + confidence
          â
          â¼
       Database
          â
    âââââââ¼âââââââââââââ
    â¼     â¼            â¼
 Teacher Student       Class
 Review  Profile       Analytics
    â
    â¼
 GPT-5.6 Luna
 Teacher Q&A
```

---

# 5. Recommended Technology Stack

## Frontend

**Next.js**

Recommended:

- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts

---

## Backend

Either:

**FastAPI**

or:

**Next.js server routes**

For hackathon speed, a single Next.js application is acceptable.

If the team is comfortable with Python AI/image tooling:

**FastAPI is preferred.**

---

## Database

Hackathon:

**SQLite**

or:

**PostgreSQL**

If deployment infrastructure is already ready:

PostgreSQL.

Otherwise SQLite is completely acceptable.

---

## File Storage

Hackathon:

local filesystem.

Production:

S3-compatible object storage.

---

## AI

Only:

```text
gpt-5.6-luna
```

through the OpenAI Responses API.

---

# 6. Luna Call Separation

Never use one giant model call.

Use independent tasks.

## Call A

Document perception.

```text
image
â structured transcription
```

## Call B

Answer grading.

```text
question
+
rubric
+
transcription
+
original visual
â criterion evaluation
```

## Call C

Teacher interrogation.

```text
assessment context
+
teacher question
â answer
```

## Call D

Learning profile generation.

```text
historical assessment records
â educational profile
```

## Call E

Class analysis.

```text
aggregated assessment data
â misconceptions + recommendations
```

---

# 7. Deterministic Backend Responsibilities

Never ask Luna to do tasks better handled by code.

Backend calculates:

- totals
- percentages
- averages
- ranking
- criterion aggregation
- confidence thresholds
- validation
- file management
- pagination
- database queries

Example:

```python
total = sum(c.awarded_marks for c in criteria)
```

NOT:

```text
"GPT, please calculate the final score."
```

---

# 8. MVP Pages

## `/`

Landing/demo page.

## `/exams`

Exam list.

## `/exams/new`

Create examination.

## `/exams/[id]`

Exam overview.

## `/exams/[id]/submissions/new`

Upload paper.

## `/submissions/[id]`

Processing + grading results.

## `/submissions/[id]/review`

Evidence-backed teacher review.

## `/students/[id]`

Student learning profile.

## `/classes/[id]`

Class analytics.

## `/assistant`

Teacher assessment chat.

---

# 9. Processing UX

When uploading:

```text
Scanning examination...

â 4 pages detected
â Reading handwriting
â Mapping questions
â Detecting equations
â Evaluating answers
â Building assessment report
```

Avoid exposing technical language such as:

```text
Calling OpenAI request 4...
```

---

# 10. MVP Non-Goals

DO NOT build:

- LMS integration
- automatic student identification from handwriting
- facial recognition
- attendance
- parent portal
- student login
- multi-school tenancy
- payment system
- autonomous final-grade submission
- model fine-tuning
- custom OCR model
- vector database
- microservices
- Kubernetes
- complex permissions
- production authentication architecture

---

# 11. Safety Rules

AI suggestions are advisory.

Teacher remains final authority.

Never infer:

- intelligence
- personality
- motivation
- mental health
- effort
- honesty

Only infer observable educational signals from submitted assessments.

Always retain:

- original paper
- original transcription
- AI grade
- teacher modifications

---

# 12. Hackathon Success Criteria

The MVP succeeds if the live demo can:

1. Upload a handwritten exam.
2. Successfully transcribe it.
3. Identify answers.
4. Grade at least three questions.
5. Show criterion-level evidence.
6. Let a teacher challenge one grade.
7. Re-evaluate that criterion.
8. Accept/reject the change.
9. Generate a student learning profile.
10. Show class-wide misconception analytics.

Anything beyond that is bonus territory.

---

# 13. Absolute Priority

If time becomes limited, implement in this order:

1. Exam creation
2. Paper upload
3. Luna transcription
4. Rubric evaluation
5. Evidence viewer
6. Teacher challenge/re-evaluation
7. Student profile
8. Class analytics
9. UI polish

The first six features form the true MVP.