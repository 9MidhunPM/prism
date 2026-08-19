"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AccountControl } from "@/components/account-control";
import { useSession } from "@/components/session-provider";
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
  total_marks: number;
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
  const { account, refresh } = useSession();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    if (!account || account.must_change_password) return;
    let cancelled = false;
    setError("");
    Promise.all([
      api.get<Profile>("/api/student/profile"),
      api.get<Submission[]>("/api/student/submissions"),
    ])
      .then(([nextProfile, nextSubmissions]) => {
        if (cancelled) return;
        setProfile(nextProfile);
        setSubmissions(nextSubmissions);
      })
      .catch(() => {
        if (!cancelled) setError("Your assessment results could not be loaded. Please try again.");
      });
    return () => {
      cancelled = true;
    };
  }, [account?.id, account?.must_change_password]);
  async function changePassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await api.post("/api/auth/change-password", { current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Your password could not be updated.");
    }
  }

  return (
    <main className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <header className="border-b border-[var(--line)] bg-[var(--surface)] px-5 py-4 sm:px-8">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link
            href="/student"
            className="font-serif text-2xl font-bold tracking-[-0.03em] text-[var(--brand-strong)]"
          >
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
          <div className="rounded-lg bg-[var(--review-soft)] p-5 text-sm text-[var(--review)]">
            {error}{" "}
            <Link href="/login" className="font-medium underline">
              Sign in
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-8 border-b border-[var(--line)] pb-7">
              <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
                {profile?.student.name ?? account?.name ?? "Loading your results..."}
              </h1>
              <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">
                Grades are shown for review. Your teacher remains responsible
                for final assessment decisions.
              </p>
            </div>
            {account?.must_change_password && (
              <section className="surface mb-6 max-w-2xl p-5">
                <h2 className="font-serif text-2xl font-semibold">Choose your password</h2>
                <p className="mt-2 text-sm text-[var(--ink-muted)]">Your teacher set a temporary password. Replace it before continuing.</p>
                <form onSubmit={changePassword} className="mt-4 grid gap-3 sm:grid-cols-2">
                  <input className="input" type="password" minLength={12} required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} placeholder="Temporary password" />
                  <input className="input" type="password" minLength={12} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="New password" />
                  <button className="button-primary sm:col-span-2 sm:justify-self-start" type="submit">Update password</button>
                </form>
              </section>
            )}
            <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
              <section>
                <h2 className="font-serif text-2xl font-semibold">
                  Your submissions
                </h2>
                <div className="surface-lined mt-3 overflow-hidden">
                  {submissions.map((submission) => (
                    <button
                      type="button"
                      key={submission.id}
                      onClick={() => setSelected(submission)}
                      className={`block w-full border-b border-[var(--line)] p-4 text-left transition-colors last:border-0 hover:bg-[var(--surface-muted)] ${selected?.id === submission.id ? "bg-[var(--brand-soft)]" : ""}`}
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
                            {submission.total_score}/{submission.total_marks}
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
            <section className="surface mt-8 p-5">
              <h2 className="font-serif text-2xl font-semibold">
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
                      className="h-full bg-[var(--brand)] transition-[width] duration-300"
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
      <section className="surface-lined p-5">
        <h2 className="font-serif text-2xl font-semibold">Assessment result</h2>
        <p className="mt-2 text-sm text-[var(--ink-muted)]">
          Choose a submission to see criterion-level feedback.
        </p>
      </section>
    );
  return (
    <section className="surface overflow-hidden">
      <div className="border-b border-[var(--line)] p-5">
        <p className="text-sm text-[var(--ink-muted)]">{result.exam_title}</p>
        <h2 className="font-serif text-2xl font-semibold">
          {result.total_score}/{result.total_marks} marks
        </h2>
      </div>
      <div className="divide-y divide-[var(--line)]">
        {result.evaluations.map((evaluation) => (
          <article key={evaluation.id} className="p-5">
            <div className="flex justify-between gap-4">
              <span>
                <p className="text-sm text-[var(--ink-muted)]">
                  {evaluation.question_number}
                </p>
                <h3 className="font-medium">{evaluation.criterion_title}</h3>
              </span>
              <strong className="font-mono">
                {evaluation.marks}/{evaluation.max_marks}
              </strong>
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
              {evaluation.reason}
            </p>
            {evaluation.needs_review && (
              <p className="mt-3 text-xs font-medium text-[var(--review)]">
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
