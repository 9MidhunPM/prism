"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";

type Student = {
  id: string;
  name: string;
  identifier: string;
  profile?: { concepts: { concept: string; mastery: number }[] };
};
type ClassData = {
  id: string;
  name: string;
  students: Student[];
  exams: { id: string; title: string; subject: string }[];
};
type Analytics = {
  student_count: number;
  submission_count: number;
  average_score: number;
  concepts: { name: string; mastery: number; review_rate: number }[];
  students: Student[];
};

export default function ClassPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [data, setData] = useState<ClassData | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [name, setName] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [error, setError] = useState("");
  const [csv, setCsv] = useState("");
  const load = async (id: string) => {
    const [nextData, nextAnalytics] = await Promise.all([
      api.get<ClassData>(`/api/classes/${id}`),
      api.get<Analytics>(`/api/classes/${id}/analytics`),
    ]);
    setData(nextData);
    setAnalytics(nextAnalytics);
  };
  useEffect(() => {
    params.then(({ id }) =>
      load(id).catch(() => setError("This class could not be loaded.")),
    );
  }, [params]);
  async function addStudent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data || !name.trim() || !identifier.trim()) return;
    try {
      await api.post(`/api/classes/${data.id}/students`, {
        name: name.trim(),
        identifier: identifier.trim(),
      });
      setName("");
      setIdentifier("");
      await load(data.id);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Student could not be added.",
      );
    }
  }
  async function importCsv(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data) return;
    const students = csv
      .split(/\r?\n/)
      .map((line) => line.split(",").map((cell) => cell.trim()))
      .filter((cells) => cells.length >= 2 && cells[0] && cells[1])
      .map(([studentName, studentIdentifier]) => ({
        name: studentName,
        identifier: studentIdentifier,
      }));
    if (!students.length) {
      setError("Paste one student per line as name, identifier.");
      return;
    }
    try {
      await api.post(`/api/classes/${data.id}/students/import`, { students });
      setCsv("");
      await load(data.id);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Roster import failed.",
      );
    }
  }
  if (!data)
    return (
      <AppShell>
        <p className="text-sm text-[var(--ink-muted)]">Loading class...</p>
      </AppShell>
    );
  return (
    <AppShell
      actions={
        <Link href="/exams/new" className="button-primary">
          Create exam
        </Link>
      }
    >
      <section className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col justify-between gap-4 border-b border-[var(--line)] pb-7 sm:flex-row sm:items-end">
          <div>
            <Link
              href="/classes"
              className="text-sm font-semibold text-[var(--brand)]"
            >
              All classes
            </Link>
            <h1 className="mt-2 font-serif text-4xl font-semibold tracking-[-0.035em]">
              {data.name}
            </h1>
          </div>
          <span className="status-pill status-neutral">
            {analytics?.submission_count ?? 0} papers assessed
          </span>
        </div>
        {error && (
          <p
            role="alert"
            className="mb-5 rounded-lg bg-[var(--review-soft)] p-4 text-sm text-[var(--review)]"
          >
            {error}
          </p>
        )}
        <div className="grid gap-6 lg:grid-cols-[1.1fr_.9fr]">
          <section className="surface p-6">
            <h2 className="font-serif text-2xl font-semibold">Roster</h2>
            <form
              onSubmit={addStudent}
              className="mt-5 grid gap-3 sm:grid-cols-[1fr_10rem_auto]"
            >
              <input
                className="input"
                aria-label="Student name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Student name"
              />
              <input
                className="input"
                aria-label="Student identifier"
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                placeholder="Identifier"
              />
              <button className="button-primary" type="submit">
                Add student
              </button>
            </form>
            <div className="mt-5 divide-y divide-[var(--line)]">
              {data.students.map((student) => (
                <Link
                  key={student.id}
                  href={`/students/${student.id}`}
                  className="flex items-center justify-between py-3 text-sm hover:text-[var(--brand)]"
                >
                  <span className="font-semibold">{student.name}</span>
                  <span className="font-mono text-xs text-[var(--ink-muted)]">
                    {student.identifier}
                  </span>
                </Link>
              ))}
            </div>
          </section>
          <section className="surface-lined p-6">
            <h2 className="font-serif text-2xl font-semibold">Import roster</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
              Paste CSV rows as <code>name, identifier</code>.
            </p>
            <form onSubmit={importCsv} className="mt-4">
              <textarea
                className="input min-h-36"
                value={csv}
                onChange={(event) => setCsv(event.target.value)}
                placeholder="Arun Patel, STU-001\nMaya Chen, STU-002"
              />
              <button className="button-secondary mt-3" type="submit">
                Import students
              </button>
            </form>
          </section>
        </div>
        <section className="mt-7">
          <h2 className="font-serif text-2xl font-semibold">
            Class performance
          </h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <Metric
              label="Students"
              value={String(analytics?.student_count ?? 0)}
            />
            <Metric
              label="Papers"
              value={String(analytics?.submission_count ?? 0)}
            />
            <Metric
              label="Average score"
              value={String(analytics?.average_score ?? 0)}
            />
          </div>
          {analytics?.concepts.length ? (
            <div className="surface-lined mt-5 divide-y divide-[var(--line)]">
              {analytics.concepts.map((concept) => (
                <div
                  key={concept.name}
                  className="grid grid-cols-[1fr_auto] gap-4 p-5"
                >
                  <div>
                    <strong>{concept.name}</strong>
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--surface-muted)]">
                      <div
                        className="h-full bg-[var(--brand)]"
                        style={{ width: `${concept.mastery}%` }}
                      />
                    </div>
                  </div>
                  <span className="font-mono text-sm">{concept.mastery}%</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-5 text-sm text-[var(--ink-muted)]">
              Performance will appear after assessed papers are uploaded.
            </p>
          )}
        </section>
      </section>
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface p-5">
      <p className="text-sm text-[var(--ink-muted)]">{label}</p>
      <p className="mt-1 font-serif text-3xl font-semibold">{value}</p>
    </div>
  );
}
