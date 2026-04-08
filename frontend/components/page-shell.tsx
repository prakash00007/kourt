import { ReactNode } from "react";

type PageShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
};

export function PageShell({ eyebrow, title, description, children }: PageShellProps) {
  return (
    <main className="space-y-8">
      <section className="grid gap-8 rounded-[36px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-card lg:grid-cols-[1.1fr_0.9fr] lg:p-10">
        <div className="space-y-4">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-saffron">{eyebrow}</p>
          <h1 className="max-w-3xl font-display text-4xl font-semibold leading-tight md:text-6xl">{title}</h1>
          <p className="max-w-2xl text-base leading-8 text-[var(--muted)] md:text-lg">{description}</p>
        </div>
        <div className="rounded-[28px] border border-[var(--border)] bg-paper/90 p-6">
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-forest">MVP Focus</p>
          <div className="space-y-4 text-sm leading-7 text-[var(--muted)]">
            <p>Built only for research, judgment summarization, and legal draft generation.</p>
            <p>Uses RAG with Indian legal data so responses can cite real materials instead of guessing.</p>
            <p>Every output carries a professional disclaimer to support responsible lawyer review.</p>
          </div>
        </div>
      </section>
      {children}
    </main>
  );
}
