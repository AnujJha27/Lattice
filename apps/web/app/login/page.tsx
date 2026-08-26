"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { NebulaSky } from "@/components/ui/NebulaSky";
import { ShimmerText } from "@/components/ui/Spotlight";

type Mode = "magic-link" | "password";

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();
  const [mode, setMode] = useState<Mode>("magic-link");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signInWithGoogle() {
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
    if (error) setError(error.message);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      if (mode === "magic-link") {
        const { error } = await supabase.auth.signInWithOtp({
          email,
          options: { emailRedirectTo: `${location.origin}/auth/callback` },
        });
        if (error) throw error;
        setSent(true);
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        router.push("/app");
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden p-6">
      <NebulaSky starCount={800} />

      <div className="relative z-10 w-full max-w-md">
        {/* Atlas entry */}
        <div className="mb-10 text-center">
          <p className="eyebrow mb-4">Personal observatory · est. tonight</p>
          <h1 className="atlas-title text-5xl leading-tight">
            <ShimmerText>Lattice</ShimmerText>
          </h1>
          <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-[var(--text-secondary)]">
            A star chart for what you know. Every idea a point of light;
            mastery is how brightly it burns.
          </p>
        </div>

        <div
          className="glass rounded-xl border border-[var(--border-subtle)] p-8 shadow-[var(--shadow-lg)]"
        >
          {sent ? (
            <div className="space-y-4 text-center" role="status">
              <p className="text-sm text-[var(--text-primary)]">
                Check your inbox — a sign-in link is on its way to{" "}
                <strong>{email}</strong>.
              </p>
              <button
                onClick={() => {
                  setSent(false);
                  setEmail("");
                }}
                className="eyebrow underline-offset-4 hover:underline"
              >
                Use a different address
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={signInWithGoogle}
                disabled={pending}
                className="mb-6 flex w-full items-center justify-center gap-3 rounded-md border border-[var(--border-strong)] bg-transparent px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] transition-colors duration-[var(--duration-fast)] hover:bg-[var(--accent-muted)] disabled:opacity-50"
              >
                Continue with Google
              </button>

              <div className="relative mb-6">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-dashed border-[var(--border-subtle)]" />
                </div>
                <div className="relative flex justify-center">
                  <span className="eyebrow bg-[var(--bg-surface)] px-3">or</span>
                </div>
              </div>

              <form onSubmit={submit} className="space-y-3">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  aria-label="Email address"
                  className="w-full rounded-md border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3.5 py-2.5 font-body text-sm outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
                />
                {mode === "password" && (
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Password"
                    aria-label="Password"
                    className="w-full rounded-md border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3.5 py-2.5 text-sm outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
                  />
                )}
                <button
                  type="submit"
                  disabled={pending}
                  className="btn-brass w-full rounded-md px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
                >
                  {pending ? "…" : mode === "magic-link" ? "Send a sign-in link" : "Sign in"}
                </button>
              </form>

              <div className="mt-5 flex justify-between text-xs text-[var(--text-secondary)]">
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    setMode(mode === "magic-link" ? "password" : "magic-link");
                  }}
                  className="underline-offset-4 hover:underline"
                >
                  {mode === "magic-link" ? "Use a password instead" : "Email me a link instead"}
                </a>
              </div>
            </>
          )}

          {error && (
            <p role="alert" className="mt-4 text-center text-sm text-[var(--danger)]">
              {error}
            </p>
          )}
        </div>

        <p className="mt-8 text-center font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--text-muted)]">
          Your knowledge · charted · cited · yours
        </p>
      </div>
    </main>
  );
}
