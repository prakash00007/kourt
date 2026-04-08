"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { loginUser, signupUser } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

type Mode = "login" | "signup";

type LoginFormProps = {
  initialMode?: Mode;
};

export function LoginForm({ initialMode = "login" }: LoginFormProps) {
  const router = useRouter();

  const { setToken } = useAuth();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response =
        mode === "login"
          ? await loginUser({ email, password })
          : await signupUser({ email, password, tier: "free" });
      setToken(response.access_token);
      router.push("/draft");
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Unable to authenticate right now.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-2xl rounded-[28px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-card">
      <div className="mb-6 flex gap-2">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
            mode === "login" ? "bg-forest text-paper" : "border border-[var(--border)] text-forest"
          }`}
        >
          Login
        </button>
        <button
          type="button"
          onClick={() => setMode("signup")}
          className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
            mode === "signup" ? "bg-forest text-paper" : "border border-[var(--border)] text-forest"
          }`}
        >
          Sign Up
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="mb-2 block text-sm font-semibold uppercase tracking-[0.14em] text-forest">Email</label>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-3xl border border-[var(--border)] bg-paper px-4 py-3 text-sm outline-none focus:border-saffron"
            placeholder="you@example.com"
            required
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold uppercase tracking-[0.14em] text-forest">Password</label>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-3xl border border-[var(--border)] bg-paper px-4 py-3 text-sm outline-none focus:border-saffron"
            placeholder="Minimum 8 characters"
            minLength={8}
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="rounded-full bg-forest px-5 py-3 text-sm font-semibold text-paper transition hover:bg-saffron disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Please wait..." : mode === "login" ? "Login" : "Create account"}
        </button>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
      </form>
    </section>
  );
}
