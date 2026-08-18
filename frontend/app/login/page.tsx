"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { useSession } from "@/components/session-provider";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useSession();
  const [mode, setMode] = useState<"login" | "setup">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.post(`/api/auth/${mode === "setup" ? "bootstrap" : "login"}`, {
        name: mode === "setup" ? name : undefined,
        email,
        password,
      });
      const account = await refresh();
      if (!account) throw new Error("Your session could not be verified.");
      router.replace(account.role === "student" ? "/student" : "/");
      router.refresh();
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "We could not sign you in. Please try again.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-[var(--background)] px-5 py-8 text-[var(--foreground)] sm:place-items-center">
      <section className="surface page-enter w-full max-w-md p-6 sm:p-8">
        <Link
          href="/"
          className="font-serif text-2xl font-bold tracking-[-0.03em] text-[var(--brand-strong)]"
        >
          PRISM
        </Link>
        <h1 className="mt-7 font-serif text-4xl font-semibold tracking-[-0.035em]">
          {mode === "setup" ? "Set up your account" : "Welcome back"}
        </h1>
        <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">
          {mode === "setup"
            ? "Create the first teacher account for this PRISM workspace."
            : "Sign in to manage examinations and review evidence."}
        </p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          {mode === "setup" && (
            <label className="block text-sm font-medium">
              Name
              <input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="input mt-1 w-full"
                autoComplete="name"
              />
            </label>
          )}
          <label className="block text-sm font-medium">
            Email
            <input
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="input mt-1 w-full"
              autoComplete="email"
            />
          </label>
          <label className="block text-sm font-medium">
            Password
            <input
              required
              minLength={12}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="input mt-1 w-full"
              autoComplete={
                mode === "setup" ? "new-password" : "current-password"
              }
            />
          </label>
          {error && (
            <p className="rounded-lg bg-[var(--review-soft)] p-3 text-sm text-[var(--review)]">
              {error}
            </p>
          )}
          <button
            disabled={saving}
            type="submit"
            className="button-primary w-full py-3"
          >
            {saving
              ? "Please wait"
              : mode === "setup"
                ? "Create teacher account"
                : "Sign in"}
          </button>
        </form>
        <button
          type="button"
          onClick={() => {
            setMode(mode === "setup" ? "login" : "setup");
            setError("");
          }}
          className="button-quiet mt-5 -ml-2"
        >
          {mode === "setup"
            ? "Already have an account? Sign in"
            : "First teacher? Set up the workspace"}
        </button>
      </section>
    </main>
  );
}
