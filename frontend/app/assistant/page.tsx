"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";

type Mention = {
  type: "student" | "class" | "exam" | "paper";
  id: string;
  label: string;
  secondary_label: string;
  href: string;
};
type Result = {
  answer: string;
  sources: { name: string; mastery: number }[];
  resolved_mentions: Mention[];
};

export default function AssistantPage() {
  const [question, setQuestion] = useState("");
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [suggestions, setSuggestions] = useState<Mention[]>([]);
  const [activeSuggestion, setActiveSuggestion] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const mentionQuery = question.match(/(?:^|\s)@([^\s@]*)$/)?.[1] ?? "";

  useEffect(() => {
    if (!question.includes("@")) {
      setSuggestions([]);
      return;
    }
    const timer = window.setTimeout(() => {
      api
        .get<{ items: Mention[] }>(
          `/api/assistant/mentions?q=${encodeURIComponent(mentionQuery)}`,
        )
        .then((data) => {
          setSuggestions(data.items);
          setActiveSuggestion(0);
        })
        .catch(() => setSuggestions([]));
    }, 150);
    return () => window.clearTimeout(timer);
  }, [mentionQuery, question]);

  function choose(item: Mention) {
    setMentions((current) =>
      current.some(
        (mention) => mention.type === item.type && mention.id === item.id,
      )
        ? current
        : [...current, item],
    );
    setQuestion((current) => current.replace(/(?:^|\s)@[^\s@]*$/, " "));
    setSuggestions([]);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }

  async function ask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      setResult(
        await api.post<Result>("/api/assistant/query", {
          question,
          mentions: mentions.map(({ type, id }) => ({ type, id })),
        }),
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "PRISM could not answer that question.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <section className="mx-auto max-w-4xl">
        <div className="border-b border-[var(--line)] pb-7">
          <h1 className="font-serif text-4xl font-semibold tracking-[-0.035em]">
            Ask PRISM
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            Type <strong>@</strong> to connect a visible student, class, exam,
            or paper. PRISM uses only the selected records and active assessment
            data.
          </p>
        </div>
        <form onSubmit={ask} className="surface relative mt-7 p-4">
          <div className="flex flex-wrap gap-2">
            {mentions.map((mention) => (
              <span
                key={`${mention.type}-${mention.id}`}
                className="status-pill bg-[var(--brand-soft)] text-[var(--brand-strong)]"
              >
                {mention.type}: {mention.label}
                <button
                  type="button"
                  aria-label={`Remove ${mention.label}`}
                  onClick={() =>
                    setMentions((current) =>
                      current.filter(
                        (item) =>
                          item.id !== mention.id || item.type !== mention.type,
                      ),
                    )
                  }
                >
                  x
                </button>
              </span>
            ))}
          </div>
          <input
            ref={inputRef}
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={suggestions.length > 0}
            aria-controls="mention-options"
            aria-activedescendant={
              suggestions[activeSuggestion]
                ? `mention-${suggestions[activeSuggestion].type}-${suggestions[activeSuggestion].id}`
                : undefined
            }
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (!suggestions.length) return;
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setActiveSuggestion((current) =>
                  Math.min(current + 1, suggestions.length - 1),
                );
              }
              if (event.key === "ArrowUp") {
                event.preventDefault();
                setActiveSuggestion((current) => Math.max(current - 1, 0));
              }
              if (event.key === "Escape") setSuggestions([]);
              if (event.key === "Enter" && suggestions[activeSuggestion]) {
                event.preventDefault();
                choose(suggestions[activeSuggestion]);
              }
            }}
            className="input mt-3"
            placeholder="Why did @Maya lose marks on Q3?"
          />
          {suggestions.length > 0 && (
            <div
              id="mention-options"
              role="listbox"
              className="absolute inset-x-4 top-[calc(100%-0.25rem)] z-20 overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--surface)] shadow-[var(--shadow)]"
            >
              {suggestions.map((item, index) => (
                <button
                  key={`${item.type}-${item.id}`}
                  id={`mention-${item.type}-${item.id}`}
                  role="option"
                  aria-selected={index === activeSuggestion}
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(item)}
                  className={`block w-full px-4 py-3 text-left text-sm ${index === activeSuggestion ? "bg-[var(--brand-soft)]" : "hover:bg-[var(--surface-muted)]"}`}
                >
                  <strong>{item.label}</strong>
                  <span className="ml-2 text-[var(--ink-muted)]">
                    {item.secondary_label}
                  </span>
                </button>
              ))}
            </div>
          )}
          <div className="mt-3 flex justify-end">
            <button type="submit" disabled={loading} className="button-primary">
              {loading ? "PRISM is checking..." : "Ask PRISM"}
            </button>
          </div>
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
            {result.resolved_mentions.length > 0 && (
              <div className="mt-5 border-t border-[var(--line)] pt-4">
                <h2 className="text-sm font-semibold">Connected records</h2>
                <div className="mt-2 flex flex-wrap gap-2">
                  {result.resolved_mentions.map((mention) => (
                    <Link
                      key={`${mention.type}-${mention.id}`}
                      href={mention.href}
                      className="button-secondary"
                    >
                      {mention.label}
                    </Link>
                  ))}
                </div>
              </div>
            )}
            {result.sources?.length > 0 && (
              <div className="mt-5 border-t border-[var(--line)] pt-4">
                <h2 className="text-sm font-semibold">
                  Assessment evidence used
                </h2>
                <ul className="mt-2 space-y-1 text-sm text-[var(--ink-muted)]">
                  {result.sources.map((source) => (
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
