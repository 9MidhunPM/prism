"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export default function ExamPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [exam, setExam] = useState<any>(null);
  const [error, setError] = useState("");
  const [studentName, setStudentName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [submission, setSubmission] = useState<any>(null);
  const [processing, setProcessing] = useState<any>(null);

  useEffect(() => {
    params.then(({ id }) =>
      fetch(`${API}/exams/${id}`)
        .then((response) => (response.ok ? response.json() : Promise.reject()))
        .then(setExam)
        .catch(() => setError("This exam could not be loaded.")),
    );
  }, [params]);

  useEffect(() => {
    if (
      !submission ||
      ["completed", "review_required", "failed"].includes(submission.status)
    )
      return;
    const timer = window.setInterval(async () => {
      const [submissionResponse, statusResponse] = await Promise.all([
        fetch(`${API}/submissions/${submission.id}`),
        fetch(`${API}/submissions/${submission.id}/status`),
      ]);
      if (submissionResponse.ok) setSubmission(await submissionResponse.json());
      if (statusResponse.ok) setProcessing(await statusResponse.json());
    }, 2000);
    return () => window.clearInterval(timer);
  }, [submission]);

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUploadError("");
    if (!studentName.trim() || !file) {
      setUploadError(
        "Enter the student's name and choose a JPEG, PNG, or PDF paper.",
      );
      return;
    }
    const form = new FormData();
    form.set("student_name", studentName);
    form.set("file", file);
    try {
      const response = await fetch(`${API}/exams/${exam.id}/submissions`, {
        method: "POST",
        body: form,
      });
      if (!response.ok) throw new Error();
      const created = await response.json();
      setSubmission(created);
      const statusResponse = await fetch(
        `${API}/submissions/${created.id}/status`,
      );
      if (statusResponse.ok) setProcessing(await statusResponse.json());
    } catch {
      setUploadError(
        "The paper could not be uploaded. Check the file and try again.",
      );
    }
  }

  if (error)
    return (
      <main className="min-h-screen bg-[#f5f1e9] p-8 text-[#172126]">
        <p>{error}</p>
        <Link href="/" className="mt-4 inline-block text-sm underline">
          Return to workspace
        </Link>
      </main>
    );
  if (!exam)
    return (
      <main className="min-h-screen bg-[#f5f1e9] p-8 text-[#566164]">
        Loading exam...
      </main>
    );
  return (
    <main className="min-h-screen bg-[#f5f1e9] text-[#172126]">
      <header className="border-b border-[#172126]/10 bg-[#fcfaf5] px-5 py-4 sm:px-8">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link href="/" className="font-serif text-2xl font-bold">
            PRISM
          </Link>
          <Link
            href="/exams/new"
            className="text-sm text-[#173f4c] underline underline-offset-4"
          >
            Create another exam
          </Link>
        </div>
      </header>
      <section className="mx-auto max-w-5xl px-5 py-8 sm:px-8">
        <p className="text-sm text-[#667174]">
          {exam.subject}
          {exam.date ? ` · ${exam.date}` : ""}
        </p>
        <div className="mt-1 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <h1 className="font-serif text-3xl font-semibold">{exam.title}</h1>
          <strong className="font-mono text-lg">
            {exam.total_marks} marks
          </strong>
        </div>
        <section className="mt-8 rounded-lg border border-[#173f4c]/15 bg-[#fcfaf5] p-5">
          <div className="flex flex-col justify-between gap-2 sm:flex-row">
            <div>
              <h2 className="font-serif text-xl font-semibold">
                Upload a student paper
              </h2>
              <p className="mt-1 text-sm text-[#566164]">
                JPEG, PNG, or PDF. Originals are retained as grading evidence.
              </p>
            </div>
            {submission && (
              <span className="text-sm font-medium text-[#173f4c]">
                {(processing?.stage ?? submission.status).replaceAll("_", " ")}
              </span>
            )}
          </div>
          {uploadError && (
            <p className="mt-4 text-sm text-[#a15130]">{uploadError}</p>
          )}
          {submission?.error && (
            <p className="mt-4 rounded-md bg-[#fff4e9] p-3 text-sm text-[#8b3d20]">
              {submission.error}
            </p>
          )}
          <form
            onSubmit={upload}
            className="mt-5 grid gap-3 sm:grid-cols-[1fr_1fr_auto]"
          >
            <input
              aria-label="Student name"
              name="student_name"
              value={studentName}
              onChange={(event) => setStudentName(event.target.value)}
              className="input"
              placeholder="Student name"
            />
            <input
              aria-label="Exam paper"
              name="paper"
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="input text-sm"
            />
            <button
              type="submit"
              className="rounded-md bg-[#173f4c] px-4 py-2 text-sm font-medium text-white"
            >
              Upload paper
            </button>
          </form>
          {submission && (
            <div className="mt-5 rounded-md bg-[#f5f1e9] p-4 text-sm">
              <p>
                <strong>{submission.student_name}</strong> · {submission.page_count} page
                {submission.page_count === 1 ? "" : "s"}
              </p>
              <p className="mt-1 text-[#566164]">
                {["completed", "review_required"].includes(submission.status)
                  ? "Assessment is ready to inspect."
                  : `Stage: ${(processing?.stage ?? "processing").replaceAll("_", " ")}.`}
              </p>
              {processing?.error && (
                <p className="mt-2 text-[#a15130]">{processing.error}</p>
              )}
              {["completed", "review_required"].includes(submission.status) && (
                <Link
                  href={`/submissions/${submission.id}`}
                  className="mt-3 inline-block font-medium text-[#173f4c] underline underline-offset-4"
                >
                  Open assessment
                </Link>
              )}
            </div>
          )}
        </section>
        <div className="mt-8 space-y-4">
          {exam.questions.map((question: any) => (
            <article
              key={question.id}
              className="rounded-lg border border-[#172126]/10 bg-[#fcfaf5] p-5"
            >
              <div className="flex justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[#173f4c]">
                    {question.number}
                  </p>
                  <h2 className="mt-1 text-lg font-medium">{question.text}</h2>
                </div>
                <span className="font-mono text-sm">
                  {question.max_marks} marks
                </span>
              </div>
              <div className="mt-5 divide-y divide-[#172126]/8 border-y border-[#172126]/8">
                {question.criteria.map((criterion: any) => (
                  <div
                    key={criterion.id}
                    className="grid gap-1 py-3 sm:grid-cols-[1fr_auto]"
                  >
                    <div>
                      <strong className="text-sm">{criterion.title}</strong>
                      <p className="text-sm text-[#566164]">
                        {criterion.description}
                      </p>
                      <p className="mt-1 text-xs uppercase tracking-wide text-[#667174]">
                        {criterion.concept}
                      </p>
                    </div>
                    <span className="font-mono text-sm">
                      {criterion.max_marks}
                    </span>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
