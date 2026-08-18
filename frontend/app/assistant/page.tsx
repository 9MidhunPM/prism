"use client";

import { useState } from "react";
import { AppShell } from "@/components/app-shell";

const API = "/api";

export default function AssistantPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function ask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    const response = await fetch(`${API}/assistant/query`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const body = await response.json().catch(() => null);
    if (!response.ok)
      setError(body?.detail ?? "The question could not be answered.");
    else setResult(body);
    setLoading(false);
  }
  return (
    <AppShell>
      <section className="mx-auto max-w-3xl">
        <div className="border-b border-[var(--line)] pb-7">
          <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
            Ask about assessment evidence
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">
            PRISM retrieves relevant assessment data first. It does not use a
            general chatbot context.
          </p>
        </div>
        <form
          onSubmit={ask}
          className="surface mt-7 flex flex-col gap-3 p-4 sm:flex-row"
        >
          <input
            aria-label="Assessment question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            className="input"
            placeholder="What should I revise tomorrow?"
          />
          <button
            type="submit"
            disabled={loading}
            className="button-primary shrink-0"
          >
            {loading ? "Checking..." : "Ask"}
          </button>
        </form>
        {error && (
          <p
            role="alert"
            className="mt-4 rounded-lg bg-[var(--review-soft)] p-4 text-sm text-[var(--review)]"
          >
            {error}
          </p>
        )}
        {result && (
          <section className="surface mt-6 p-6">
            <p className="text-sm leading-7 text-[var(--ink-muted)]">
              {result.answer}
            </p>
            {result.sources?.length > 0 && (
              <div className="mt-5 border-t border-[var(--line)] pt-4">
                <h2 className="text-sm font-medium">Retrieved evidence</h2>
                <ul className="mt-2 space-y-1 text-sm text-[var(--ink-muted)]">
                  {result.sources.map((source: any) => (
                    <li key={source.name}>
                      {source.name}: {source.mastery}% mastery
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
      </section>
    </AppShell>
  );
}
