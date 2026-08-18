"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useSession } from "@/components/session-provider";

export function AccountControl() {
  const router = useRouter();
  const { account, logout } = useSession();
  const [loggingOut, setLoggingOut] = useState(false);

  async function signOut() {
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      router.replace("/login");
      router.refresh();
      setLoggingOut(false);
    }
  }

  if (!account) return null;

  return (
    <div className="flex items-center gap-3 text-sm">
      <Link
        href={account.role === "student" ? "/student" : "/"}
        className="hidden text-[#566164] sm:inline"
      >
        {account.name}
      </Link>
      <button
        type="button"
        onClick={signOut}
        disabled={loggingOut}
        className="font-medium text-[#173f4c] underline underline-offset-4 disabled:opacity-60"
      >
        {loggingOut ? "Signing out" : "Sign out"}
      </button>
    </div>
  );
}
