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
  pending_reviews: number;
  submissions: Submission[];
  exams: { id: string; title: string; subject: string }[];
};

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

export default function Home() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [selected, setSelected] = useState<Submission | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<Dashboard>("/api/dashboard")
      .then(setData)
      .catch(() => setError("Sign in to load your workspace."));
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.get(`/api/submissions/${selected.id}`).then(setDetail);
  }, [selected]);

  const review = async (evaluationId: string) => {
    const item = await api.post(`/api/evaluations/${evaluationId}/review`, {
      comment: "Please reconsider the visual and written evidence.",
    });
    setDetail((current: any) => ({ ...current, review: item }));
  };

  const decide = async (decision: "accept" | "reject") => {
    if (!detail?.review) return;
    await api.post(`/api/reviews/${detail.review.id}/${decision}`);
    setDetail(await api.get(`/api/submissions/${selected?.id}`));
  };

  return (
    <AppShell
      actions={
        <Link href="/exams/new" className="button-primary">
          Create exam
        </Link>
      }
    >
      <section id="workspace" className="mx-auto max-w-6xl">
        <div className="mb-9 flex flex-col justify-between gap-4 border-b border-[var(--line)] pb-7 sm:flex-row sm:items-end">
          <div>
            <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
              Assessment review
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--ink-muted)]">
              A review queue built around the original paper, the rubric, and
              your final decision.
            </p>
          </div>
          <Link href="/assistant" className="button-secondary">
            Ask about class evidence
          </Link>
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
        <div className="mb-9 grid gap-4 md:grid-cols-3">
          <Metric
            label="Pending review"
            value={data ? String(data.pending_reviews) : "-"}
            note="criteria need attention"
          />
          <Metric
            label="Completed papers"
            value={
              data
                ? String(
                    data.submissions.filter((item) => item.status !== "failed")
                      .length,
                  )
                : "-"
            }
            note="in the current cohort"
          />
          <Metric
            label="Live model"
            value="Luna"
            note="structured evaluation"
          />
        </div>
        <div className="grid gap-6 xl:grid-cols-[minmax(18rem,.85fr)_minmax(0,1.15fr)]">
          <section id="exams">
            <div className="mb-3 flex items-baseline justify-between">
              <h2 className="font-serif text-2xl font-semibold tracking-[-0.02em]">
                Recent submissions
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
                    <strong className="block text-base font-semibold sm:text-sm">
                      {item.student_name}
                    </strong>
                    <span className="text-sm text-[var(--ink-muted)]">
                      {item.exam_title}
                    </span>
                  </span>
                  <span className="text-right">
                    <strong className="block font-mono text-base sm:text-sm">
                      {item.total_score.toFixed(1)}
                    </strong>
                    <span
                      className={`status-pill mt-1 ${item.status === "review_required" ? "status-review" : "status-success"}`}
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
            </div>
          </section>
          <ReviewPanel detail={detail} onReview={review} onDecide={decide} />
        </div>
      </section>
    </AppShell>
  );
}

function Metric({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="surface p-5">
      <p className="truncate text-sm font-medium text-[var(--ink-muted)]">
        {label}
      </p>
      <p className="my-1 font-serif text-3xl font-semibold tracking-[-0.03em]">
        {value}
      </p>
      <p className="text-sm text-[var(--ink-muted)]">{note}</p>
    </div>
  );
}

function ReviewPanel({
  detail,
  onReview,
  onDecide,
}: {
  detail: any;
  onReview: (id: string) => void;
  onDecide: (decision: "accept" | "reject") => void;
}) {
  if (!detail)
    return (
      <section className="surface-lined p-7">
        <h2 className="font-serif text-2xl font-semibold">Evidence review</h2>
        <p className="mt-2 text-base text-[var(--ink-muted)] sm:text-sm">
          Select a submission to inspect criterion-level evidence and request a
          teacher-controlled re-evaluation.
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
      </div>
      <div className="max-h-[525px] divide-y divide-[var(--line)] overflow-y-auto">
        {detail.evaluations.map((item: any) => (
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
              “{item.evidence[0]?.quote}”
            </blockquote>
            <div className="mt-3 flex items-center justify-between">
              <span
                className={
                  item.needs_review
                    ? "status-pill status-review"
                    : "status-pill status-success"
                }
              >
                {item.needs_review ? "Review recommended" : "High confidence"}
              </span>
              <button
                type="button"
                onClick={() => onReview(item.id)}
                className="button-quiet -mr-2"
              >
                Challenge
              </button>
            </div>
          </article>
        ))}
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
