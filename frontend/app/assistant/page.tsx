"use client";

import Link from "next/link";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export default function AssistantPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  async function ask(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); if (!question.trim()) return; setLoading(true); const response = await fetch(`${API}/assistant/query`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) }); setResult(await response.json()); setLoading(false); }
  return <main className="min-h-screen bg-[#f5f1e9] text-[#172126]"><header className="border-b border-[#172126]/10 bg-[#fcfaf5] px-5 py-4"><div className="mx-auto flex max-w-3xl justify-between"><Link href="/" className="font-serif text-2xl font-bold">PRISM</Link><span className="text-sm text-[#667174]">Grounded assessment chat</span></div></header><section className="mx-auto max-w-3xl px-5 py-8"><p className="text-sm text-[#667174]">Teacher assistant</p><h1 className="font-serif text-3xl font-semibold">Ask about assessment evidence</h1><p className="mt-2 text-sm text-[#566164]">PRISM retrieves relevant assessment data first. It does not use a general chatbot context.</p><form onSubmit={ask} className="mt-6 flex gap-3"><input aria-label="Assessment question" value={question} onChange={(event) => setQuestion(event.target.value)} className="input" placeholder="What should I revise tomorrow?" /><button type="submit" disabled={loading} className="rounded-md bg-[#173f4c] px-4 py-2 text-sm font-medium text-white">{loading ? "Checking..." : "Ask"}</button></form>{result && <section className="mt-6 rounded-lg border border-[#172126]/10 bg-[#fcfaf5] p-5"><p className="text-sm leading-6 text-[#566164]">{result.answer}</p>{result.sources?.length > 0 && <div className="mt-5 border-t border-[#172126]/10 pt-4"><h2 className="text-sm font-medium">Retrieved evidence</h2><ul className="mt-2 space-y-1 text-sm text-[#566164]">{result.sources.map((source: any) => <li key={source.name}>{source.name}: {source.mastery}% mastery</li>)}</ul></div>}</section>}</section></main>;
}
