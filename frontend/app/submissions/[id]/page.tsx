"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";

const API = "/api";

export default function SubmissionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [submission, setSubmission] = useState<any>(null);
  const [selected, setSelected] = useState<any>(null);
  const [error, setError] = useState("");
  const [overrideMarks, setOverrideMarks] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [challenge, setChallenge] = useState("");
  const [proposal, setProposal] = useState<any>(null);
  const [activePage, setActivePage] = useState(0);

  useEffect(() => {
    params.then(({ id }) =>
      fetch(`${API}/submissions/${id}`, { credentials: "include" })
        .then((response) => (response.ok ? response.json() : Promise.reject()))
        .then((data) => {
          setSubmission(data);
          setSelected(data.evaluations[0] ?? null);
        })
        .catch(() => setError("This submission could not be loaded.")),
    );
  }, [params]);

  if (error)
    return (
      <main className="min-h-screen bg-[#f5f1e9] p-8 text-[#172126]">
        {error}
      </main>
    );
  if (!submission)
    return (
      <main className="min-h-screen bg-[#f5f1e9] p-8 text-[#566164]">
        Loading assessment...
      </main>
    );
  const answer = submission.answers?.find(
    (item: any) => item.question_id === selected?.question_id,
  );
  async function saveOverride(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !overrideMarks) return;
    setSaving(true);
    const response = await fetch(`${API}/evaluations/${selected.id}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        marks: Number(overrideMarks),
        reason: overrideReason || null,
      }),
    });
    if (response.ok) {
      const refreshed = await fetch(`${API}/submissions/${submission.id}`, {
        credentials: "include",
      });
      const data = await refreshed.json();
      setSubmission(data);
      setSelected(
        data.evaluations.find((item: any) => item.id === selected.id),
      );
      setOverrideMarks("");
      setOverrideReason("");
    }
    setSaving(false);
  }
  async function requestReview(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !challenge.trim()) return;
    setSaving(true);
    const response = await fetch(`${API}/evaluations/${selected.id}/review`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ comment: challenge }),
    });
    if (response.ok) {
      setProposal(await response.json());
      setChallenge("");
    }
    setSaving(false);
  }
  async function decideReview(decision: "accept" | "reject") {
    if (!proposal) return;
    setSaving(true);
    const response = await fetch(`${API}/reviews/${proposal.id}/${decision}`, {
      method: "POST",
      credentials: "include",
    });
    if (response.ok) {
      const refreshed = await fetch(`${API}/submissions/${submission.id}`, {
        credentials: "include",
      });
      const data = await refreshed.json();
      setSubmission(data);
      setSelected(
        data.evaluations.find((item: any) => item.id === selected.id),
      );
      setProposal(null);
    }
    setSaving(false);
  }
  return (
    <AppShell
      actions={
        <Link
          href={`/exams/${submission.exam_id ?? ""}`}
          className="button-secondary"
        >
          Back to exam
        </Link>
      }
    >
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-col justify-between gap-3 border-b border-[var(--line)] pb-6 sm:flex-row sm:items-end">
          <div>
            <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
              {submission.student_name}
            </h1>
            <p className="mt-2 text-sm text-[var(--ink-muted)]">
              {submission.exam_title} · {submission.total_score} marks
            </p>
          </div>
          <span className="status-pill status-neutral">
            Teacher decision required
          </span>
        </div>
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(21rem,.8fr)]">
          <section className="surface overflow-hidden">
            <div className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4">
              <div>
                <h2 className="font-serif text-2xl font-semibold">
                  Original paper
                </h2>
                <p className="mt-1 text-sm text-[var(--ink-muted)]">
                  Use the page image as ground evidence.
                </p>
              </div>
              <span className="text-sm text-[var(--ink-muted)]">
                {submission.pages.length} page
                {submission.pages.length === 1 ? "" : "s"}
              </span>
            </div>
            {submission.pages.length ? (
              <div className="grid min-h-[38rem] grid-cols-[5rem_minmax(0,1fr)] bg-[var(--surface-muted)]">
                <nav
                  className="flex flex-col gap-2 border-r border-[var(--line)] bg-[var(--surface)] p-2"
                  aria-label="Paper pages"
                >
                  {submission.pages.map((page: any, index: number) => (
                    <button
                      key={page.id}
                      type="button"
                      onClick={() => setActivePage(index)}
                      aria-current={activePage === index ? "page" : undefined}
                      className={`overflow-hidden rounded-md border p-1 text-xs font-semibold transition-colors ${activePage === index ? "border-[var(--brand)] bg-[var(--brand-soft)] text-[var(--brand-strong)]" : "border-[var(--line)] text-[var(--ink-muted)]"}`}
                    >
                      <img
                        src={`${API.replace(/\/api$/, "")}${page.url}`}
                        alt=""
                        className="mb-1 aspect-[3/4] w-full object-cover"
                      />
                      {page.page_number}
                    </button>
                  ))}
                </nav>
                <div className="flex items-center justify-center overflow-auto p-4">
                  <img
                    src={`${API.replace(/\/api$/, "")}${submission.pages[activePage]?.url}`}
                    alt={`Original paper page ${submission.pages[activePage]?.page_number}`}
                    className="max-h-[44rem] w-auto max-w-full rounded-md shadow-[0_12px_28px_rgb(30_42_43_/_0.14)]"
                  />
                </div>
              </div>
            ) : (
              <p className="m-5 rounded-lg bg-[var(--surface-muted)] p-4 text-sm text-[var(--ink-muted)]">
                No original paper is attached to this cached submission.
              </p>
            )}
          </section>
          <aside className="min-w-0">
            <section className="surface overflow-hidden">
              <div className="border-b border-[var(--line)] p-5">
                <p className="text-sm text-[var(--ink-muted)]">
                  Assessment result
                </p>
                <h2 className="font-serif text-2xl font-semibold">
                  Criterion review
                </h2>
              </div>
              <div className="max-h-[23rem] divide-y divide-[var(--line)] overflow-y-auto">
                {submission.evaluations.map((evaluation: any) => (
                  <button
                    type="button"
                    key={evaluation.id}
                    onClick={() => {
                      setSelected(evaluation);
                      setProposal(null);
                    }}
                    className={`w-full p-4 text-left transition-colors duration-150 ${selected?.id === evaluation.id ? "bg-[var(--brand-soft)]" : "hover:bg-[var(--surface-muted)]"}`}
                  >
                    <div className="flex justify-between gap-3">
                      <span>
                        <strong className="block text-sm">
                          {evaluation.question_number} ·{" "}
                          {evaluation.criterion_title}
                        </strong>
                        <span className="text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                          {evaluation.concept}
                        </span>
                      </span>
                      <strong className="font-mono text-sm">
                        {evaluation.effective_marks}/{evaluation.max_marks}
                      </strong>
                    </div>
                  </button>
                ))}
              </div>
            </section>
            {selected && (
              <section className="surface mt-5 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm text-[var(--ink-muted)]">
                      {selected.question_number}
                    </p>
                    <h2 className="font-serif text-xl font-semibold">
                      {selected.criterion_title}
                    </h2>
                  </div>
                  <span
                    className={
                      selected.needs_review
                        ? "status-pill status-review"
                        : "status-pill status-success"
                    }
                  >
                    {selected.needs_review
                      ? "Review recommended"
                      : "High confidence"}
                  </span>
                </div>
                <p className="mt-4 text-sm leading-6 text-[var(--ink-muted)]">
                  {selected.reason}
                </p>
                <blockquote className="mt-4 border-l border-[var(--line)] pl-3 text-sm italic text-[var(--ink-muted)]">
                  “{selected.evidence[0]?.quote ?? "No quotation was returned."}
                  ”
                </blockquote>
                {answer && (
                  <div className="mt-5 border-t border-[var(--line)] pt-4">
                    <h3 className="text-sm font-medium">Transcription</h3>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[var(--ink-muted)]">
                      {answer.transcription}
                    </p>
                    {answer.uncertainty.length > 0 && (
                      <p className="mt-3 text-xs text-[var(--review)]">
                        Contains uncertain transcription.
                      </p>
                    )}
                  </div>
                )}
                <form
                  onSubmit={requestReview}
                  className="mt-5 border-t border-[var(--line)] pt-4"
                >
                  <h3 className="text-sm font-medium">
                    Challenge this decision
                  </h3>
                  <div className="mt-3 flex gap-2">
                    <input
                      aria-label="Challenge explanation"
                      className="input"
                      value={challenge}
                      onChange={(event) => setChallenge(event.target.value)}
                      placeholder="What evidence should PRISM reconsider?"
                    />
                    <button
                      type="submit"
                      disabled={saving}
                      className="button-secondary shrink-0"
                    >
                      Ask Luna
                    </button>
                  </div>
                </form>
                {proposal && (
                  <section className="mt-4 rounded-lg bg-[var(--review-soft)] p-4">
                    <p className="text-sm">
                      Luna suggests{" "}
                      <strong>
                        {proposal.suggested_marks}/{selected.max_marks}
                      </strong>
                      . {proposal.reason}
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        onClick={() => decideReview("accept")}
                        disabled={saving}
                        className="button-primary"
                      >
                        Accept
                      </button>
                      <button
                        type="button"
                        onClick={() => decideReview("reject")}
                        disabled={saving}
                        className="button-secondary"
                      >
                        Reject
                      </button>
                    </div>
                  </section>
                )}
                <form
                  onSubmit={saveOverride}
                  className="mt-5 border-t border-[var(--line)] pt-4"
                >
                  <h3 className="text-sm font-medium">Teacher override</h3>
                  <div className="mt-3 grid gap-2 sm:grid-cols-[100px_1fr_auto]">
                    <input
                      aria-label="Override marks"
                      className="input"
                      type="number"
                      min="0"
                      max={selected.max_marks}
                      step="0.5"
                      value={overrideMarks}
                      onChange={(event) => setOverrideMarks(event.target.value)}
                      placeholder="Marks"
                    />
                    <input
                      aria-label="Override reason"
                      className="input"
                      value={overrideReason}
                      onChange={(event) =>
                        setOverrideReason(event.target.value)
                      }
                      placeholder="Optional reason"
                    />
                    <button
                      type="submit"
                      disabled={saving}
                      className="button-primary"
                    >
                      {saving ? "Saving" : "Apply"}
                    </button>
                  </div>
                </form>
              </section>
            )}
          </aside>
        </div>
      </div>
    </AppShell>
  );
}
