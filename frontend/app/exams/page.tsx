"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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
    <main className="min-h-screen bg-[#f5f1e9] text-[#172126]">
      <header className="border-b border-[#172126]/10 bg-[#fcfaf5] px-5 py-4 sm:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <Link href="/" className="font-serif text-2xl font-bold">
            PRISM
          </Link>
          <Link
            href="/exams/new"
            className="rounded-md bg-[#173f4c] px-3 py-2 text-sm font-medium text-white"
          >
            Create exam
          </Link>
        </div>
      </header>
      <section className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
        <div className="mb-8">
          <p className="text-sm text-[#667174]">Assessment library</p>
          <h1 className="font-serif text-3xl font-semibold tracking-tight">
            Your exams
          </h1>
          <p className="mt-2 text-sm text-[#566164]">
            Open an assessment to upload papers, review its rubric, or inspect
            class evidence.
          </p>
        </div>
        {loading && (
          <div className="rounded-lg border border-[#172126]/10 bg-[#fcfaf5] p-6 text-sm text-[#667174]">
            Loading assessments...
          </div>
        )}
        {!loading && error && (
          <div
            role="alert"
            className="rounded-lg border border-[#a15130]/25 bg-[#fff4e9] p-5 text-sm text-[#8b3d20]"
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
          <div className="rounded-lg border border-dashed border-[#172126]/20 bg-[#fcfaf5] p-8">
            <h2 className="font-serif text-xl font-semibold">No exams yet</h2>
            <p className="mt-2 text-sm text-[#566164]">
              Create your first assessment and add its marking rubric before
              uploading student papers.
            </p>
            <Link
              href="/exams/new"
              className="mt-5 inline-block rounded-md bg-[#173f4c] px-4 py-2 text-sm font-medium text-white"
            >
              Create exam
            </Link>
          </div>
        )}
        {!loading && !error && exams.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {exams.map((exam) => (
              <article
                key={exam.id}
                className="flex min-h-52 flex-col rounded-lg border border-[#172126]/10 bg-[#fcfaf5] p-5"
              >
                <p className="text-sm text-[#667174]">
                  {exam.subject}
                  {exam.date ? ` · ${exam.date}` : ""}
                </p>
                <h2 className="mt-2 font-serif text-xl font-semibold">
                  {exam.title}
                </h2>
                <p className="mt-3 text-sm text-[#566164]">
                  {exam.questions?.length ?? 0} questions
                  {typeof exam.total_marks === "number"
                    ? ` · ${exam.total_marks} marks`
                    : ""}
                </p>
                <div className="mt-auto flex flex-wrap gap-3 pt-6 text-sm font-medium">
                  <Link
                    href={`/exams/${exam.id}`}
                    className="text-[#173f4c] underline underline-offset-4"
                  >
                    Open exam
                  </Link>
                  <Link
                    href={`/exams/${exam.id}/insights`}
                    className="text-[#173f4c] underline underline-offset-4"
                  >
                    View insights
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
