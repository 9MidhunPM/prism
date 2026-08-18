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
};

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
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .get<Dashboard>("/api/dashboard")
      .then(setData)
      .catch(() => setError("Sign in to load your workspace."));
  }, []);
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
            <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
              Assessment review
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--ink-muted)]">
              Open a paper to inspect its original evidence, confirm a current
              mark, or make a teacher override.
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
          <p
            role="alert"
            className="mb-5 rounded-lg bg-[var(--review-soft)] p-4 text-sm text-[var(--review)]"
          >
            {error}{" "}
            <Link
              href="/login"
              className="font-medium underline underline-offset-2"
            >
              Open sign in
            </Link>
          </p>
        )}
        <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Metric
            label="Active assessments"
            value={metrics ? String(metrics.active_exams) : "-"}
            note="Available for marking"
          />
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
                : "Loading workspace"
            }
          />
          <Metric
            label="Class average"
            value={metrics ? `${metrics.average_percentage}%` : "-"}
            note="Across evaluated papers"
          />
          <Metric
            label="Review required"
            value={metrics ? String(metrics.required_reviews) : "-"}
            note="Evidence cannot support a mark"
            tone="danger"
          />
          <Metric
            label="Review recommended"
            value={metrics ? String(metrics.recommended_reviews) : "-"}
            note="Optional teacher check"
            tone="review"
          />
        </div>
        <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(22rem,.85fr)]">
          <section className="surface-lined overflow-hidden">
            <div className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4">
              <h2 className="font-serif text-2xl font-semibold">
                Concepts to revisit
              </h2>
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
          <section id="papers" className="min-w-0">
            <div className="mb-3 flex items-baseline justify-between">
              <h2 className="font-serif text-2xl font-semibold tracking-[-0.02em]">
                Recent papers
              </h2>
              <Link href="/submissions" className="button-quiet">
                View all
              </Link>
            </div>
            <div className="surface-lined overflow-hidden">
            {data?.submissions.map((item) => (
              <Link
                key={item.id}
                href={`/submissions/${item.id}`}
                className="flex items-center justify-between gap-3 border-b border-[var(--line)] px-4 py-4 transition-colors duration-150 last:border-0 hover:bg-[var(--surface-muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--brand)]"
              >
                <span className="min-w-0">
                  <strong className="block truncate text-sm font-semibold">
                    {item.student_name}
                  </strong>
                  <span className="block truncate text-sm text-[var(--ink-muted)]">
                    {item.exam_title}
                  </span>
                </span>
                <span className="shrink-0 text-right">
                  <strong className="block font-mono text-sm">
                    {item.total_score.toFixed(1)}
                  </strong>
                  <span
                    className={`status-pill mt-1 ${statusClass(item.status)}`}
                  >
                    {item.status.replaceAll("_", " ")}
                  </span>
                </span>
              </Link>
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
            {metrics && metrics.failed_papers > 0 && (
              <p className="mt-3 text-sm text-[var(--review)]">
                {metrics.failed_papers} paper{metrics.failed_papers === 1 ? "" : "s"} need processing attention.
              </p>
            )}
          </section>
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
