"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";

const API = "/api";

type Exam = {
  id: string;
  title: string;
  subject: string;
  date?: string | null;
  total_marks?: number;
  questions?: unknown[];
};

export default function ExamsPage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    fetch(`${API}/exams`, { credentials: "include" })
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((body) => {
        if (active) setExams(Array.isArray(body) ? body : []);
      })
      .catch(() => {
        if (active)
          setError(
            "Your assessments could not be loaded. Sign in and try again.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <AppShell
      actions={
        <Link href="/exams/new" className="button-primary">
          Create exam
        </Link>
      }
    >
      <section className="mx-auto max-w-6xl">
        <div className="mb-9 flex flex-col justify-between gap-5 border-b border-[var(--line)] pb-7 sm:flex-row sm:items-end">
          <div>
            <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
              Your exams
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--ink-muted)]">
              Open an assessment to upload papers, review its rubric, or inspect
              class evidence.
            </p>
          </div>
          <p className="text-sm text-[var(--ink-muted)]">
            {exams.length} assessment{exams.length === 1 ? "" : "s"}
          </p>
        </div>
        {loading && (
          <div className="surface-lined p-6 text-sm text-[var(--ink-muted)]">
            Loading assessments...
          </div>
        )}
        {!loading && error && (
          <div
            role="alert"
            className="rounded-lg bg-[var(--review-soft)] p-5 text-sm text-[var(--review)]"
          >
            <p>{error}</p>
            <Link
              href="/login"
              className="mt-3 inline-block font-medium underline underline-offset-2"
            >
              Open sign in
            </Link>
          </div>
        )}
        {!loading && !error && exams.length === 0 && (
          <div className="surface-lined p-8">
            <h2 className="font-serif text-2xl font-semibold">No exams yet</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-[var(--ink-muted)]">
              Create your first assessment and add its marking rubric before
              uploading student papers.
            </p>
            <Link href="/exams/new" className="button-primary mt-5">
              Create exam
            </Link>
          </div>
        )}
        {!loading && !error && exams.length > 0 && (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {exams.map((exam) => (
              <article
                key={exam.id}
                className="surface flex min-h-52 flex-col p-6"
              >
                <p className="text-sm text-[var(--ink-muted)]">
                  {exam.subject}
                  {exam.date ? ` · ${exam.date}` : ""}
                </p>
                <h2 className="mt-2 font-serif text-2xl font-semibold tracking-[-0.02em]">
                  {exam.title}
                </h2>
                <p className="mt-3 text-sm text-[var(--ink-muted)]">
                  {exam.questions?.length ?? 0} questions
                  {typeof exam.total_marks === "number"
                    ? ` · ${exam.total_marks} marks`
                    : ""}
                </p>
                <div className="mt-auto flex flex-wrap gap-3 pt-6 text-sm font-medium">
                  <Link href={`/exams/${exam.id}`} className="button-secondary">
                    Open exam
                  </Link>
                  <Link
                    href={`/exams/${exam.id}/insights`}
                    className="button-quiet"
                  >
                    View insights
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
