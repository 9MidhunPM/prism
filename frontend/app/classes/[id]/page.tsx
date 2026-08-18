"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export default function ClassAnalytics({ params }: { params: Promise<{ id: string }> }) {
  const [analytics, setAnalytics] = useState<any>(null);
  useEffect(() => { params.then(({ id }) => fetch(`${API}/exams/${id}/analytics`).then((response) => response.ok ? response.json() : Promise.reject()).then(setAnalytics)); }, [params]);
  if (!analytics) return <main className="min-h-screen bg-[#f5f1e9] p-8 text-[#566164]">Loading class analytics...</main>;
  const concepts = [...analytics.concepts].sort((a: any, b: any) => a.mastery - b.mastery);
  return <main className="min-h-screen bg-[#f5f1e9] text-[#172126]"><header className="border-b border-[#172126]/10 bg-[#fcfaf5] px-5 py-4"><div className="mx-auto flex max-w-4xl justify-between"><Link href="/" className="font-serif text-2xl font-bold">PRISM</Link><span className="text-sm text-[#667174]">Class evidence</span></div></header><section className="mx-auto max-w-4xl px-5 py-8"><p className="text-sm text-[#667174]">Class intelligence</p><h1 className="font-serif text-3xl font-semibold">Concept mastery</h1><div className="mt-8 overflow-hidden rounded-lg border border-[#172126]/10 bg-[#fcfaf5]"><div className="grid grid-cols-[1fr_auto_auto] gap-4 border-b border-[#172126]/10 px-5 py-3 text-xs uppercase tracking-wide text-[#667174]"><span>Concept</span><span>Mastery</span><span>Review rate</span></div>{concepts.map((concept: any) => <div key={concept.name} className="grid grid-cols-[1fr_auto_auto] gap-4 border-b border-[#172126]/8 px-5 py-4 text-sm last:border-0"><span>{concept.name}<span className="mt-2 block h-1.5 overflow-hidden rounded-full bg-[#172126]/8"><span className="block h-full rounded-full bg-[#173f4c]" style={{ width: `${concept.mastery}%` }} /></span></span><strong className="font-mono">{concept.mastery}%</strong><span className={concept.review_rate > 20 ? "font-mono text-[#a15130]" : "font-mono text-[#52705b]"}>{concept.review_rate}%</span></div>)}</div></section></main>;
}
