"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AccountControl } from "@/components/account-control";
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
    <main className="min-h-screen bg-[#f5f1e9] text-[#172126]">
      <header className="border-b border-[#172126]/10 bg-[#fcfaf5] px-5 py-4 sm:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <span className="font-serif text-2xl font-bold tracking-tight">
              PRISM
            </span>
            <span className="ml-3 hidden border-l border-[#172126]/15 pl-3 text-sm text-[#566164] sm:inline">
              Assessment intelligence
            </span>
          </div>
          <div className="flex items-center gap-4">
            <AccountControl />
            <Link
              href="/exams/new"
              className="rounded-md bg-[#173f4c] px-3 py-2 text-sm font-medium text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#173f4c]"
            >
              Create exam
            </Link>
          </div>
        </div>
      </header>
      <div className="mx-auto grid max-w-7xl lg:grid-cols-[210px_1fr]">
        <aside className="hidden border-r border-[#172126]/10 px-4 py-7 lg:block">
          <nav className="space-y-1 text-sm">
            <a
              className="block rounded-md bg-[#173f4c]/8 px-3 py-2 text-[#173f4c]"
              href="#workspace"
            >
              Workspace
            </a>
            <Link
              className="block rounded-md px-3 py-2 text-[#566164] hover:bg-[#173f4c]/5"
              href="/exams"
            >
              Exams
            </Link>
            {data?.exams[0] ? (
              <Link
                className="block rounded-md px-3 py-2 text-[#566164] hover:bg-[#173f4c]/5"
                href={`/exams/${data.exams[0].id}/insights`}
              >
                Class insights
              </Link>
            ) : (
              <span
                className="block cursor-not-allowed rounded-md px-3 py-2 text-[#667174]"
                aria-disabled="true"
              >
                Class insights
              </span>
            )}
          </nav>
        </aside>
        <section id="workspace" className="min-w-0 px-5 py-7 sm:px-8">
          <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="mb-1 text-sm text-[#667174]">Teaching workspace</p>
              <h1 className="font-serif text-3xl font-semibold tracking-tight">
                Assessment review
              </h1>
            </div>
            <p className="text-base text-[#566164] sm:text-sm">
              Evidence-backed marks. Teacher-approved decisions.
            </p>
          </div>
          {error && (
            <p className="mb-5 rounded-md border border-[#a15130]/25 bg-[#fff4e9] p-3 text-sm text-[#8b3d20]">
              {error}{" "}
              <Link
                href="/login"
                className="font-medium underline underline-offset-2"
              >
                Open sign in
              </Link>
            </p>
          )}
          <div className="@container mb-8 grid gap-px overflow-hidden rounded-lg bg-[#172126]/10 sm:grid-cols-3">
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
                      data.submissions.filter(
                        (item) => item.status !== "failed",
                      ).length,
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
          <div className="grid gap-6 xl:grid-cols-[1fr_1.15fr]">
            <section id="exams">
              <div className="mb-3 flex items-baseline justify-between">
                <h2 className="font-serif text-xl font-semibold">
                  Recent submissions
                </h2>
                <span className="text-sm text-[#667174]">
                  Select to inspect
                </span>
              </div>
              <div className="overflow-hidden rounded-lg border border-[#172126]/10 bg-[#fcfaf5]">
                {data?.submissions.map((item) => (
                  <button
                    type="button"
                    key={item.id}
                    onClick={() => setSelected(item)}
                    className={`flex w-full items-center justify-between gap-3 border-b border-[#172126]/8 px-4 py-4 text-left last:border-0 hover:bg-[#173f4c]/4 ${selected?.id === item.id ? "bg-[#173f4c]/7" : ""}`}
                  >
                    <span>
                      <strong className="block text-base font-medium sm:text-sm">
                        {item.student_name}
                      </strong>
                      <span className="text-sm text-[#667174]">
                        {item.exam_title}
                      </span>
                    </span>
                    <span className="text-right">
                      <strong className="block font-mono text-base sm:text-sm">
                        {item.total_score.toFixed(1)}
                      </strong>
                      <span
                        className={`text-xs uppercase tracking-wider ${item.status === "review_required" ? "text-[#a15130]" : "text-[#52705b]"}`}
                      >
                        {statusLabel(item.status)}
                      </span>
                    </span>
                  </button>
                ))}
                {!data && (
                  <div className="p-5 text-sm text-[#667174]">
                    Loading assessment records...
                  </div>
                )}
              </div>
            </section>
            <ReviewPanel detail={detail} onReview={review} onDecide={decide} />
          </div>
        </section>
      </div>
    </main>
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
    <div className="bg-[#fcfaf5] p-5">
      <p className="truncate text-sm text-[#667174]">{label}</p>
      <p className="my-1 font-serif text-3xl font-semibold">{value}</p>
      <p className="text-sm text-[#667174]">{note}</p>
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
      <section className="rounded-lg border border-dashed border-[#172126]/20 p-6">
        <h2 className="font-serif text-xl font-semibold">Evidence review</h2>
        <p className="mt-2 text-base text-[#667174] sm:text-sm">
          Select a submission to inspect criterion-level evidence and request a
          teacher-controlled re-evaluation.
        </p>
      </section>
    );
  return (
    <section className="overflow-hidden rounded-lg border border-[#172126]/10 bg-[#fcfaf5]">
      <div className="border-b border-[#172126]/10 px-5 py-4">
        <p className="text-sm text-[#667174]">{detail.exam_title}</p>
        <h2 className="font-serif text-xl font-semibold">
          {detail.student_name}
        </h2>
      </div>
      <div className="max-h-[525px] divide-y divide-[#172126]/8 overflow-y-auto">
        {detail.evaluations.map((item: any) => (
          <article key={item.id} className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-[#667174]">
                  {item.question_number} · {item.concept}
                </p>
                <h3 className="font-medium">{item.criterion_title}</h3>
              </div>
              <strong className="font-mono">
                {item.effective_marks}/{item.max_marks}
              </strong>
            </div>
            <p className="mt-2 text-sm leading-6 text-[#566164]">
              {item.reason}
            </p>
            <blockquote className="mt-3 border-l-2 border-[#c29b54] pl-3 text-sm italic text-[#566164]">
              “{item.evidence[0]?.quote}”
            </blockquote>
            <div className="mt-3 flex items-center justify-between">
              <span
                className={
                  item.needs_review
                    ? "text-xs font-medium text-[#a15130]"
                    : "text-xs font-medium text-[#52705b]"
                }
              >
                {item.needs_review ? "Review recommended" : "High confidence"}
              </span>
              <button
                type="button"
                onClick={() => onReview(item.id)}
                className="text-sm font-medium text-[#173f4c] underline underline-offset-4"
              >
                Challenge
              </button>
            </div>
          </article>
        ))}
      </div>
      {detail.review && (
        <div className="border-t border-[#c29b54]/30 bg-[#fff8e8] p-4">
          <p className="text-sm">
            AI suggests <strong>{detail.review.suggested_marks} marks</strong>.
            This does not change the grade until you decide.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => onDecide("accept")}
              className="rounded-md bg-[#173f4c] px-3 py-2 text-sm text-white"
            >
              Accept
            </button>
            <button
              type="button"
              onClick={() => onDecide("reject")}
              className="rounded-md border border-[#173f4c]/20 px-3 py-2 text-sm text-[#173f4c]"
            >
              Reject
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
