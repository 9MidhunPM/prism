"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AccountControl } from "@/components/account-control";
import { api } from "@/lib/api";

type Profile = {
  student: { name: string; identifier: string };
  concepts: { concept: string; mastery: number }[];
  strengths: string[];
  developing: string[];
};
type Submission = {
  id: string;
  exam_title: string;
  subject: string;
  status: string;
  total_score: number;
  created_at: string;
  evaluations: {
    id: string;
    question_number: string;
    criterion_title: string;
    max_marks: number;
    marks: number;
    reason: string;
    needs_review: boolean;
  }[];
};

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

export default function StudentPortal() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [selected, setSelected] = useState<Submission | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.get<Profile>("/api/student/profile"),
      api.get<Submission[]>("/api/student/submissions"),
    ])
      .then(([nextProfile, nextSubmissions]) => {
        setProfile(nextProfile);
        setSubmissions(nextSubmissions);
      })
      .catch(() =>
        setError(
          "Sign in with your student account to view your assessment results.",
        ),
      );
  }, []);

  return (
    <main className="min-h-screen bg-[#f5f1e9] text-[#172126]">
      <header className="border-b border-[#172126]/10 bg-[#fcfaf5] px-5 py-4 sm:px-8">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link href="/student" className="font-serif text-2xl font-bold">
            PRISM
          </Link>
          <div className="flex items-center gap-4">
            <span className="hidden text-sm text-[#566164] sm:inline">
              Your assessment record
            </span>
            <AccountControl />
          </div>
        </div>
      </header>
      <section className="mx-auto max-w-5xl px-5 py-8 sm:px-8">
        {error ? (
          <div className="rounded-lg border border-[#a15130]/25 bg-[#fff4e9] p-5 text-sm text-[#8b3d20]">
            {error}{" "}
            <Link href="/login" className="font-medium underline">
              Sign in
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-8">
              <p className="text-sm text-[#667174]">Student portal</p>
              <h1 className="font-serif text-3xl font-semibold">
                {profile?.student.name ?? "Loading your results..."}
              </h1>
              <p className="mt-2 text-sm text-[#566164]">
                Grades are shown for review. Your teacher remains responsible
                for final assessment decisions.
              </p>
            </div>
            <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
              <section>
                <h2 className="font-serif text-xl font-semibold">
                  Your submissions
                </h2>
                <div className="mt-3 overflow-hidden rounded-lg border border-[#172126]/10 bg-[#fcfaf5]">
                  {submissions.map((submission) => (
                    <button
                      type="button"
                      key={submission.id}
                      onClick={() => setSelected(submission)}
                      className={`block w-full border-b border-[#172126]/8 p-4 text-left last:border-0 hover:bg-[#173f4c]/4 ${selected?.id === submission.id ? "bg-[#173f4c]/7" : ""}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <span>
                          <strong className="block">
                            {submission.exam_title}
                          </strong>
                          <span className="text-sm text-[#667174]">
                            {submission.subject} ·{" "}
                            {new Date(
                              submission.created_at,
                            ).toLocaleDateString()}
                          </span>
                        </span>
                        <span className="text-right">
                          <strong className="block font-mono">
                            {submission.total_score}
                          </strong>
                          <span className="text-xs uppercase tracking-wide text-[#52705b]">
                            {statusLabel(submission.status)}
                          </span>
                        </span>
                      </div>
                    </button>
                  ))}
                  {!submissions.length && (
                    <p className="p-5 text-sm text-[#667174]">
                      No submissions have been shared with your account yet.
                    </p>
                  )}
                </div>
              </section>
              <Result result={selected} />
            </div>
            <section className="mt-8 rounded-lg border border-[#172126]/10 bg-[#fcfaf5] p-5">
              <h2 className="font-serif text-xl font-semibold">
                Learning profile
              </h2>
              <div className="mt-5 grid gap-5 sm:grid-cols-2">
                <ConceptList
                  title="Strengths"
                  items={profile?.strengths ?? []}
                />
                <ConceptList
                  title="Developing concepts"
                  items={profile?.developing ?? []}
                />
              </div>
              {profile?.concepts.map((concept) => (
                <div key={concept.concept} className="mt-4">
                  <div className="flex justify-between text-sm">
                    <span>{concept.concept}</span>
                    <strong className="font-mono">{concept.mastery}%</strong>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#172126]/8">
                    <div
                      className="h-full bg-[#173f4c]"
                      style={{ width: `${concept.mastery}%` }}
                    />
                  </div>
                </div>
              ))}
            </section>
          </>
        )}
      </section>
    </main>
  );
}

function Result({ result }: { result: Submission | null }) {
  if (!result)
    return (
      <section className="rounded-lg border border-dashed border-[#172126]/20 p-5">
        <h2 className="font-serif text-xl font-semibold">Assessment result</h2>
        <p className="mt-2 text-sm text-[#667174]">
          Choose a submission to see criterion-level feedback.
        </p>
      </section>
    );
  return (
    <section className="overflow-hidden rounded-lg border border-[#172126]/10 bg-[#fcfaf5]">
      <div className="border-b border-[#172126]/10 p-5">
        <p className="text-sm text-[#667174]">{result.exam_title}</p>
        <h2 className="font-serif text-2xl font-semibold">
          {result.total_score} marks
        </h2>
      </div>
      <div className="divide-y divide-[#172126]/8">
        {result.evaluations.map((evaluation) => (
          <article key={evaluation.id} className="p-5">
            <div className="flex justify-between gap-4">
              <span>
                <p className="text-sm text-[#667174]">
                  {evaluation.question_number}
                </p>
                <h3 className="font-medium">{evaluation.criterion_title}</h3>
              </span>
              <strong className="font-mono">
                {evaluation.marks}/{evaluation.max_marks}
              </strong>
            </div>
            <p className="mt-2 text-sm leading-6 text-[#566164]">
              {evaluation.reason}
            </p>
            {evaluation.needs_review && (
              <p className="mt-3 text-xs font-medium text-[#a15130]">
                Teacher review recommended
              </p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function ConceptList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-[#566164]">{title}</h3>
      <p className="mt-2 text-sm">
        {items.length
          ? items.join(", ")
          : "No concepts have enough evidence yet."}
      </p>
    </div>
  );
}
