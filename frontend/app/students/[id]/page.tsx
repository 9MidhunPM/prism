"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export default function StudentProfile({ params }: { params: Promise<{ id: string }> }) {
  const [profile, setProfile] = useState<any>(null);
  useEffect(() => { params.then(({ id }) => fetch(`${API}/students/${id}/profile`).then((response) => response.ok ? response.json() : Promise.reject()).then(setProfile)); }, [params]);
  if (!profile) return <main className="min-h-screen bg-[#f5f1e9] p-8 text-[#566164]">Loading student profile...</main>;
  return <main className="min-h-screen bg-[#f5f1e9] text-[#172126]"><header className="border-b border-[#172126]/10 bg-[#fcfaf5] px-5 py-4"><div className="mx-auto flex max-w-4xl justify-between"><Link href="/" className="font-serif text-2xl font-bold">PRISM</Link><span className="text-sm text-[#667174]">Educational evidence only</span></div></header><section className="mx-auto max-w-4xl px-5 py-8"><p className="text-sm text-[#667174]">Student learning profile</p><h1 className="font-serif text-3xl font-semibold">{profile.student.name}</h1><div className="mt-8 rounded-lg border border-[#172126]/10 bg-[#fcfaf5] p-5"><h2 className="font-serif text-xl font-semibold">Concept performance</h2><div className="mt-5 space-y-4">{profile.concepts.map((concept: any) => <div key={concept.concept}><div className="flex justify-between text-sm"><span>{concept.concept}</span><strong className="font-mono">{concept.mastery}%</strong></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-[#172126]/8"><div className="h-full rounded-full bg-[#173f4c]" style={{ width: `${concept.mastery}%` }} /></div></div>)}</div></div><div className="mt-5 grid gap-5 sm:grid-cols-2"><List title="Strengths" items={profile.strengths} empty="No concepts have enough evidence yet." /><List title="Developing concepts" items={profile.developing} empty="No developing concepts identified." /></div></section></main>;
}

function List({ title, items, empty }: { title: string; items: string[]; empty: string }) { return <section className="rounded-lg border border-[#172126]/10 bg-[#fcfaf5] p-5"><h2 className="font-serif text-xl font-semibold">{title}</h2>{items.length ? <ul className="mt-4 space-y-2 text-sm text-[#566164]">{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-4 text-sm text-[#667174]">{empty}</p>}</section>; }
