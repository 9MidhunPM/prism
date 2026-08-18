"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";

type ClassRow = { id: string; name: string; student_count: number };

export default function ClassesPage() {
  const [classes, setClasses] = useState<ClassRow[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () =>
    api
      .get<ClassRow[]>("/api/classes")
      .then(setClasses)
      .catch(() => setError("Classes could not be loaded. Please try again."));
  useEffect(() => {
    load();
  }, []);

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError("");
    try {
      await api.post("/api/classes", { name: name.trim() });
      setName("");
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Class could not be created.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <section className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col justify-between gap-5 border-b border-[var(--line)] pb-7 sm:flex-row sm:items-end">
          <div>
            <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
              Classes
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--ink-muted)]">
              Build a roster once, assign assessments to it, and follow the
              evidence behind class performance.
            </p>
          </div>
          <span className="status-pill status-neutral">
            {classes.length} active
          </span>
        </div>
        <form
          onSubmit={create}
          className="surface mb-7 flex flex-col gap-3 p-4 sm:flex-row"
        >
          <label className="sr-only" htmlFor="class-name">
            Class name
          </label>
          <input
            id="class-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="input"
            placeholder="e.g. Year 10 Biology"
          />
          <button
            className="button-primary shrink-0"
            disabled={saving}
            type="submit"
          >
            {saving ? "Creating" : "Create class"}
          </button>
        </form>
        {error && (
          <p
            role="alert"
            className="mb-6 rounded-lg bg-[var(--review-soft)] p-4 text-sm text-[var(--review)]"
          >
            {error}
          </p>
        )}
        {classes.length ? (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {classes.map((cohort) => (
              <Link
                key={cohort.id}
                href={`/classes/${cohort.id}`}
                className="surface group p-6 transition-transform duration-150 hover:-translate-y-0.5"
              >
                <p className="text-sm text-[var(--ink-muted)]">
                  {cohort.student_count} student
                  {cohort.student_count === 1 ? "" : "s"}
                </p>
                <h2 className="mt-2 font-serif text-2xl font-semibold tracking-[-0.02em]">
                  {cohort.name}
                </h2>
                <span className="button-quiet mt-6 -ml-2">Open class</span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="surface-lined p-8">
            <h2 className="font-serif text-2xl font-semibold">
              Start with a class roster
            </h2>
            <p className="mt-2 text-sm text-[var(--ink-muted)]">
              Create a class, add students, then connect an exam to see
              meaningful class performance.
            </p>
          </div>
        )}
      </section>
    </AppShell>
  );
}
