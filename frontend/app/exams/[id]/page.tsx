"use client";

import Link from "next/link";
import { type DragEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";

const API = "/api";
const IMAGE_TYPES = ["image/jpeg", "image/png"];
const PDF_TYPE = "application/pdf";
const MAX_IMAGE_PAGES = 10;
const MAX_TOTAL_BYTES = 20 * 1024 * 1024;
const STAGES = [
  "uploaded",
  "preprocessing",
  "transcribing",
  "grading",
  "review_required",
  "completed",
];

function stageLabel(stage?: string) {
  return (stage ?? "uploaded").replaceAll("_", " ");
}

function fileSize(size: number) {
  return `${(size / 1024 / 1024).toFixed(size > 10 * 1024 * 1024 ? 0 : 1)} MB`;
}

export default function ExamPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [exam, setExam] = useState<any>(null);
  const [error, setError] = useState("");
  const [studentName, setStudentName] = useState("");
  const [studentId, setStudentId] = useState("");
  const [roster, setRoster] = useState<
    { id: string; name: string; identifier: string }[]
  >([]);
  const [pages, setPages] = useState<File[]>([]);
  const [uploadError, setUploadError] = useState("");
  const [submission, setSubmission] = useState<any>(null);
  const [processing, setProcessing] = useState<any>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [existingSubmissions, setExistingSubmissions] = useState<
    {
      id: string;
      student_name: string;
      total_score: number;
      created_at: string;
    }[]
  >([]);
  const [localPreviewUrl, setLocalPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    params.then(({ id }) => {
      fetch(`${API}/exams/${id}`, { credentials: "include" })
        .then((response) => (response.ok ? response.json() : Promise.reject()))
        .then((nextExam) => {
          setExam(nextExam);
          if (nextExam.class_id) {
            fetch(`${API}/classes/${nextExam.class_id}`, {
              credentials: "include",
            })
              .then((response) => (response.ok ? response.json() : null))
              .then((cohort) => setRoster(cohort?.students ?? []));
          }
        })
        .catch(() =>
          setError(
            "This assessment could not be loaded. Sign in and try again.",
          ),
        );
      fetch(`${API}/submissions?exam_id=${id}`, { credentials: "include" })
        .then((response) => (response.ok ? response.json() : []))
        .then(setExistingSubmissions);
    });
  }, [params]);

  useEffect(() => {
    if (!pages[0]) {
      setLocalPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(pages[0]);
    setLocalPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [pages]);

  useEffect(() => {
    if (
      !submission ||
      ["completed", "review_required", "failed"].includes(submission.status)
    )
      return;
    const timer = window.setInterval(async () => {
      const [submissionResponse, statusResponse] = await Promise.all([
        fetch(`${API}/submissions/${submission.id}`, {
          credentials: "include",
        }),
        fetch(`${API}/submissions/${submission.id}/status`, {
          credentials: "include",
        }),
      ]);
      if (submissionResponse.ok) setSubmission(await submissionResponse.json());
      if (statusResponse.ok) setProcessing(await statusResponse.json());
    }, 1800);
    return () => window.clearInterval(timer);
  }, [submission]);

  function addPages(nextFiles: FileList | File[]) {
    setUploadError("");
    const nextPages = Array.from(nextFiles);
    if (!nextPages.length) return;

    if (
      nextPages.some(
        (page) => !IMAGE_TYPES.includes(page.type) && page.type !== PDF_TYPE,
      )
    ) {
      setUploadError("Choose JPEG, PNG, or PDF files only.");
      return;
    }
    const hasPdf = nextPages.some((page) => page.type === PDF_TYPE);
    if (hasPdf && nextPages.length !== 1) {
      setUploadError("Upload one PDF or a set of JPEG/PNG pages, not both.");
      return;
    }
    if (pages.length && (pages[0].type === PDF_TYPE || hasPdf)) {
      setUploadError(
        "Remove the current paper before switching between a PDF and image pages.",
      );
      return;
    }
    const updatedPages = [...pages, ...nextPages];
    if (updatedPages.length > MAX_IMAGE_PAGES) {
      setUploadError(
        `A paper can contain up to ${MAX_IMAGE_PAGES} image pages.`,
      );
      return;
    }
    if (
      updatedPages.reduce((total, page) => total + page.size, 0) >
      MAX_TOTAL_BYTES
    ) {
      setUploadError("All pages together must be smaller than 20 MB.");
      return;
    }
    setPages(updatedPages);
  }

  function drop(event: DragEvent<HTMLFieldSetElement>) {
    event.preventDefault();
    setDragging(false);
    addPages(event.dataTransfer.files);
  }

  function movePage(index: number, direction: -1 | 1) {
    setPages((currentPages) => {
      const destination = index + direction;
      if (destination < 0 || destination >= currentPages.length)
        return currentPages;
      const updatedPages = [...currentPages];
      [updatedPages[index], updatedPages[destination]] = [
        updatedPages[destination],
        updatedPages[index],
      ];
      return updatedPages;
    });
  }

  function removePage(index: number) {
    setPages((currentPages) =>
      currentPages.filter((_, pageIndex) => pageIndex !== index),
    );
  }

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUploadError("");
    if ((!studentName.trim() && !studentId) || !pages.length) {
      setUploadError(
        "Add the student name and select their paper pages before uploading.",
      );
      return;
    }
    setUploading(true);
    const form = new FormData();
    form.set("student_name", studentName.trim());
    if (studentId) form.set("student_id", studentId);
    pages.forEach((page) => {
      form.append("pages", page);
    });
    try {
      const response = await fetch(`${API}/exams/${exam.id}/submissions`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      const body = await response.json().catch(() => null);
      if (!response.ok)
        throw new Error(body?.detail ?? "The paper could not be uploaded.");
      setSubmission(body);
      const statusResponse = await fetch(
        `${API}/submissions/${body.id}/status`,
        { credentials: "include" },
      );
      if (statusResponse.ok) setProcessing(await statusResponse.json());
    } catch (reason) {
      setUploadError(
        reason instanceof Error
          ? reason.message
          : "The paper could not be uploaded.",
      );
    } finally {
      setUploading(false);
    }
  }

  if (error)
    return (
      <main className="min-h-screen bg-[#e8edf0] p-6 text-[#13252c]">
        <div className="mx-auto max-w-xl rounded-2xl bg-white p-8 shadow-[0_18px_45px_rgba(21,43,51,.12)]">
          <h1 className="text-2xl font-semibold">Assessment unavailable</h1>
          <p className="mt-3 text-[#49616a]">{error}</p>
          <Link
            href="/login"
            className="mt-6 inline-flex rounded-lg bg-[#0f5864] px-4 py-2 text-sm font-semibold text-white"
          >
            Open sign in
          </Link>
        </div>
      </main>
    );
  if (!exam)
    return (
      <main className="grid min-h-screen place-items-center bg-[#e8edf0] text-[#49616a]">
        Loading assessment…
      </main>
    );

  const currentStage = processing?.stage ?? submission?.status;
  const stageIndex = STAGES.indexOf(currentStage);
  return (
    <AppShell
      actions={
        <div className="flex gap-2">
          <Link
            href={`/exams/${exam.id}/insights`}
            className="button-secondary"
          >
            Insights
          </Link>
          <Link href="/exams/new" className="button-primary">
            New assessment
          </Link>
        </div>
      }
    >
      <section className="mx-auto max-w-6xl">
        <div className="flex flex-col justify-between gap-4 border-b border-[var(--line)] pb-7 sm:flex-row sm:items-end">
          <div>
            <h1 className="max-w-3xl font-serif text-4xl font-semibold tracking-[-0.035em]">
              {exam.title}
            </h1>
            <p className="mt-2 text-[var(--ink-muted)]">
              {exam.subject}
              {exam.date ? ` · ${exam.date}` : ""} · {exam.questions.length}{" "}
              questions
            </p>
          </div>
          <span className="status-pill bg-[var(--brand-soft)] text-[var(--brand-strong)]">
            {exam.total_marks} total marks
          </span>
        </div>
        <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(300px,.85fr)]">
          <section className="surface p-5 sm:p-7">
            <h2 className="font-serif text-3xl font-semibold tracking-[-0.025em]">
              Add a student paper
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--ink-muted)]">
              Upload a photographed or scanned answer sheet. PRISM preserves the
              original, normalizes each page, then uses it alongside the
              transcription during grading.
            </p>
            <form onSubmit={upload} className="mt-7 space-y-5">
              {roster.length ? (
                <label className="block text-sm font-semibold text-[#25454e]">
                  Student
                  <select
                    value={studentId}
                    onChange={(event) => {
                      setStudentId(event.target.value);
                      const student = roster.find(
                        (item) => item.id === event.target.value,
                      );
                      setStudentName(student?.name ?? "");
                    }}
                    className="input mt-2"
                  >
                    <option value="">Choose a student from this class</option>
                    {roster.map((student) => (
                      <option key={student.id} value={student.id}>
                        {student.name} ({student.identifier})
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <label className="block text-sm font-semibold text-[#25454e]">
                  Student name
                  <input
                    value={studentName}
                    onChange={(event) => setStudentName(event.target.value)}
                    className="input mt-2"
                    placeholder="e.g. Arun Patel"
                    autoComplete="name"
                  />
                </label>
              )}
              <fieldset
                onDrop={drop}
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                className={`rounded-xl border-2 border-dashed p-7 text-center transition-colors duration-200 ${dragging ? "border-[var(--brand)] bg-[var(--brand-soft)]" : "border-[var(--line)] bg-[var(--surface-muted)]"}`}
              >
                <input
                  id="paper-pages"
                  className="sr-only"
                  type="file"
                  accept="image/jpeg,image/png,application/pdf"
                  multiple
                  onChange={(event) => {
                    addPages(event.target.files ?? []);
                    event.target.value = "";
                  }}
                />
                <input
                  id="camera-page"
                  className="sr-only"
                  type="file"
                  accept="image/jpeg,image/png"
                  capture="environment"
                  onChange={(event) => {
                    addPages(event.target.files ?? []);
                    event.target.value = "";
                  }}
                />
                <span className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-[var(--brand-soft)] text-lg font-semibold text-[var(--brand)]">
                  +
                </span>
                <strong className="mt-3 block text-sm">
                  Drop paper pages here
                </strong>
                <span className="mt-1 block text-sm text-[var(--ink-muted)]">
                  One PDF, or 1–10 JPEG/PNG pages · 20 MB total
                </span>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  <label
                    htmlFor="paper-pages"
                    className="button-secondary cursor-pointer"
                  >
                    Browse files
                  </label>
                  <label
                    htmlFor="camera-page"
                    className="button-secondary cursor-pointer"
                  >
                    Add camera page
                  </label>
                </div>
              </fieldset>
              {pages.length > 0 && (
                <section
                  aria-label="Selected paper pages"
                  className="overflow-hidden rounded-xl border border-[var(--line)]"
                >
                  <div className="flex items-center justify-between bg-[var(--brand-soft)] px-4 py-3 text-sm">
                    <strong>
                      {pages[0].type === PDF_TYPE
                        ? "PDF paper"
                        : `${pages.length} image page${pages.length === 1 ? "" : "s"}`}
                    </strong>
                    <span className="text-[var(--ink-muted)]">
                      {fileSize(
                        pages.reduce((total, page) => total + page.size, 0),
                      )}{" "}
                      total
                    </span>
                  </div>
                  <ol className="divide-y divide-[var(--line)]">
                    {pages.map((page, index) => (
                      <li
                        key={`${page.name}-${page.lastModified}-${page.size}-${index}`}
                        className="flex items-center gap-3 px-4 py-3 text-sm"
                      >
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--brand-soft)] text-xs font-bold text-[var(--brand-strong)]">
                          {index + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <strong className="block truncate">
                            {page.name}
                          </strong>
                          <span className="text-[var(--ink-muted)]">
                            {page.type === PDF_TYPE
                              ? "PDF document"
                              : "Image page"}{" "}
                            · {fileSize(page.size)}
                          </span>
                        </div>
                        <div className="flex shrink-0 gap-1">
                          <button
                            type="button"
                            onClick={() => movePage(index, -1)}
                            disabled={index === 0}
                            aria-label={`Move ${page.name} up`}
                            className="button-quiet px-2 py-1 disabled:cursor-not-allowed disabled:opacity-35"
                          >
                            Up
                          </button>
                          <button
                            type="button"
                            onClick={() => movePage(index, 1)}
                            disabled={index === pages.length - 1}
                            aria-label={`Move ${page.name} down`}
                            className="button-quiet px-2 py-1 disabled:cursor-not-allowed disabled:opacity-35"
                          >
                            Down
                          </button>
                          <button
                            type="button"
                            onClick={() => removePage(index)}
                            aria-label={`Remove ${page.name}`}
                            className="button-quiet px-2 py-1"
                          >
                            Remove
                          </button>
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              )}
              {pages.length > 0 && localPreviewUrl && (
                <section className="overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface-muted)]">
                  <div className="flex items-center justify-between border-b border-[var(--line)] bg-[var(--surface)] px-4 py-3">
                    <strong className="text-sm">Scan preview</strong>
                    <span className="text-xs text-[var(--ink-muted)]">
                      Check orientation and readability before upload
                    </span>
                  </div>
                  {pages[0].type === PDF_TYPE ? (
                    <object
                      data={localPreviewUrl}
                      type="application/pdf"
                      className="h-80 w-full bg-white"
                    >
                      <p className="p-4 text-sm text-[var(--ink-muted)]">
                        Your browser cannot preview this PDF. It will be
                        normalized into page images after upload.
                      </p>
                    </object>
                  ) : (
                    <img
                      src={localPreviewUrl}
                      alt="Selected paper preview"
                      className="h-80 w-full object-contain p-3"
                    />
                  )}
                </section>
              )}
              {uploadError && (
                <p
                  role="alert"
                  className="rounded-xl bg-[var(--review-soft)] px-4 py-3 text-sm text-[var(--review)]"
                >
                  {uploadError}
                </p>
              )}
              <button
                disabled={uploading}
                type="submit"
                className="button-primary w-full py-3"
              >
                {uploading ? "Uploading paper…" : "Upload and begin assessment"}
              </button>
            </form>
            {submission && (
              <section className="mt-7 border-t border-[var(--line)] pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h3 className="font-semibold">
                      {submission.student_name ?? studentName}
                    </h3>
                    <p className="mt-1 text-sm text-[var(--ink-muted)]">
                      {submission.page_count ??
                        (pages[0]?.type === PDF_TYPE
                          ? "Multi-page"
                          : pages.length)}{" "}
                      page paper
                    </p>
                  </div>
                  <span className="status-pill status-neutral">
                    {stageLabel(currentStage)}
                  </span>
                </div>
                <ol className="mt-5 grid grid-cols-3 gap-2 sm:grid-cols-6">
                  {STAGES.map((stage, index) => (
                    <li key={stage} className="text-center">
                      <span
                        className={`mx-auto block h-2 rounded-full transition-colors duration-300 ${index <= stageIndex ? "bg-[var(--brand)]" : "bg-[var(--line)]"}`}
                      />
                      <span className="mt-2 block text-[10px] font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
                        {stageLabel(stage)}
                      </span>
                    </li>
                  ))}
                </ol>
                {processing?.error && (
                  <p className="mt-4 rounded-xl bg-[var(--review-soft)] px-4 py-3 text-sm text-[var(--review)]">
                    {processing.error}
                  </p>
                )}
                {["completed", "review_required"].includes(
                  submission.status,
                ) && (
                  <Link
                    href={`/submissions/${submission.id}`}
                    className="button-secondary mt-5"
                  >
                    Open evidence review
                  </Link>
                )}
              </section>
            )}
          </section>
          <aside className="lg:pt-1">
            <h2 className="text-lg font-semibold">Marking plan</h2>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">
              The rubric below remains the grading source of truth.
            </p>
            <div className="surface mt-4 divide-y divide-[var(--line)] px-5">
              {exam.questions.map((question: any) => (
                <article key={question.id} className="py-5">
                  <div className="flex justify-between gap-4">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--brand)]">
                        {question.number}
                      </p>
                      <h3 className="mt-1 font-semibold leading-5">
                        {question.text}
                      </h3>
                    </div>
                    <span className="shrink-0 text-sm font-semibold text-[var(--ink-muted)]">
                      {question.max_marks}
                    </span>
                  </div>
                  <ul className="mt-3 space-y-2">
                    {question.criteria.map((criterion: any) => (
                      <li
                        key={criterion.id}
                        className="text-sm text-[var(--ink-muted)]"
                      >
                        <span className="font-medium text-[var(--foreground)]">
                          {criterion.title}
                        </span>{" "}
                        · {criterion.max_marks} marks
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          </aside>
        </div>
        <section className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-serif text-2xl font-semibold">
              Submitted papers
            </h2>
            <Link
              href={`/submissions?exam_id=${exam.id}`}
              className="button-quiet"
            >
              View all
            </Link>
          </div>
          <div className="surface-lined overflow-hidden">
            {existingSubmissions.length ? (
              existingSubmissions.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/submissions/${item.id}`}
                  className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4 text-sm last:border-0 hover:bg-[var(--surface-muted)]"
                >
                  <span>
                    <strong className="block">{item.student_name}</strong>
                    <span className="text-[var(--ink-muted)]">
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                  </span>
                  <span className="font-mono">{item.total_score}</span>
                </Link>
              ))
            ) : (
              <p className="p-5 text-sm text-[var(--ink-muted)]">
                No papers have been submitted for this assessment.
              </p>
            )}
          </div>
        </section>
      </section>
    </AppShell>
  );
}
