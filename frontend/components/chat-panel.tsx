"use client";

import { useState } from "react";

import { sendChat } from "@/lib/api";
import { CopyButton } from "@/components/copy-button";

type ChatResponse = {
  answer: string;
  citations: Array<{ title: string; citation?: string; court?: string; source_url?: string }>;
  sources: Array<{ title: string; excerpt: string; citation?: string; source_url?: string }>;
  disclaimer: string;
};

export function ChatPanel() {
  const [query, setQuery] = useState("Give me case laws for bail in NDPS Act");
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await sendChat({ query });
      setResult(response);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <form onSubmit={handleSubmit} className="rounded-[28px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-card">
        <label className="mb-3 block text-sm font-semibold uppercase tracking-[0.14em] text-forest">Legal Query</label>
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          rows={8}
          className="w-full rounded-3xl border border-[var(--border)] bg-paper px-4 py-4 text-sm outline-none ring-0 transition focus:border-saffron"
        />
        <button
          type="submit"
          disabled={loading}
          className="mt-4 rounded-full bg-forest px-5 py-3 text-sm font-semibold text-paper transition hover:bg-saffron disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Researching..." : "Run legal research"}
        </button>
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      </form>

      <div className="rounded-[28px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-card">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.14em] text-forest">Answer</p>
        {result ? (
          <div className="space-y-6">
            <div className="rounded-3xl border border-[var(--border)] bg-paper p-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-semibold uppercase tracking-[0.12em] text-forest">Research output</p>
                <CopyButton text={result.answer} />
              </div>
              <article className="prose-output whitespace-pre-wrap text-sm leading-7 text-ink">{result.answer}</article>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {result.citations.map((citation) => (
                <div key={`${citation.title}-${citation.citation}`} className="rounded-3xl border border-[var(--border)] bg-paper p-4">
                  <p className="font-semibold">{citation.title}</p>
                  <p className="mt-1 text-sm text-[var(--muted)]">{citation.citation || "Citation unavailable"}</p>
                  <p className="text-sm text-[var(--muted)]">{citation.court || "Court not provided"}</p>
                </div>
              ))}
            </div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted)]">{result.disclaimer}</p>
          </div>
        ) : (
          <p className="text-sm leading-7 text-[var(--muted)]">
            Ask for case laws, principles, or section-wise guidance. The app will retrieve Indian legal materials, send
            them to the model, and return a citation-aware answer.
          </p>
        )}
      </div>
    </section>
  );
}
