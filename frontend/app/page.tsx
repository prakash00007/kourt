import Link from "next/link";

import { PageShell } from "@/components/page-shell";

const features = [
  {
    href: "/chat",
    title: "Legal Research Chat",
    description: "Ask legal questions in plain English and get Indian case references with a short practical explanation."
  },
  {
    href: "/upload",
    title: "Judgment Summarization",
    description: "Upload long judgments and convert them into facts, issues, judgment, and key takeaways."
  },
  {
    href: "/draft",
    title: "Draft Generator",
    description: "Turn a rough matter brief into a formatted first draft with heading, facts, grounds, and prayer."
  }
];

export default function HomePage() {
  return (
    <PageShell
      eyebrow="MVP for lawyers"
      title="An AI copilot built for Indian legal work, not generic chat."
      description="This MVP is designed for solo practitioners, small firms, and district court lawyers who need faster research, better judgment summaries, and reliable draft starting points."
    >
      <section className="grid gap-5 md:grid-cols-3">
        {features.map((feature) => (
          <Link
            key={feature.href}
            href={feature.href as any}
            className="rounded-[28px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-card transition hover:-translate-y-1"
          >
            <p className="font-display text-3xl font-semibold">{feature.title}</p>
            <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{feature.description}</p>
          </Link>
        ))}
      </section>
    </PageShell>
  );
}
