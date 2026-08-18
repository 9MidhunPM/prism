"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { AccountControl } from "@/components/account-control";
import { api } from "@/lib/api";

const items = [
  { href: "/", label: "Workspace", mark: "W" },
  { href: "/classes", label: "Classes", mark: "C" },
  { href: "/exams", label: "Exams", mark: "E" },
  { href: "/submissions", label: "Papers", mark: "P" },
  { href: "/assistant", label: "PRISM Assistant", mark: "A" },
];

function isCurrent(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({
  children,
  actions,
}: {
  children: ReactNode;
  actions?: ReactNode;
}) {
  const pathname = usePathname();
  const [taskCount, setTaskCount] = useState(0);
  useEffect(() => {
    let active = true;
    const load = () =>
      api
        .get<{ items: unknown[] }>("/api/processing-jobs")
        .then((data) => {
          if (active) setTaskCount(data.items.length);
        })
        .catch(() => undefined);
    void load();
    const timer = window.setInterval(load, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <header className="app-header">
        <div className="mx-auto flex h-[4.5rem] max-w-[90rem] items-center justify-between gap-4 px-5 sm:px-8">
          <Link
            href="/"
            className="font-serif text-2xl font-bold tracking-[-0.03em] text-[var(--brand-strong)]"
          >
            PRISM
          </Link>
          <div className="flex items-center gap-2 sm:gap-4">
            {taskCount > 0 && (
              <Link href="/submissions" className="status-pill status-neutral">
                {taskCount} processing
              </Link>
            )}
            {actions}
            <AccountControl />
          </div>
        </div>
      </header>
      <div className="app-frame">
        <aside className="app-sidebar" aria-label="Teacher navigation">
          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--ink-muted)]">
            Teaching
          </p>
          <nav className="space-y-1">
            {items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="app-nav-link"
                aria-current={
                  isCurrent(pathname, item.href) ? "page" : undefined
                }
              >
                <span className="grid h-5 w-5 place-items-center rounded bg-current/10 text-[10px] font-bold">
                  {item.mark}
                </span>
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>
        <main id="main-content" className="app-main page-enter">
          {children}
        </main>
      </div>
      <nav
        className="fixed inset-x-0 bottom-0 z-30 flex justify-around border-t border-[var(--line)] bg-[color-mix(in_srgb,var(--surface)_96%,transparent)] px-3 py-2 backdrop-blur lg:hidden"
        aria-label="Teacher navigation"
      >
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex min-w-16 flex-col items-center gap-1 rounded-md px-3 py-1 text-[11px] font-semibold text-[var(--ink-muted)]"
            aria-current={isCurrent(pathname, item.href) ? "page" : undefined}
          >
            <span className="grid h-5 w-5 place-items-center rounded bg-current/10 text-[10px]">
              {item.mark}
            </span>
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
