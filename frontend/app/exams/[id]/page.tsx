"use client";

import Link from "next/link";
import { DragEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "application/pdf"];
const STAGES = ["uploaded", "preprocessing", "transcribing", "grading", "review_required", "completed"];

function stageLabel(stage?: string) {
  return (stage ?? "uploaded").replaceAll("_", " ");
}

function fileSize(size: number) {
  return `${(size / 1024 / 1024).toFixed(size > 10 * 1024 * 1024 ? 0 : 1)} MB`;
}

export default function ExamPage({ params }: { params: Promise<{ id: string }> }) {
  const [exam, setExam] = useState<any>(null);
  const [error, setError] = useState("");
  const [studentName, setStudentName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [submission, setSubmission] = useState<any>(null);
  const [processing, setProcessing] = useState<any>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    params.then(({ id }) => fetch(`${API}/exams/${id}`, { credentials: "include" })
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then(setExam)
      .catch(() => setError("This assessment could not be loaded. Sign in and try again.")));
  }, [params]);

  useEffect(() => {
    if (!submission || ["completed", "review_required", "failed"].includes(submission.status)) return;
    const timer = window.setInterval(async () => {
      const [submissionResponse, statusResponse] = await Promise.all([
        fetch(`${API}/submissions/${submission.id}`, { credentials: "include" }),
        fetch(`${API}/submissions/${submission.id}/status`, { credentials: "include" }),
      ]);
      if (submissionResponse.ok) setSubmission(await submissionResponse.json());
      if (statusResponse.ok) setProcessing(await statusResponse.json());
    }, 1800);
    return () => window.clearInterval(timer);
  }, [submission]);

  function chooseFile(nextFile: File | undefined) {
    setUploadError("");
    if (!nextFile) return;
    if (!ACCEPTED_TYPES.includes(nextFile.type)) {
      setUploadError("Choose a JPEG, PNG, or PDF paper.");
      return;
    }
    if (nextFile.size > 20 * 1024 * 1024) {
      setUploadError("The paper must be smaller than 20 MB.");
      return;
    }
    setFile(nextFile);
  }

  function drop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  }

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUploadError("");
    if (!studentName.trim() || !file) {
      setUploadError("Add the student name and select their paper before uploading.");
      return;
    }
    setUploading(true);
    const form = new FormData();
    form.set("student_name", studentName.trim());
    form.set("file", file);
    try {
      const response = await fetch(`${API}/exams/${exam.id}/submissions`, { method: "POST", credentials: "include", body: form });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(body?.detail ?? "The paper could not be uploaded.");
      setSubmission(body);
      const statusResponse = await fetch(`${API}/submissions/${body.id}/status`, { credentials: "include" });
      if (statusResponse.ok) setProcessing(await statusResponse.json());
    } catch (reason) {
      setUploadError(reason instanceof Error ? reason.message : "The paper could not be uploaded.");
    } finally {
      setUploading(false);
    }
  }

  if (error) return <main className="min-h-screen bg-[#e8edf0] p-6 text-[#13252c]"><div className="mx-auto max-w-xl rounded-2xl bg-white p-8 shadow-[0_18px_45px_rgba(21,43,51,.12)]"><h1 className="text-2xl font-semibold">Assessment unavailable</h1><p className="mt-3 text-[#49616a]">{error}</p><Link href="/login" className="mt-6 inline-flex rounded-lg bg-[#0f5864] px-4 py-2 text-sm font-semibold text-white">Open sign in</Link></div></main>;
  if (!exam) return <main className="grid min-h-screen place-items-center bg-[#e8edf0] text-[#49616a]">Loading assessment…</main>;

  const currentStage = processing?.stage ?? submission?.status;
  const stageIndex = STAGES.indexOf(currentStage);
  return <main className="min-h-screen bg-[#e8edf0] text-[#13252c]">
    <header className="border-b border-[#13252c]/10 bg-white px-5 py-4 sm:px-8"><div className="mx-auto flex max-w-6xl items-center justify-between gap-4"><Link href="/" className="text-xl font-bold tracking-tight text-[#0f5864]">PRISM</Link><div className="flex items-center gap-4"><span className="hidden text-sm text-[#49616a] sm:block">{exam.subject}</span><Link href="/exams/new" className="text-sm font-semibold text-[#0f5864]">New assessment</Link></div></div></header>
    <section className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
      <div className="flex flex-col justify-between gap-4 border-b border-[#13252c]/12 pb-7 sm:flex-row sm:items-end"><div><h1 className="max-w-3xl text-3xl font-semibold tracking-[-0.03em] sm:text-4xl">{exam.title}</h1><p className="mt-2 text-[#49616a]">{exam.subject}{exam.date ? ` · ${exam.date}` : ""} · {exam.questions.length} questions</p></div><span className="rounded-full bg-[#d5ebe8] px-4 py-2 text-sm font-semibold text-[#075462]">{exam.total_marks} total marks</span></div>
      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(300px,.85fr)]">
        <section className="rounded-2xl bg-white p-5 shadow-[0_18px_45px_rgba(21,43,51,.1)] sm:p-7"><h2 className="text-2xl font-semibold tracking-[-0.02em]">Add a student paper</h2><p className="mt-2 max-w-xl text-sm leading-6 text-[#49616a]">Upload a photographed or scanned answer sheet. PRISM preserves the original, normalizes each page, then uses it alongside the transcription during grading.</p>
          <form onSubmit={upload} className="mt-7 space-y-5"><label className="block text-sm font-semibold text-[#25454e]">Student name<input value={studentName} onChange={(event) => setStudentName(event.target.value)} className="input mt-2" placeholder="e.g. Arun Patel" autoComplete="name" /></label>
            <label htmlFor="paper" onDrop={drop} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} className={`block cursor-pointer rounded-xl border-2 border-dashed p-7 text-center transition ${dragging ? "border-[#0f5864] bg-[#e6f4f1]" : "border-[#b9c8cc] bg-[#f7faf9] hover:border-[#5d8d95]"}`}><input id="paper" className="sr-only" type="file" accept="image/jpeg,image/png,application/pdf" capture="environment" onChange={(event) => chooseFile(event.target.files?.[0])} /><span className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-[#d5ebe8] text-xl text-[#0f5864]">↑</span><strong className="mt-3 block text-sm">Drop a paper here, or browse files</strong><span className="mt-1 block text-sm text-[#49616a]">JPEG, PNG, or PDF · up to 20 MB · mobile camera supported</span></label>
            {file && <div className="flex items-center justify-between gap-3 rounded-xl bg-[#e6f4f1] px-4 py-3 text-sm"><div className="min-w-0"><strong className="block truncate">{file.name}</strong><span className="text-[#49616a]">{file.type === "application/pdf" ? "PDF document" : "Image"} · {fileSize(file.size)}</span></div><button type="button" onClick={() => setFile(null)} className="rounded-md px-2 py-1 font-semibold text-[#0f5864] hover:bg-white">Remove</button></div>}
            {uploadError && <p role="alert" className="rounded-xl bg-[#fff0e9] px-4 py-3 text-sm text-[#9b3e23]">{uploadError}</p>}
            <button disabled={uploading} type="submit" className="w-full rounded-xl bg-[#0f5864] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#0b4650] disabled:cursor-not-allowed disabled:opacity-60">{uploading ? "Uploading paper…" : "Upload and begin assessment"}</button>
          </form>
          {submission && <section className="mt-7 border-t border-[#13252c]/10 pt-6"><div className="flex items-center justify-between gap-4"><div><h3 className="font-semibold">{submission.student_name ?? studentName}</h3><p className="mt-1 text-sm text-[#49616a]">{submission.page_count ?? (file?.type === "application/pdf" ? "Multi-page" : "1")} page paper</p></div><span className="rounded-full bg-[#eef3f4] px-3 py-1 text-xs font-bold uppercase tracking-wide text-[#0f5864]">{stageLabel(currentStage)}</span></div><ol className="mt-5 grid grid-cols-3 gap-2 sm:grid-cols-6">{STAGES.map((stage, index) => <li key={stage} className="text-center"><span className={`mx-auto block h-2 rounded-full ${index <= stageIndex ? "bg-[#0f5864]" : "bg-[#d6e0e2]"}`} /><span className="mt-2 block text-[10px] font-semibold uppercase tracking-wide text-[#49616a]">{stageLabel(stage)}</span></li>)}</ol>{processing?.error && <p className="mt-4 rounded-xl bg-[#fff0e9] px-4 py-3 text-sm text-[#9b3e23]">{processing.error}</p>}{["completed", "review_required"].includes(submission.status) && <Link href={`/submissions/${submission.id}`} className="mt-5 inline-flex rounded-lg border border-[#0f5864] px-4 py-2 text-sm font-semibold text-[#0f5864] hover:bg-[#e6f4f1]">Open evidence review</Link>}</section>}
        </section>
        <aside className="lg:pt-1"><h2 className="text-lg font-semibold">Marking plan</h2><p className="mt-1 text-sm text-[#49616a]">The rubric below remains the grading source of truth.</p><div className="mt-4 divide-y divide-[#13252c]/10 rounded-2xl bg-white px-5 shadow-[0_18px_45px_rgba(21,43,51,.08)]">{exam.questions.map((question: any) => <article key={question.id} className="py-5"><div className="flex justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[.14em] text-[#0f5864]">{question.number}</p><h3 className="mt-1 font-semibold leading-5">{question.text}</h3></div><span className="shrink-0 text-sm font-semibold text-[#49616a]">{question.max_marks}</span></div><ul className="mt-3 space-y-2">{question.criteria.map((criterion: any) => <li key={criterion.id} className="text-sm text-[#49616a]"><span className="font-medium text-[#25454e]">{criterion.title}</span> · {criterion.max_marks} marks</li>)}</ul></article>)}</div></aside>
      </div>
    </section>
  </main>;
}
