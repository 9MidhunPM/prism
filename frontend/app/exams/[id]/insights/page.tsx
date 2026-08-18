"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API = "/api";

type Concept = Record<string, unknown> & {
  name?: string;
  concept?: string;
  mastery?: number;
  review_rate?: number;
  attempts?: number;
};
type InsightData = Record<string, unknown> & {
  concepts?: Concept[];
  questions?: Record<string, unknown>[];
  criteria?: Record<string, unknown>[];
};
type Exam = {
  id: string;
  title: string;
  subject: string;
  date?: string | null;
  total_marks?: number;
  questions?: unknown[];
};

function metric(data: InsightData, keys: string[]) {
  for (const key of keys)
    if (typeof data[key] === "number") return data[key] as number;
  return null;
}

function percent(value: number | null) {
  return value === null ? "Not available" : `${Math.round(value)}%`;
}

export default function ExamInsightsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [exam, setExam] = useState<Exam | null>(null);
  const [analytics, setAnalytics] = useState<InsightData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    params.then(async ({ id }) => {
      try {
        const [examResponse, analyticsResponse] = await Promise.all([
          fetch(`${API}/exams/${id}`, { credentials: "include" }),
          fetch(`${API}/exams/${id}/analytics`, { credentials: "include" }),
        ]);
        if (!examResponse.ok || !analyticsResponse.ok) throw new Error();
        const [examBody, analyticsBody] = await Promise.all([
          examResponse.json(),
          analyticsResponse.json(),
        ]);
        if (active) {
          setExam(examBody);
          setAnalytics(analyticsBody ?? {});
        }
      } catch {
        if (active)
          setError(
            "This exam's insights could not be loaded. Sign in and try again.",
          );
      } finally {
        if (active) setLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, [params]);

  if (loading)
    return (
      <main className="grid min-h-screen place-items-center bg-[#f5f1e9] text-[#667174]">
        Loading exam insights...
      </main>
    );
  if (error || !exam || !analytics)
    return (
      <main className="min-h-screen bg-[#f5f1e9] p-6 text-[#172126]">
        <div className="mx-auto max-w-xl rounded-lg border border-[#a15130]/25 bg-[#fff4e9] p-7">
          <h1 className="font-serif text-2xl font-semibold">
            Insights unavailable
          </h1>
          <p className="mt-3 text-sm text-[#8b3d20]">
            {error || "This exam could not be found."}
          </p>
          <Link
            href={error ? "/login" : "/exams"}
            className="mt-5 inline-block font-medium text-[#173f4c] underline underline-offset-4"
          >
            {error ? "Open sign in" : "Back to exams"}
          </Link>
        </div>
      </main>
    );

  const concepts = Array.isArray(analytics.concepts)
    ? [...analytics.concepts].sort(
        (a, b) => (a.mastery ?? 0) - (b.mastery ?? 0),
      )
    : [];
  const questions = Array.isArray(analytics.questions)
    ? analytics.questions
    : [];
  const criteria = Array.isArray(analytics.criteria) ? analytics.criteria : [];
  const submissions = metric(analytics, [
    "submission_count",
    "submissions_count",
    "total_submissions",
  ]);
  const averageScore = metric(analytics, ["average_score", "avg_score"]);
  const averagePercentage = metric(analytics, [
    "average_percentage",
    "avg_percentage",
  ]);
  const reviewRate = metric(analytics, ["review_rate", "overall_review_rate"]);

  return (
    <main className="min-h-screen bg-[#f5f1e9] text-[#172126]">
      <header className="border-b border-[#172126]/10 bg-[#fcfaf5] px-5 py-4 sm:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <Link href="/" className="font-serif text-2xl font-bold">
            PRISM
          </Link>
          <div className="flex gap-4 text-sm">
            <Link href="/exams" className="text-[#566164]">
              All exams
            </Link>
            <Link
              href={`/exams/${exam.id}`}
              className="font-medium text-[#173f4c]"
            >
              Open exam
            </Link>
          </div>
        </div>
      </header>
      <section className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
        <p className="text-sm text-[#667174]">Exam insights</p>
        <div className="flex flex-col justify-between gap-4 border-b border-[#172126]/10 pb-7 sm:flex-row sm:items-end">
          <div>
            <h1 className="font-serif text-3xl font-semibold tracking-tight">
              {exam.title}
            </h1>
            <p className="mt-2 text-sm text-[#566164]">
              {exam.subject}
              {exam.date ? ` · ${exam.date}` : ""} ·{" "}
              {exam.questions?.length ?? 0} questions
              {typeof exam.total_marks === "number"
                ? ` · ${exam.total_marks} marks`
                : ""}
            </p>
          </div>
        </div>
        <div className="mt-7 grid gap-px overflow-hidden rounded-lg bg-[#172126]/10 sm:grid-cols-2 lg:grid-cols-4">
          <Metric
            label="Submissions"
            value={submissions === null ? "Not available" : String(submissions)}
          />
          <Metric
            label="Average score"
            value={
              averageScore === null ? "Not available" : String(averageScore)
            }
          />
          <Metric
            label="Average percentage"
            value={percent(averagePercentage)}
          />
          <Metric label="Review rate" value={percent(reviewRate)} />
        </div>
        {concepts.length === 0 &&
          questions.length === 0 &&
          criteria.length === 0 && (
            <section className="mt-7 rounded-lg border border-dashed border-[#172126]/20 bg-[#fcfaf5] p-7">
              <h2 className="font-serif text-xl font-semibold">
                No evaluated data yet
              </h2>
              <p className="mt-2 text-sm text-[#566164]">
                Upload and complete at least one student paper to see concept
                performance and review signals here.
              </p>
              <Link
                href={`/exams/${exam.id}`}
                className="mt-5 inline-block rounded-md bg-[#173f4c] px-4 py-2 text-sm font-medium text-white"
              >
                Upload a paper
              </Link>
            </section>
          )}
        {concepts.length > 0 && (
          <InsightTable
            title="Concept performance"
            rows={concepts}
            name={(row) => String(row.name ?? row.concept ?? "Uncategorized")}
          />
        )}
        {questions.length > 0 && (
          <InsightTable
            title="Question performance"
            rows={questions}
            name={(row) =>
              String(
                row.question_number ?? row.number ?? row.title ?? "Question",
              )
            }
          />
        )}
        {criteria.length > 0 && (
          <InsightTable
            title="Criterion performance"
            rows={criteria}
            name={(row) =>
              String(row.criterion_title ?? row.title ?? "Criterion")
            }
          />
        )}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#fcfaf5] p-5">
      <p className="text-sm text-[#667174]">{label}</p>
      <p className="mt-1 font-serif text-2xl font-semibold">{value}</p>
    </div>
  );
}

function InsightTable({
  title,
  rows,
  name,
}: {
  title: string;
  rows: Record<string, unknown>[];
  name: (row: Record<string, unknown>) => string;
}) {
  return (
    <section className="mt-7">
      <h2 className="mb-3 font-serif text-xl font-semibold">{title}</h2>
      <div className="overflow-hidden rounded-lg border border-[#172126]/10 bg-[#fcfaf5]">
        <div className="grid grid-cols-[1fr_auto_auto] gap-4 border-b border-[#172126]/10 px-5 py-3 text-xs uppercase tracking-wide text-[#667174]">
          <span>Area</span>
          <span>Mastery</span>
          <span>Review rate</span>
        </div>
        {rows.map((row, index) => {
          const mastery =
            typeof row.mastery === "number"
              ? row.mastery
              : typeof row.percentage === "number"
                ? row.percentage
                : null;
          const review =
            typeof row.review_rate === "number" ? row.review_rate : null;
          return (
            <div
              key={`${name(row)}-${index}`}
              className="grid grid-cols-[1fr_auto_auto] gap-4 border-b border-[#172126]/8 px-5 py-4 text-sm last:border-0"
            >
              <span className="min-w-0">
                <strong className="font-medium">{name(row)}</strong>
                {mastery !== null && (
                  <span className="mt-2 block h-1.5 overflow-hidden rounded-full bg-[#172126]/8">
                    <span
                      className="block h-full rounded-full bg-[#173f4c]"
                      style={{
                        width: `${Math.max(0, Math.min(100, mastery))}%`,
                      }}
                    />
                  </span>
                )}
              </span>
              <strong className="font-mono">{percent(mastery)}</strong>
              <span
                className={
                  review !== null && review > 20
                    ? "font-mono text-[#a15130]"
                    : "font-mono text-[#52705b]"
                }
              >
                {percent(review)}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
