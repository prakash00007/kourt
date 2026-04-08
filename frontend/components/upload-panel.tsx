"use client";

import { useState } from "react";

import { uploadJudgment } from "@/lib/api";

type UploadResponse = {
  file_name: string;
  summary: {
    facts: string;
    issues: string;
    judgment: string;
    key_takeaways: string;
  };
  disclaimer: string;
};

export function UploadPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Please choose a judgment PDF.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await uploadJudgment(file);
      setResult(response);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
      <form onSubmit={handleSubmit} className="rounded-[28px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-card">
        <label className="mb-3 block text-sm font-semibold uppercase tracking-[0.14em] text-forest">Upload Judgment PDF</label>
        <input
          type="file"
          accept="application/pdf"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
          className="w-full rounded-3xl border border-[var(--border)] bg-paper px-4 py-4 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="mt-4 rounded-full bg-forest px-5 py-3 text-sm font-semibold text-paper transition hover:bg-saffron disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Summarizing..." : "Generate summary"}
        </button>
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      </form>

      <div className="rounded-[28px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-card">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.14em] text-forest">Structured Summary</p>
        {result ? (
          <div className="grid gap-4 md:grid-cols-2">
            {Object.entries(result.summary).map(([key, value]) => (
              <div key={key} className="rounded-3xl border border-[var(--border)] bg-paper p-5">
                <p className="mb-2 font-semibold capitalize">{key.replace("_", " ")}</p>
                <p className="text-sm leading-7 text-[var(--muted)]">{value}</p>
              </div>
            ))}
            <p className="md:col-span-2 text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted)]">{result.disclaimer}</p>
          </div>
        ) : (
          <p className="text-sm leading-7 text-[var(--muted)]">
            Upload a Supreme Court or High Court judgment PDF. The backend extracts text, cleans it, and returns a lawyer-friendly
            summary with facts, issues, judgment, and key takeaways.
          </p>
        )}
      </div>
    </section>
  );
}
