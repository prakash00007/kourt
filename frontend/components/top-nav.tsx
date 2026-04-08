"use client";

import Link from "next/link";
import { Scale } from "lucide-react";

const links = [
  { href: "/", label: "Overview" },
  { href: "/chat", label: "Research Chat" },
  { href: "/upload", label: "Judgment Summary" },
  { href: "/draft", label: "Draft Generator" }
];

export function TopNav() {
  return (
    <nav className="mb-8 flex flex-col gap-4 rounded-[28px] border border-[var(--border)] bg-[var(--card)] px-5 py-4 shadow-card backdrop-blur md:flex-row md:items-center md:justify-between">
      <Link href="/" className="flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-forest text-paper">
          <Scale className="h-5 w-5" />
        </span>
        <div>
          <p className="font-display text-2xl font-semibold">Kourt</p>
          <p className="text-sm text-[var(--muted)]">AI Copilot for Indian lawyers</p>
        </div>
      </Link>
      <div className="flex flex-wrap gap-2">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href as any}
            className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium transition hover:border-forest hover:bg-forest hover:text-paper"
          >
            {link.label}
          </Link>
        ))}
        <Link
          href={"/draft" as any}
          className="rounded-full bg-forest px-4 py-2 text-sm font-medium text-paper transition hover:bg-saffron"
        >
          Open Workspace
        </Link>
      </div>
    </nav>
  );
}
