"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";

const API = "/api";

export default function SubmissionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
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
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        !submission ||
        ["INPUT", "TEXTAREA", "SELECT"].includes(
          (event.target as HTMLElement)?.tagName,
        )
      )
        return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const questions: any[] = Array.from(
        new Map(
          submission.evaluations.map((evaluation: any) => [
            evaluation.question_id,
            evaluation,
          ]),
        ).values(),
      );
      const index = questions.findIndex(
        (evaluation: any) => evaluation.question_id === selected?.question_id,
      );
      const next = questions[index + (event.key === "ArrowRight" ? 1 : -1)];
      if (!next) return;
      event.preventDefault();
      setSelected(next);
      setProposal(null);
      const evidencePageId = next.evidence?.[0]?.page_id;
      const pageIndex = submission.pages.findIndex(
        (page: any) => page.id === evidencePageId,
      );
      if (pageIndex >= 0) setActivePage(pageIndex);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selected, submission]);

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
  const answers = submission.answers?.filter(
    (item: any) => item.question_id === selected?.question_id,
  );
  const questions: any[] = Array.from(
    new Map(
      submission.evaluations.map((evaluation: any) => [
        evaluation.question_id,
        evaluation,
      ]),
    ).values(),
  ) as any[];
  const activeQuestionIndex = questions.findIndex(
    (evaluation) => evaluation.question_id === selected?.question_id,
  );
  const activeEvaluations = submission.evaluations.filter(
    (evaluation: any) => evaluation.question_id === selected?.question_id,
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
  async function completeReview() {
    if (!selected) return;
    setSaving(true);
    const response = await fetch(
      `${API}/evaluations/${selected.id}/complete-review`,
      { method: "POST", credentials: "include" },
    );
    if (response.ok) {
      const data = await (
        await fetch(`${API}/submissions/${submission.id}`, {
          credentials: "include",
        })
      ).json();
      setSubmission(data);
      setSelected(
        data.evaluations.find((item: any) => item.id === selected.id),
      );
      setProposal(null);
    }
    setSaving(false);
  }
  async function replacePage(file: File | undefined) {
    const page = submission?.pages[activePage];
    if (!file || !page) return;
    setSaving(true);
    setError("");
    try {
      const form = new FormData();
      form.set("file", file);
      await api.request(`/api/submissions/${submission.id}/pages/${page.id}`, {
        method: "PUT",
        body: form,
      });
      setSubmission(await api.get(`/api/submissions/${submission.id}`));
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The replacement scan could not be uploaded.",
      );
    } finally {
      setSaving(false);
    }
  }
  async function removePaper() {
    if (
      !window.confirm(
        "Delete this paper permanently? Its evaluations, evidence, and review history will be removed.",
      )
    )
      return;
    await api.delete(`/api/submissions/${submission.id}`);
    router.replace("/submissions");
  }
  async function setReleased(released: boolean) {
    setSaving(true);
    try {
      await api.patch(`/api/submissions/${submission.id}/release`, { released });
      setSubmission(await api.get(`/api/submissions/${submission.id}`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The release status could not be updated.");
    } finally {
      setSaving(false);
    }
  }
  return (
    <AppShell
      workbench
      actions={
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void setReleased(!submission.released_at)}
            disabled={saving || (!submission.released_at && !["completed", "review_required"].includes(submission.status))}
            className={submission.released_at ? "button-secondary" : "button-primary"}
          >
            {submission.released_at ? "Unrelease results" : "Release results"}
          </button>
          <button
            type="button"
            onClick={() => void removePaper()}
            className="button-quiet"
          >
            Delete paper
          </button>
          <Link
            href={`/exams/${submission.exam_id}`}
            className="button-secondary"
          >
            Back to exam
          </Link>
        </div>
      }
    >
      <div className="mx-auto max-w-[100rem] xl:flex xl:h-full xl:flex-col">
        <div className="mb-6 flex flex-col justify-between gap-3 border-b border-[var(--line)] pb-6 sm:flex-row sm:items-end xl:mb-4 xl:shrink-0 xl:pb-4">
          <div>
            <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
              {submission.student_name}
            </h1>
            <p className="mt-2 text-sm text-[var(--ink-muted)]">
              {submission.exam_title} · {submission.total_score} marks
            </p>
          </div>
          <span
            className={`status-pill ${submission.pages.some((page: any) => page.quality_status === "rescan_required") ? "status-review" : "status-neutral"}`}
          >
            {submission.pages.some(
              (page: any) => page.quality_status === "rescan_required",
            )
              ? "Rescan required"
              : "Evidence review"}
          </span>
        </div>
        <div className="grid gap-6 xl:min-h-0 xl:flex-1 xl:grid-cols-[minmax(0,1.5fr)_minmax(28rem,1fr)]">
          <section className="surface overflow-hidden xl:flex xl:min-h-0 xl:flex-col">
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
              <div className="grid min-h-[38rem] grid-cols-[5rem_minmax(0,1fr)] bg-[var(--surface-muted)] xl:min-h-0 xl:flex-1">
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
                        src={`${API.replace(/\/api$/, "")}${page.preview_url}`}
                        alt=""
                        className="mb-1 aspect-[3/4] w-full object-cover"
                      />
                      {page.page_number}
                    </button>
                  ))}
                </nav>
                <div className="flex items-center justify-center overflow-auto p-4">
                  <img
                    src={`${API.replace(/\/api$/, "")}${submission.pages[activePage]?.preview_url}`}
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
            {(submission.pages[activePage]?.quality_status ===
              "rescan_required" ||
              !submission.pages[activePage]?.original_available) && (
              <div className="border-t border-[var(--line)] bg-[var(--review-soft)] p-4">
                <p className="text-sm font-semibold text-[var(--review)]">
                  {submission.pages[activePage]?.original_available
                    ? "Rescan required"
                    : "Original scan unavailable"}
                </p>
                <p className="mt-1 text-sm text-[var(--review)]">
                  {submission.pages[activePage]?.original_available
                    ? (submission.pages[activePage]?.quality_reason ??
                      "This page is too unclear to grade responsibly.")
                    : "This scan was not retained after a previous deployment. Upload a replacement page to restore the original evidence."}
                </p>
                <label className="button-secondary mt-3 cursor-pointer">
                  <span>{saving ? "Uploading..." : "Replace this page"}</span>
                  <input
                    className="sr-only"
                    disabled={saving}
                    type="file"
                    accept="image/jpeg,image/png"
                    onChange={(event) => {
                      void replacePage(event.target.files?.[0]);
                      event.target.value = "";
                    }}
                  />
                </label>
              </div>
            )}
          </section>
          <aside className="min-w-0 xl:min-h-0 xl:overflow-y-auto xl:pr-1">
            <section className="surface overflow-hidden">
              <div className="border-b border-[var(--line)] p-5">
                <p className="text-sm text-[var(--ink-muted)]">
                  Assessment result
                </p>
                <h2 className="font-serif text-2xl font-semibold">
                  Question review
                </h2>
                <p className="mt-1 text-xs text-[var(--ink-muted)]">
                  Use Left and Right arrow keys to move between questions.
                </p>
              </div>
              <div className="max-h-[23rem] divide-y divide-[var(--line)] overflow-y-auto">
                {questions.map((evaluation) => (
                  <button
                    type="button"
                    key={evaluation.id}
                    onClick={() => {
                      setSelected(evaluation);
                      setProposal(null);
                      const pageIndex = submission.pages.findIndex(
                        (page: any) =>
                          page.id === evaluation.evidence?.[0]?.page_id,
                      );
                      if (pageIndex >= 0) setActivePage(pageIndex);
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
                      selected.review_resolved
                        ? "status-pill status-success"
                        : selected.review_severity === "review_required"
                          ? "status-pill status-danger"
                          : selected.review_severity === "review_recommended"
                            ? "status-pill status-review"
                            : "status-pill status-success"
                    }
                  >
                    {selected.review_resolved
                      ? "Teacher reviewed"
                      : selected.review_severity === "review_required"
                        ? "Review required"
                        : selected.review_severity === "review_recommended"
                          ? "Review advised"
                          : "High confidence"}
                  </span>
                </div>
                <p className="mt-2 text-xs text-[var(--ink-muted)]">
                  Model confidence: {Math.round(selected.confidence * 100)}%.
                  This is a review signal, not a calibrated probability.
                </p>
                <div className="mt-3 flex items-center justify-between border-y border-[var(--line)] py-3 text-xs font-semibold text-[var(--ink-muted)]">
                  <button
                    type="button"
                    className="button-quiet px-2 py-1"
                    disabled={activeQuestionIndex <= 0}
                    onClick={() =>
                      setSelected(questions[activeQuestionIndex - 1])
                    }
                  >
                    Previous
                  </button>
                  <span>
                    Question {activeQuestionIndex + 1} of {questions.length}
                  </span>
                  <button
                    type="button"
                    className="button-quiet px-2 py-1"
                    disabled={activeQuestionIndex >= questions.length - 1}
                    onClick={() =>
                      setSelected(questions[activeQuestionIndex + 1])
                    }
                  >
                    Next
                  </button>
                </div>
                <div className="mt-4 space-y-2">
                  {activeEvaluations.map((evaluation: any) => (
                    <button
                      key={evaluation.id}
                      type="button"
                      onClick={() => setSelected(evaluation)}
                      className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm ${selected?.id === evaluation.id ? "bg-[var(--brand-soft)] text-[var(--brand-strong)]" : "bg-[var(--surface-muted)]"}`}
                    >
                      <span>{evaluation.criterion_title}</span>
                      <span className="font-mono">
                        {evaluation.effective_marks}/{evaluation.max_marks}
                      </span>
                    </button>
                  ))}
                </div>
                <p className="mt-4 text-sm leading-6 text-[var(--ink-muted)]">
                  {selected.reason}
                </p>
                {selected.evidence.map((evidence: any) => (
                  <button
                    key={`${evidence.page_id}-${evidence.quote}`}
                    type="button"
                    onClick={() => {
                      const index = submission.pages.findIndex(
                        (page: any) => page.id === evidence.page_id,
                      );
                      if (index >= 0) setActivePage(index);
                    }}
                    className="mt-3 block w-full border-l border-[var(--line)] pl-3 text-left text-sm italic text-[var(--ink-muted)] hover:text-[var(--brand-strong)]"
                  >
                    Page {evidence.page ?? "?"}: “{evidence.quote}”
                  </button>
                ))}
                {answers?.length > 0 && (
                  <div className="mt-5 border-t border-[var(--line)] pt-4">
                    <h3 className="text-sm font-medium">Transcription</h3>
                    {answers.map((answer: any) => {
                      const page = submission.pages.find(
                        (item: any) => item.id === answer.page_id,
                      );
                      return (
                        <div key={answer.id} className="mt-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
                            Page {page?.page_number ?? "?"}
                            {answer.mapping_basis ===
                            "previous_page_continuation"
                              ? " · continuation"
                              : ""}
                          </p>
                          <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-[var(--ink-muted)]">
                            {answer.transcription}
                          </p>
                          {answer.uncertainty.length > 0 && (
                            <p className="mt-2 text-xs text-[var(--review)]">
                              Contains uncertain transcription:{" "}
                              {answer.uncertainty
                                .map(
                                  (segment: any) =>
                                    `${segment.text} (${Math.round((segment.confidence ?? 0) * 100)}%)`,
                                )
                                .join(", ")}
                              .
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
                {!selected.review_resolved && selected.review_severity && (
                  <div className="mt-5 border-t border-[var(--line)] pt-4">
                    <button
                      type="button"
                      onClick={() => void completeReview()}
                      disabled={saving}
                      className="button-secondary"
                    >
                      {saving ? "Saving" : "Complete review"}
                    </button>
                    <p className="mt-2 text-xs text-[var(--ink-muted)]">
                      Confirms this review and keeps the current mark unchanged.
                    </p>
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
                      Ask PRISM
                    </button>
                  </div>
                </form>
                {proposal && (
                  <section className="mt-4 rounded-lg bg-[var(--review-soft)] p-4">
                    <p className="text-sm">
                      PRISM suggests{" "}
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
