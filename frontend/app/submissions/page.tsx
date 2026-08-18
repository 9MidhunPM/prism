"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";

type Submission = {
  id: string;
  student_id: string;
  student_name: string;
  exam_id: string;
  exam_title: string;
  total_score: number;
  status: string;
  created_at: string;
};
export default function SubmissionsPage() {
  const [rows, setRows] = useState<Submission[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .get<Submission[]>("/api/submissions")
      .then(setRows)
      .catch(() => setError("Papers could not be loaded."));
  }, []);
  return (
    <AppShell>
      <section className="mx-auto max-w-6xl">
        <div className="mb-8 border-b border-[var(--line)] pb-7">
          <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
            Papers
          </h1>
          <p className="mt-2 text-sm text-[var(--ink-muted)]">
            Every submitted original remains available for evidence review.
          </p>
        </div>
        {error && (
          <p
            role="alert"
            className="rounded-lg bg-[var(--review-soft)] p-4 text-sm text-[var(--review)]"
          >
            {error}
          </p>
        )}
        <div className="surface-lined overflow-hidden">
          {rows.map((row) => (
            <div
              key={row.id}
              className="flex flex-col justify-between gap-3 border-b border-[var(--line)] p-5 last:border-0 sm:flex-row sm:items-center"
            >
              <div>
                <Link
                  href={`/submissions/${row.id}`}
                  className="font-semibold hover:text-[var(--brand)]"
                >
                  {row.student_name}
                </Link>
                <p className="mt-1 text-sm text-[var(--ink-muted)]">
                  {row.exam_title} ·{" "}
                  {new Date(row.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm">{row.total_score}</span>
                <Link
                  href={`/submissions/${row.id}`}
                  className="button-secondary"
                >
                  Review paper
                </Link>
              </div>
            </div>
          ))}
          {!rows.length && !error && (
            <p className="p-6 text-sm text-[var(--ink-muted)]">
              No submitted papers yet.
            </p>
          )}
        </div>
      </section>
    </AppShell>
  );
}
