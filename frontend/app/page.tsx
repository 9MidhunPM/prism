"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";

type Submission = {
  id: string;
  student_name: string;
  exam_title: string;
  status: string;
  total_score: number;
  student_id: string;
};
type Dashboard = {
  metrics: {
    active_exams: number;
    total_papers: number;
    completed_papers: number;
    in_progress_papers: number;
    failed_papers: number;
    average_percentage: number;
    required_reviews: number;
    recommended_reviews: number;
  };
  attention: {
    name: string;
    mastery: number;
    required_reviews: number;
    recommended_reviews: number;
  }[];
  submissions: Submission[];
  exams: { id: string; title: string; subject: string }[];
};
type Evaluation = {
  id: string;
  effective_marks: number;
  max_marks: number;
  reason: string;
  question_number: string;
  question_id: string;
  concept: string;
  criterion_title: string;
  review_severity: "review_required" | "review_recommended" | null;
  review_resolved: boolean;
  evidence: { quote: string }[];
};
type ReviewSuggestion = {
  id: string;
  suggested_marks: number;
};
type SubmissionDetail = {
  student_name: string;
  exam_title: string;
  evaluations: Evaluation[];
  review?: ReviewSuggestion;
};

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function statusClass(status: string) {
  if (status === "review_required" || status === "failed")
    return "status-danger";
  if (
    [
      "uploaded",
      "preprocessing",
      "transcribing",
      "structured",
      "grading",
    ].includes(status)
  )
    return "status-neutral";
  return "status-success";
}

export default function Home() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [selected, setSelected] = useState<Submission | null>(null);
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<Dashboard>("/api/dashboard")
      .then(setData)
      .catch(() => setError("Sign in to load your workspace."));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setDetail(null);
    api
      .get<SubmissionDetail>(`/api/submissions/${selected.id}`)
      .then(setDetail);
  }, [selected]);

  const review = async (evaluationId: string) => {
    const item = await api.post<ReviewSuggestion>(
      `/api/evaluations/${evaluationId}/review`,
      {
        comment: "Please reconsider the visual and written evidence.",
      },
    );
    setDetail((current) => (current ? { ...current, review: item } : current));
  };

  const decide = async (decision: "accept" | "reject") => {
    if (!detail?.review || !selected) return;
    await api.post(`/api/reviews/${detail.review.id}/${decision}`);
    const [nextDetail, nextDashboard] = await Promise.all([
      api.get<SubmissionDetail>(`/api/submissions/${selected.id}`),
      api.get<Dashboard>("/api/dashboard"),
    ]);
    setDetail(nextDetail);
    setData(nextDashboard);
  };

  const metrics = data?.metrics;
  return (
    <AppShell
      actions={
        <Link href="/exams/new" className="button-primary">
          Create exam
        </Link>
      }
    >
      <section id="workspace" className="mx-auto max-w-7xl page-enter">
        <div className="mb-8 flex flex-col justify-between gap-5 border-b border-[var(--line)] pb-7 lg:flex-row lg:items-end">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.16em] text-[var(--brand)]">
              Teaching workspace
            </p>
            <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
              Assessment review
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--ink-muted)]">
              The papers that need a decision, the concepts asking for
              attention, and a direct route back to the original evidence.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/assistant" className="button-secondary">
              Ask about class evidence
            </Link>
            <Link href="/exams" className="button-quiet">
              View all exams
            </Link>
          </div>
        </div>
        {error && (
          <p className="mb-5 rounded-lg bg-[var(--review-soft)] p-4 text-sm text-[var(--review)]">
            {error}{" "}
            <Link
              href="/login"
              className="font-medium underline underline-offset-2"
            >
              Open sign in
            </Link>
          </p>
        )}

        <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric
            label="Papers completed"
            value={
              metrics
                ? `${metrics.completed_papers}/${metrics.total_papers}`
                : "-"
            }
            note={
              metrics
                ? `${metrics.in_progress_papers} in progress`
                : "loading workspace"
            }
          />
          <Metric
            label="Class average"
            value={metrics ? `${metrics.average_percentage}%` : "-"}
            note="across evaluated papers"
          />
          <Metric
            label="Review required"
            value={metrics ? String(metrics.required_reviews) : "-"}
            note="blocks paper completion"
            tone="danger"
          />
          <Metric
            label="Review recommended"
            value={metrics ? String(metrics.recommended_reviews) : "-"}
            note="advisory teacher check"
            tone="review"
          />
        </div>

        <div className="mb-7 grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(19rem,.7fr)]">
          <section className="surface-lined overflow-hidden">
            <div className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.13em] text-[var(--ink-muted)]">
                  Attention map
                </p>
                <h2 className="mt-1 font-serif text-2xl font-semibold">
                  Concepts to revisit
                </h2>
              </div>
              <Link href="/classes" className="button-quiet">
                Class insights
              </Link>
            </div>
            <div className="divide-y divide-[var(--line)]">
              {data?.attention.map((item) => (
                <article
                  key={item.name}
                  className="grid gap-3 px-5 py-4 sm:grid-cols-[minmax(0,1fr)_7rem_9rem] sm:items-center"
                >
                  <div>
                    <h3 className="font-medium">{item.name}</h3>
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--surface-muted)]">
                      <div
                        className="h-full rounded-full bg-[var(--brand)]"
                        style={{ width: `${item.mastery}%` }}
                      />
                    </div>
                  </div>
                  <p className="font-mono text-sm text-[var(--ink-muted)]">
                    {item.mastery}% mastery
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {item.required_reviews > 0 && (
                      <span className="status-pill status-danger">
                        {item.required_reviews} required
                      </span>
                    )}
                    {item.recommended_reviews > 0 && (
                      <span className="status-pill status-review">
                        {item.recommended_reviews} advised
                      </span>
                    )}
                    {!item.required_reviews && !item.recommended_reviews && (
                      <span className="text-sm text-[var(--ink-muted)]">
                        No open signals
                      </span>
                    )}
                  </div>
                </article>
              ))}
              {data && data.attention.length === 0 && (
                <p className="p-5 text-sm text-[var(--ink-muted)]">
                  Concept patterns will appear after PRISM evaluates papers.
                </p>
              )}
              {!data && (
                <p className="p-5 text-sm text-[var(--ink-muted)]">
                  Loading concept evidence...
                </p>
              )}
            </div>
          </section>
          <section className="surface bg-[var(--brand)] p-5 text-white">
            <p className="text-xs font-bold uppercase tracking-[0.13em] text-white/65">
              Workspace pulse
            </p>
            <p className="mt-4 font-serif text-4xl font-semibold">
              {metrics ? metrics.active_exams : "-"}
            </p>
            <p className="mt-1 text-sm text-white/75">active assessments</p>
            <div className="mt-7 border-t border-white/20 pt-4 text-sm text-white/80">
              {metrics && metrics.failed_papers > 0
                ? `${metrics.failed_papers} paper${metrics.failed_papers === 1 ? "" : "s"} need processing attention.`
                : "No failed processing jobs in the active workspace."}
            </div>
          </section>
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(19rem,.85fr)_minmax(0,1.15fr)]">
          <section id="exams">
            <div className="mb-3 flex items-baseline justify-between">
              <h2 className="font-serif text-2xl font-semibold tracking-[-0.02em]">
                Recent papers
              </h2>
              <span className="text-sm text-[var(--ink-muted)]">
                Select to inspect
              </span>
            </div>
            <div className="surface-lined overflow-hidden">
              {data?.submissions.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setSelected(item)}
                  className={`flex w-full items-center justify-between gap-3 border-b border-[var(--line)] px-4 py-4 text-left transition-colors duration-150 last:border-0 hover:bg-[var(--surface-muted)] ${selected?.id === item.id ? "bg-[var(--brand-soft)]" : ""}`}
                >
                  <span>
                    <strong className="block text-sm font-semibold">
                      {item.student_name}
                    </strong>
                    <span className="text-sm text-[var(--ink-muted)]">
                      {item.exam_title}
                    </span>
                  </span>
                  <span className="text-right">
                    <strong className="block font-mono text-sm">
                      {item.total_score.toFixed(1)}
                    </strong>
                    <span
                      className={`status-pill mt-1 ${statusClass(item.status)}`}
                    >
                      {statusLabel(item.status)}
                    </span>
                  </span>
                </button>
              ))}
              {!data && (
                <div className="p-5 text-sm text-[var(--ink-muted)]">
                  Loading assessment records...
                </div>
              )}
              {data?.submissions.length === 0 && (
                <div className="p-5 text-sm text-[var(--ink-muted)]">
                  Upload a paper to begin the evidence trail.
                </div>
              )}
            </div>
          </section>
          <ReviewPanel
            submissionId={selected?.id}
            detail={detail}
            onReview={review}
            onDecide={decide}
          />
        </div>
      </section>
    </AppShell>
  );
}

function Metric({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: string;
  note: string;
  tone?: "danger" | "review";
}) {
  const color =
    tone === "danger"
      ? "text-[var(--danger)]"
      : tone === "review"
        ? "text-[var(--review)]"
        : "";
  return (
    <div className="surface p-5">
      <p className="truncate text-sm font-medium text-[var(--ink-muted)]">
        {label}
      </p>
      <p
        className={`my-1 font-serif text-3xl font-semibold tracking-[-0.03em] ${color}`}
      >
        {value}
      </p>
      <p className="text-sm text-[var(--ink-muted)]">{note}</p>
    </div>
  );
}

function ReviewPanel({
  submissionId,
  detail,
  onReview,
  onDecide,
}: {
  submissionId?: string;
  detail: SubmissionDetail | null;
  onReview: (id: string) => void;
  onDecide: (decision: "accept" | "reject") => void;
}) {
  if (!detail)
    return (
      <section className="surface-lined p-7">
        <h2 className="font-serif text-2xl font-semibold">Evidence review</h2>
        <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
          Select a paper to inspect the criterion, source evidence, and the
          teacher-controlled decision.
        </p>
      </section>
    );
  return (
    <section className="surface overflow-hidden">
      <div className="border-b border-[var(--line)] px-5 py-5">
        <p className="text-sm text-[var(--ink-muted)]">{detail.exam_title}</p>
        <h2 className="font-serif text-2xl font-semibold">
          {detail.student_name}
        </h2>
        {submissionId && (
          <Link
            href={`/submissions/${submissionId}`}
            className="button-quiet mt-2 -ml-2"
          >
            Open original paper
          </Link>
        )}
      </div>
      <div className="max-h-[525px] divide-y divide-[var(--line)] overflow-y-auto">
        {detail.evaluations.map((item) => {
          const unresolved = item.review_severity && !item.review_resolved;
          const label =
            item.review_severity === "review_required"
              ? "Review required"
              : item.review_severity === "review_recommended"
                ? "Review advised"
                : item.review_resolved
                  ? "Teacher reviewed"
                  : "High confidence";
          const tone =
            item.review_severity === "review_required"
              ? "status-danger"
              : unresolved
                ? "status-review"
                : "status-success";
          return (
            <article key={item.id} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm text-[var(--ink-muted)]">
                    {item.question_number} · {item.concept}
                  </p>
                  <h3 className="font-medium">{item.criterion_title}</h3>
                </div>
                <strong className="font-mono">
                  {item.effective_marks}/{item.max_marks}
                </strong>
              </div>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
                {item.reason}
              </p>
              <blockquote className="mt-3 border-l border-[var(--line)] pl-3 text-sm italic text-[var(--ink-muted)]">
                “{item.evidence[0]?.quote ?? "No quoted evidence recorded."}”
              </blockquote>
              <div className="mt-3 flex items-center justify-between">
                <span className={`status-pill ${tone}`}>{label}</span>
                <button
                  type="button"
                  onClick={() => onReview(item.id)}
                  className="button-quiet -mr-2"
                >
                  Challenge
                </button>
              </div>
            </article>
          );
        })}
      </div>
      {detail.review && (
        <div className="border-t border-[var(--line)] bg-[var(--review-soft)] p-5">
          <p className="text-sm">
            AI suggests <strong>{detail.review.suggested_marks} marks</strong>.
            This does not change the grade until you decide.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => onDecide("accept")}
              className="button-primary"
            >
              Accept
            </button>
            <button
              type="button"
              onClick={() => onDecide("reject")}
              className="button-secondary"
            >
              Reject
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
