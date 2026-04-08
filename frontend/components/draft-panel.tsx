"use client";

import { useState } from "react";

import { generateDraft } from "@/lib/api";
import { CopyButton } from "@/components/copy-button";

type DraftResponse = {
  title: string;
  draft: string;
  disclaimer: string;
};

export function DraftPanel() {
  const [draftType, setDraftType] = useState("Bail application");
  const [details, setDetails] = useState(
    "Draft bail application for NDPS case. Accused is 24 years old, no prior criminal record, in custody for 90 days, recovery is 8 grams, charge sheet not filed yet."
  );
  const [result, setResult] = useState<DraftResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await generateDraft({ draft_type: draftType, details });
      setResult(response);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
      <form onSubmit={handleSubmit} className="rounded-[28px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-card">
        <label className="mb-3 block text-sm font-semibold uppercase tracking-[0.14em] text-forest">Draft Type</label>
        <input
          value={draftType}
          onChange={(event) => setDraftType(event.target.value)}
          className="w-full rounded-3xl border border-[var(--border)] bg-paper px-4 py-3 text-sm outline-none focus:border-saffron"
        />
        <label className="mb-3 mt-5 block text-sm font-semibold uppercase tracking-[0.14em] text-forest">Case Details</label>
        <textarea
          value={details}
          onChange={(event) => setDetails(event.target.value)}
          rows={10}
          className="w-full rounded-3xl border border-[var(--border)] bg-paper px-4 py-4 text-sm outline-none focus:border-saffron"
        />
        <button
          type="submit"
          disabled={loading}
          className="mt-4 rounded-full bg-forest px-5 py-3 text-sm font-semibold text-paper transition hover:bg-saffron disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Drafting..." : "Generate draft"}
        </button>
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      </form>

      <div className="rounded-[28px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-card">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.14em] text-forest">Generated Draft</p>
        {result ? (
          <div className="space-y-4">
            <div className="rounded-3xl border border-[var(--border)] bg-paper p-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="font-semibold">{result.title}</p>
                <CopyButton text={result.draft} />
              </div>
              <pre className="whitespace-pre-wrap font-sans text-sm leading-7 text-[var(--muted)]">{result.draft}</pre>
            </div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted)]">{result.disclaimer}</p>
          </div>
        ) : (
          <p className="text-sm leading-7 text-[var(--muted)]">
            Generate practical first drafts for bail applications, notices, petitions, and other repeatable legal documents.
          </p>
        )}
      </div>
    </section>
  );
}
