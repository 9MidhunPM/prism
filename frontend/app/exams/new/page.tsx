"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AppShell } from "@/components/app-shell";

const API = "/api";

type Criterion = {
  title: string;
  description: string;
  max_marks: string;
  concept: string;
};
type Question = {
  number: string;
  text: string;
  visible_max_marks?: string;
  criteria: Criterion[];
};

const blankCriterion = (): Criterion => ({
  title: "",
  description: "",
  max_marks: "1",
  concept: "",
});
const blankQuestion = (number: number): Question => ({
  number: `Q${number}`,
  text: "",
  criteria: [blankCriterion()],
});

export default function NewExamPage() {
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [date, setDate] = useState("");
  const [questions, setQuestions] = useState<Question[]>([blankQuestion(1)]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [createdId, setCreatedId] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [importWarnings, setImportWarnings] = useState<string[]>([]);
  const [clarifications, setClarifications] = useState<
    {
      type: string;
      question_number: string | null;
      message: string;
      required: boolean;
    }[]
  >([]);
  const [classId, setClassId] = useState("");
  const [classes, setClasses] = useState<{ id: string; name: string }[]>([]);
  const [confirmedClarifications, setConfirmedClarifications] = useState<
    string[]
  >([]);

  useEffect(() => {
    api
      .get<{ id: string; name: string }[]>("/api/classes")
      .then(setClasses)
      .catch(() => undefined);
  }, []);

  const updateQuestion = (
    index: number,
    field: "number" | "text" | "visible_max_marks",
    value: string,
  ) =>
    setQuestions((items) =>
      items.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    );
  const updateCriterion = (
    questionIndex: number,
    criterionIndex: number,
    field: keyof Criterion,
    value: string,
  ) =>
    setQuestions((items) =>
      items.map((question, itemIndex) =>
        itemIndex !== questionIndex
          ? question
          : {
              ...question,
              criteria: question.criteria.map((criterion, index) =>
                index === criterionIndex
                  ? { ...criterion, [field]: value }
                  : criterion,
              ),
            },
      ),
    );
  const questionTotal = (question: Question) =>
    question.criteria.reduce(
      (total, criterion) => total + (Number(criterion.max_marks) || 0),
      0,
    );
  const total = questions.reduce(
    (sum, question) => sum + questionTotal(question),
    0,
  );
  const removeQuestion = (questionIndex: number) =>
    setQuestions((items) =>
      items.length === 1
        ? items
        : items.filter((_, index) => index !== questionIndex),
    );
  const removeCriterion = (questionIndex: number, criterionIndex: number) =>
    setQuestions((items) =>
      items.map((question, index) =>
        index !== questionIndex || question.criteria.length === 1
          ? question
          : {
              ...question,
              criteria: question.criteria.filter(
                (_, criterion) => criterion !== criterionIndex,
              ),
            },
      ),
    );

  async function importQuestionPaper(file: File | undefined) {
    if (!file) return;
    setImportError("");
    setImportWarnings([]);
    setClarifications([]);
    if (!["image/jpeg", "image/png", "application/pdf"].includes(file.type)) {
      setImportError("Choose a JPEG, PNG, or PDF question paper.");
      return;
    }
    setImporting(true);
    const form = new FormData();
    form.set("file", file);
    try {
      const response = await fetch(`${API}/exam-drafts/import`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      const draft = await response.json().catch(() => null);
      if (!response.ok)
        throw new Error(
          draft?.detail ?? "The question paper could not be imported.",
        );
      setTitle(draft.title ?? "");
      setSubject(draft.subject ?? "");
      setQuestions(
        draft.questions.map((question: any) => ({
          number: question.number,
          text: question.text,
          visible_max_marks:
            question.max_marks == null ? "" : String(question.max_marks),
          criteria: question.criteria.map((criterion: any) => ({
            ...criterion,
            max_marks: String(criterion.max_marks),
          })),
        })),
      );
      setImportWarnings(draft.warnings ?? []);
      setClarifications(draft.clarifications ?? []);
      setConfirmedClarifications([]);
    } catch (reason) {
      setImportError(
        reason instanceof Error
          ? reason.message
          : "The question paper could not be imported.",
      );
    } finally {
      setImporting(false);
    }
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (
      !title.trim() ||
      !subject.trim() ||
      questions.some(
        (question) =>
          !question.text.trim() ||
          question.criteria.some(
            (criterion) =>
              !criterion.title.trim() ||
              !criterion.description.trim() ||
              !criterion.concept.trim() ||
              Number(criterion.max_marks) <= 0,
          ),
      )
    ) {
      setError(
        "Complete the exam details, every question, and every rubric criterion before saving.",
      );
      return;
    }
    if (
      clarifications.some(
        (item, index) =>
          item.required &&
          !confirmedClarifications.includes(
            `${item.type}-${item.question_number ?? index}`,
          ),
      )
    ) {
      setError(
        "Resolve or confirm every import clarification before saving this exam.",
      );
      return;
    }
    setSaving(true);
    try {
      const response = await fetch(`${API}/exams`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          subject,
          date: date || null,
          class_id: classId || null,
          questions: questions.map((question) => ({
            ...question,
            criteria: question.criteria.map((criterion) => ({
              ...criterion,
              max_marks: Number(criterion.max_marks),
            })),
          })),
        }),
      });
      if (!response.ok) throw new Error("The exam could not be saved.");
      const exam = await response.json();
      setCreatedId(exam.id);
    } catch {
      setError(
        "The exam could not be saved. Check that the PRISM API is running and try again.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (createdId)
    return (
      <main className="min-h-screen bg-[#f5f1e9] px-5 py-12 text-[#172126] sm:px-8">
        <div className="mx-auto max-w-xl rounded-lg border border-[#173f4c]/15 bg-[#fcfaf5] p-8">
          <p className="text-sm font-medium text-[#52705b]">Exam saved</p>
          <h1 className="mt-2 font-serif text-3xl font-semibold">
            Your rubric is ready.
          </h1>
          <p className="mt-3 text-[#566164]">
            PRISM will use these criteria as the source of truth when student
            papers are uploaded.
          </p>
          <Link
            className="mt-6 inline-block rounded-md bg-[#173f4c] px-4 py-2 text-sm font-medium text-white"
            href={`/exams/${createdId}`}
          >
            View exam
          </Link>
        </div>
      </main>
    );

  return (
    <AppShell>
      <form onSubmit={submit} className="mx-auto max-w-5xl">
        <div className="mb-8 flex flex-col justify-between gap-3 border-b border-[var(--line)] pb-7 sm:flex-row sm:items-end">
          <div>
            <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
              Create an assessment
            </h1>
            <p className="mt-2 text-sm text-[var(--ink-muted)]">
              Set the source-of-truth rubric before papers reach the review
              queue.
            </p>
          </div>
          <strong className="status-pill bg-[var(--brand-soft)] text-[var(--brand-strong)]">
            {total} marks
          </strong>
        </div>
        {error && (
          <p className="mb-6 rounded-lg bg-[var(--review-soft)] p-4 text-sm text-[var(--review)]">
            {error}
          </p>
        )}
        <section className="mb-6 rounded-xl bg-[var(--brand-soft)] p-5">
          <h2 className="font-serif text-2xl font-semibold text-[var(--brand-strong)]">
            Start from a question paper
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            Upload a scanned or photographed paper. PRISM extracts a draft of
            visible questions and suggests rubric criteria for you to review
            before saving.
          </p>
          <label className="mt-4 flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-dashed border-[var(--brand)] bg-[var(--surface)] px-4 py-4 text-sm transition-colors hover:bg-[var(--surface-muted)]">
            <span>
              <strong className="block text-[var(--brand-strong)]">
                {importing
                  ? "Reading question paper…"
                  : "Choose a JPEG, PNG, or PDF"}
              </strong>
              <span className="text-[var(--ink-muted)]">
                The existing form will be replaced by an editable draft.
              </span>
            </span>
            <span className="button-primary">Browse</span>
            <input
              className="sr-only"
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              capture="environment"
              disabled={importing}
              onChange={(event) => importQuestionPaper(event.target.files?.[0])}
            />
          </label>
          {importError && (
            <p role="alert" className="mt-3 text-sm text-[#9b3e23]">
              {importError}
            </p>
          )}
          {importWarnings.length > 0 && (
            <div className="mt-4 rounded-md bg-[#fff7e7] p-4 text-sm text-[#7a4b12]">
              <strong>Review before saving</strong>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {importWarnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
        <section className="surface mb-6 grid gap-4 p-5 sm:grid-cols-3">
          <Field label="Exam title">
            <input
              name="title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="input"
              placeholder="Machine Learning Foundations"
            />
          </Field>
          <Field label="Subject">
            <input
              name="subject"
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              className="input"
              placeholder="Computer Science"
            />
          </Field>
          <Field label="Assessment date">
            <input
              name="date"
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              className="input"
            />
          </Field>
          <Field label="Class">
            <select
              value={classId}
              onChange={(event) => setClassId(event.target.value)}
              className="input"
            >
              <option value="">No class assigned</option>
              {classes.map((cohort) => (
                <option key={cohort.id} value={cohort.id}>
                  {cohort.name}
                </option>
              ))}
            </select>
          </Field>
        </section>
        {clarifications.length > 0 && (
          <section className="surface-lined mb-6 p-5">
            <h2 className="font-serif text-2xl font-semibold">
              Review imported questions
            </h2>
            <p className="mt-2 text-sm text-[var(--ink-muted)]">
              Confirm the question count, marks, and any low-confidence
              extraction before saving.
            </p>
            <div className="mt-4 space-y-3">
              {clarifications.map((item, index) => {
                const key = `${item.type}-${item.question_number ?? index}`;
                const checked = confirmedClarifications.includes(key);
                return (
                  <label
                    key={key}
                    className="flex cursor-pointer items-start gap-3 rounded-lg bg-[var(--surface-muted)] p-3 text-sm"
                  >
                    <input
                      className="mt-0.5"
                      type="checkbox"
                      checked={checked}
                      onChange={(event) =>
                        setConfirmedClarifications((current) =>
                          event.target.checked
                            ? [...current, key]
                            : current.filter((value) => value !== key),
                        )
                      }
                    />
                    <span>
                      <strong>
                        {item.question_number
                          ? `${item.question_number}: `
                          : ""}
                      </strong>
                      {item.message}
                    </span>
                  </label>
                );
              })}
            </div>
          </section>
        )}
        <div className="space-y-5">
          {questions.map((question, questionIndex) => (
            <section key={question.number} className="surface-lined p-5">
              <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
                <div className="grid gap-3 sm:grid-cols-[100px_1fr]">
                  <Field label="Number">
                    <input
                      name={`question-number-${questionIndex}`}
                      value={question.number}
                      onChange={(event) =>
                        updateQuestion(
                          questionIndex,
                          "number",
                          event.target.value,
                        )
                      }
                      className="input"
                    />
                  </Field>
                  <Field label="Question">
                    <input
                      name={`question-text-${questionIndex}`}
                      value={question.text}
                      onChange={(event) =>
                        updateQuestion(
                          questionIndex,
                          "text",
                          event.target.value,
                        )
                      }
                      className="input"
                      placeholder="What should the student explain?"
                    />
                  </Field>
                  <Field label="Paper marks">
                    <input
                      name={`question-visible-marks-${questionIndex}`}
                      type="number"
                      min="0"
                      step="0.5"
                      value={question.visible_max_marks ?? ""}
                      onChange={(event) =>
                        updateQuestion(
                          questionIndex,
                          "visible_max_marks",
                          event.target.value,
                        )
                      }
                      className="input"
                      placeholder="Not shown"
                    />
                  </Field>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-[var(--ink-muted)]">
                    {questionTotal(question)} marks
                  </span>
                  <button
                    type="button"
                    onClick={() => removeQuestion(questionIndex)}
                    disabled={questions.length === 1}
                    className="button-quiet px-2 py-1 text-xs disabled:opacity-40"
                  >
                    Remove
                  </button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[650px] text-left text-sm">
                  <thead className="border-b border-[#172126]/10 text-[#667174]">
                    <tr>
                      <th className="pb-2 font-medium">Criterion</th>
                      <th className="pb-2 font-medium">Description</th>
                      <th className="pb-2 font-medium">Concept</th>
                      <th className="pb-2 text-right font-medium">Marks</th>
                      <th aria-label="Criterion actions" />
                    </tr>
                  </thead>
                  <tbody>
                    {question.criteria.map((criterion, criterionIndex) => (
                      <tr
                        key={criterion.title}
                        className="border-b border-[#172126]/8 last:border-0"
                      >
                        <td className="py-2 pr-2">
                          <input
                            name={`criterion-title-${questionIndex}-${criterionIndex}`}
                            value={criterion.title}
                            onChange={(event) =>
                              updateCriterion(
                                questionIndex,
                                criterionIndex,
                                "title",
                                event.target.value,
                              )
                            }
                            className="input"
                            placeholder="Correct definition"
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <input
                            name={`criterion-description-${questionIndex}-${criterionIndex}`}
                            value={criterion.description}
                            onChange={(event) =>
                              updateCriterion(
                                questionIndex,
                                criterionIndex,
                                "description",
                                event.target.value,
                              )
                            }
                            className="input"
                            placeholder="What evidence earns marks?"
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <input
                            name={`criterion-concept-${questionIndex}-${criterionIndex}`}
                            value={criterion.concept}
                            onChange={(event) =>
                              updateCriterion(
                                questionIndex,
                                criterionIndex,
                                "concept",
                                event.target.value,
                              )
                            }
                            className="input"
                            placeholder="Optimization"
                          />
                        </td>
                        <td className="py-2">
                          <input
                            name={`criterion-marks-${questionIndex}-${criterionIndex}`}
                            type="number"
                            min="0.5"
                            step="0.5"
                            value={criterion.max_marks}
                            onChange={(event) =>
                              updateCriterion(
                                questionIndex,
                                criterionIndex,
                                "max_marks",
                                event.target.value,
                              )
                            }
                            className="input w-20 text-right"
                          />
                        </td>
                        <td className="py-2 pl-2 text-right">
                          <button
                            type="button"
                            onClick={() =>
                              removeCriterion(questionIndex, criterionIndex)
                            }
                            disabled={question.criteria.length === 1}
                            className="button-quiet px-2 py-1 text-xs disabled:opacity-40"
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button
                type="button"
                onClick={() =>
                  setQuestions((items) =>
                    items.map((item, index) =>
                      index === questionIndex
                        ? {
                            ...item,
                            criteria: [...item.criteria, blankCriterion()],
                          }
                        : item,
                    ),
                  )
                }
                className="button-secondary mt-4"
              >
                Add criterion
              </button>
            </section>
          ))}
        </div>
        <div className="mt-6 flex flex-col justify-between gap-4 border-t border-[var(--line)] pt-5 sm:flex-row sm:items-center">
          <button
            type="button"
            onClick={() =>
              setQuestions((items) => [
                ...items,
                blankQuestion(items.length + 1),
              ])
            }
            className="button-secondary self-start"
          >
            Add question
          </button>
          <button type="submit" disabled={saving} className="button-primary">
            {saving ? "Saving exam..." : "Save exam and rubric"}
          </button>
        </div>
      </form>
    </AppShell>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1 text-sm font-medium text-[#566164]">
      <span>{label}</span>
      {children}
    </div>
  );
}
