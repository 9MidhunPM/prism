"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";

type Profile = {
  student: {
    id: string;
    name: string;
    identifier: string;
    classes: { id: string; name: string }[];
  };
  concepts: { concept: string; mastery: number }[];
  strengths: string[];
  developing: string[];
  submissions: {
    id: string;
    exam_title: string;
    subject: string;
    total_marks: number;
    score: number;
    percentage: number;
    status: string;
    created_at: string;
    href: string;
  }[];
};

export default function StudentProfile({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    params.then(({ id }) =>
      api
        .get<Profile>(`/api/students/${id}/profile`)
        .then(setProfile)
        .catch((reason) =>
          setError(
            reason instanceof Error
              ? reason.message
              : "Student profile could not be loaded.",
          ),
        ),
    );
  }, [params]);
  if (!profile)
    return (
      <AppShell>
        <p
          role={error ? "alert" : "status"}
          className="text-sm text-[var(--ink-muted)]"
        >
          {error || "Loading student profile..."}
        </p>
      </AppShell>
    );
  return (
    <AppShell>
      <section className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col justify-between gap-4 border-b border-[var(--line)] pb-7 sm:flex-row sm:items-end">
          <div>
            <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
              {profile.student.name}
            </h1>
            <p className="mt-2 text-sm text-[var(--ink-muted)]">
              {profile.student.identifier}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {profile.student.classes.map((cohort) => (
              <Link
                key={cohort.id}
                href={`/classes/${cohort.id}`}
                className="button-secondary"
              >
                {cohort.name}
              </Link>
            ))}
          </div>
        </div>
        <div className="grid gap-6 lg:grid-cols-[.8fr_1.2fr]">
          <section className="surface p-6">
            <h2 className="font-serif text-2xl font-semibold">
              Concept performance
            </h2>
            <div className="mt-5 space-y-4">
              {profile.concepts.map((concept) => (
                <div key={concept.concept}>
                  <div className="flex justify-between text-sm">
                    <span>{concept.concept}</span>
                    <strong className="font-mono">{concept.mastery}%</strong>
                  </div>
                  <div
                    role="progressbar"
                    aria-label={`${concept.concept} mastery`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={concept.mastery}
                    className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--surface-muted)]"
                  >
                    <div
                      className="h-full bg-[var(--brand)]"
                      style={{ width: `${concept.mastery}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <List title="Strengths" items={profile.strengths} />
              <List title="Developing" items={profile.developing} />
            </div>
          </section>
          <section className="surface overflow-hidden">
            <div className="border-b border-[var(--line)] p-6">
              <h2 className="font-serif text-2xl font-semibold">
                Uploaded papers
              </h2>
              <p className="mt-1 text-sm text-[var(--ink-muted)]">
                Open any paper to inspect its source images and evidence.
              </p>
            </div>
            <div className="divide-y divide-[var(--line)]">
              {profile.submissions.map((paper) => (
                <Link
                  key={paper.id}
                  href={paper.href}
                  className="flex items-center justify-between gap-4 p-5 hover:bg-[var(--surface-muted)]"
                >
                  <span>
                    <strong className="block">{paper.exam_title}</strong>
                    <span className="text-sm text-[var(--ink-muted)]">
                      {paper.subject} ·{" "}
                      {new Date(paper.created_at).toLocaleDateString()}
                    </span>
                  </span>
                  <span className="text-right">
                    <strong className="font-mono">
                      {paper.score}/{paper.total_marks}
                    </strong>
                    <span className="mt-1 block text-xs text-[var(--ink-muted)]">
                      {paper.percentage}% · {paper.status.replaceAll("_", " ")}
                    </span>
                  </span>
                </Link>
              ))}
              {!profile.submissions.length && (
                <p className="p-6 text-sm text-[var(--ink-muted)]">
                  No active papers are available for this student.
                </p>
              )}
            </div>
          </section>
        </div>
      </section>
    </AppShell>
  );
}
function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h2 className="text-sm font-semibold text-[var(--ink-muted)]">{title}</h2>
      <p className="mt-2 text-sm">
        {items.length ? items.join(", ") : "No evidence yet."}
      </p>
    </div>
  );
}
