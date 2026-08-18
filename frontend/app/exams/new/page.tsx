"use client";

import Link from "next/link";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

type Criterion = { title: string; description: string; max_marks: string; concept: string };
type Question = { number: string; text: string; criteria: Criterion[] };

const blankCriterion = (): Criterion => ({ title: "", description: "", max_marks: "1", concept: "" });
const blankQuestion = (number: number): Question => ({ number: `Q${number}`, text: "", criteria: [blankCriterion()] });

export default function NewExamPage() {
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [date, setDate] = useState("");
  const [questions, setQuestions] = useState<Question[]>([blankQuestion(1)]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [createdId, setCreatedId] = useState("");

  const updateQuestion = (index: number, field: "number" | "text", value: string) => setQuestions((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item));
  const updateCriterion = (questionIndex: number, criterionIndex: number, field: keyof Criterion, value: string) => setQuestions((items) => items.map((question, itemIndex) => itemIndex !== questionIndex ? question : { ...question, criteria: question.criteria.map((criterion, index) => index === criterionIndex ? { ...criterion, [field]: value } : criterion) }));
  const questionTotal = (question: Question) => question.criteria.reduce((total, criterion) => total + (Number(criterion.max_marks) || 0), 0);
  const total = questions.reduce((sum, question) => sum + questionTotal(question), 0);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!title.trim() || !subject.trim() || questions.some((question) => !question.text.trim() || question.criteria.some((criterion) => !criterion.title.trim() || !criterion.description.trim() || !criterion.concept.trim() || Number(criterion.max_marks) <= 0))) {
      setError("Complete the exam details, every question, and every rubric criterion before saving.");
      return;
    }
    setSaving(true);
    try {
      const response = await fetch(`${API}/exams`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, subject, date: date || null, questions: questions.map((question) => ({ ...question, criteria: question.criteria.map((criterion) => ({ ...criterion, max_marks: Number(criterion.max_marks) })) })) }) });
      if (!response.ok) throw new Error("The exam could not be saved.");
      const exam = await response.json();
      setCreatedId(exam.id);
    } catch {
      setError("The exam could not be saved. Check that the PRISM API is running and try again.");
    } finally {
      setSaving(false);
    }
  }

  if (createdId) return <main className="min-h-screen bg-[#f5f1e9] px-5 py-12 text-[#172126] sm:px-8"><div className="mx-auto max-w-xl rounded-lg border border-[#173f4c]/15 bg-[#fcfaf5] p-8"><p className="text-sm font-medium text-[#52705b]">Exam saved</p><h1 className="mt-2 font-serif text-3xl font-semibold">Your rubric is ready.</h1><p className="mt-3 text-[#566164]">PRISM will use these criteria as the source of truth when student papers are uploaded.</p><Link className="mt-6 inline-block rounded-md bg-[#173f4c] px-4 py-2 text-sm font-medium text-white" href={`/exams/${createdId}`}>View exam</Link></div></main>;

  return <main className="min-h-screen bg-[#f5f1e9] text-[#172126]"><header className="border-b border-[#172126]/10 bg-[#fcfaf5] px-5 py-4 sm:px-8"><div className="mx-auto flex max-w-5xl items-center justify-between"><Link href="/" className="font-serif text-2xl font-bold">PRISM</Link><Link href="/" className="text-sm text-[#566164] underline underline-offset-4">Back to workspace</Link></div></header><form onSubmit={submit} className="mx-auto max-w-5xl px-5 py-8 sm:px-8"><div className="mb-8 flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="text-sm text-[#667174]">Exam setup</p><h1 className="font-serif text-3xl font-semibold">Create an assessment</h1></div><strong className="font-mono text-lg">{total} marks</strong></div>{error && <p className="mb-6 rounded-md border border-[#a15130]/25 bg-[#fff4e9] p-3 text-sm text-[#8b3d20]">{error}</p>}<section className="mb-6 grid gap-4 rounded-lg border border-[#172126]/10 bg-[#fcfaf5] p-5 sm:grid-cols-3"><Field label="Exam title"><input name="title" value={title} onChange={(event) => setTitle(event.target.value)} className="input" placeholder="Machine Learning Foundations" /></Field><Field label="Subject"><input name="subject" value={subject} onChange={(event) => setSubject(event.target.value)} className="input" placeholder="Computer Science" /></Field><Field label="Assessment date"><input name="date" type="date" value={date} onChange={(event) => setDate(event.target.value)} className="input" /></Field></section><div className="space-y-5">{questions.map((question, questionIndex) => <section key={questionIndex} className="rounded-lg border border-[#172126]/10 bg-[#fcfaf5] p-5"><div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div className="grid gap-3 sm:grid-cols-[100px_1fr]"><Field label="Number"><input name={`question-number-${questionIndex}`} value={question.number} onChange={(event) => updateQuestion(questionIndex, "number", event.target.value)} className="input" /></Field><Field label="Question"><input name={`question-text-${questionIndex}`} value={question.text} onChange={(event) => updateQuestion(questionIndex, "text", event.target.value)} className="input" placeholder="What should the student explain?" /></Field></div><span className="font-mono text-sm text-[#566164]">{questionTotal(question)} marks</span></div><div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="border-b border-[#172126]/10 text-[#667174]"><tr><th className="pb-2 font-medium">Criterion</th><th className="pb-2 font-medium">Description</th><th className="pb-2 font-medium">Concept</th><th className="pb-2 text-right font-medium">Marks</th></tr></thead><tbody>{question.criteria.map((criterion, criterionIndex) => <tr key={criterionIndex} className="border-b border-[#172126]/8 last:border-0"><td className="py-2 pr-2"><input name={`criterion-title-${questionIndex}-${criterionIndex}`} value={criterion.title} onChange={(event) => updateCriterion(questionIndex, criterionIndex, "title", event.target.value)} className="input" placeholder="Correct definition" /></td><td className="py-2 pr-2"><input name={`criterion-description-${questionIndex}-${criterionIndex}`} value={criterion.description} onChange={(event) => updateCriterion(questionIndex, criterionIndex, "description", event.target.value)} className="input" placeholder="What evidence earns marks?" /></td><td className="py-2 pr-2"><input name={`criterion-concept-${questionIndex}-${criterionIndex}`} value={criterion.concept} onChange={(event) => updateCriterion(questionIndex, criterionIndex, "concept", event.target.value)} className="input" placeholder="Optimization" /></td><td className="py-2"><input name={`criterion-marks-${questionIndex}-${criterionIndex}`} type="number" min="0.5" step="0.5" value={criterion.max_marks} onChange={(event) => updateCriterion(questionIndex, criterionIndex, "max_marks", event.target.value)} className="input w-20 text-right" /></td></tr>)}</tbody></table></div><button type="button" onClick={() => setQuestions((items) => items.map((item, index) => index === questionIndex ? { ...item, criteria: [...item.criteria, blankCriterion()] } : item))} className="mt-4 text-sm font-medium text-[#173f4c] underline underline-offset-4">Add criterion</button></section>)}</div><div className="mt-6 flex flex-col justify-between gap-4 border-t border-[#172126]/10 pt-5 sm:flex-row sm:items-center"><button type="button" onClick={() => setQuestions((items) => [...items, blankQuestion(items.length + 1)])} className="self-start text-sm font-medium text-[#173f4c] underline underline-offset-4">Add question</button><button type="submit" disabled={saving} className="rounded-md bg-[#173f4c] px-4 py-2 text-sm font-medium text-white disabled:opacity-60">{saving ? "Saving exam..." : "Save exam and rubric"}</button></div></form></main>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="grid gap-1 text-sm font-medium text-[#566164]"><span>{label}</span>{children}</label>; }
