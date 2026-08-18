"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LegacyClassInsights({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();

  useEffect(() => {
    params.then(({ id }) => router.replace(`/exams/${id}/insights`));
  }, [params, router]);

  return <main className="grid min-h-screen place-items-center bg-[#f5f1e9] text-[#566164]">Opening exam insights…</main>;
}
