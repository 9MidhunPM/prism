"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export default function LoginPage() {
  const router = useRouter();
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
    const response = await fetch(
      `${API}/auth/${mode === "setup" ? "bootstrap" : "login"}`,
      {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: mode === "setup" ? name : undefined,
          email,
          password,
        }),
      },
    );
    if (response.ok) {
      const account = await response.json();
      router.replace(account.role === "student" ? "/student" : "/");
      router.refresh();
    } else {
      const body = await response.json().catch(() => null);
      setError(body?.detail ?? "We could not sign you in. Please try again.");
    }
    setSaving(false);
  }

  return (
    <main className="grid min-h-screen bg-[#f5f1e9] px-5 py-8 text-[#172126] sm:place-items-center">
      <section className="w-full max-w-md rounded-lg border border-[#173f4c]/15 bg-[#fcfaf5] p-6 shadow-[0_18px_50px_rgba(23,63,76,0.08)] sm:p-8">
        <Link href="/" className="font-serif text-2xl font-bold">
          PRISM
        </Link>
        <p className="mt-6 text-sm font-medium text-[#173f4c]">
          Teacher workspace
        </p>
        <h1 className="mt-1 font-serif text-3xl font-semibold">
          {mode === "setup" ? "Set up your account" : "Welcome back"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-[#566164]">
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
            <p className="rounded-md bg-[#fff4e9] p-3 text-sm text-[#8b3d20]">
              {error}
            </p>
          )}
          <button
            disabled={saving}
            type="submit"
            className="w-full rounded-md bg-[#173f4c] px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60"
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
          className="mt-5 text-sm text-[#173f4c] underline underline-offset-4"
        >
          {mode === "setup"
            ? "Already have an account? Sign in"
            : "First teacher? Set up the workspace"}
        </button>
      </section>
    </main>
  );
}
