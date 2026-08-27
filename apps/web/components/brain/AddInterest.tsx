"use client";

import { useState } from "react";
import { useAddInterest } from "@/hooks/useBrain";
import { Loader2, Plus } from "lucide-react";
import { ApiError } from "@/lib/api";

export function AddInterest({ onAdded }: { onAdded?: () => void }) {
  const [name, setName] = useState("");
  const addInterest = useAddInterest();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    await addInterest.mutateAsync({ name: name.trim() });
    setName("");
    onAdded?.();
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <label
          htmlFor="interest-name"
          className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]"
        >
          What do you want to understand?
        </label>
        <input
          id="interest-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Spectral graph theory"
          className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3.5 py-2.5 text-sm outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
        />
      </div>
      <p className="text-xs text-[var(--text-muted)]">We&apos;ll classify the domain automatically.</p>
      <button
        type="submit"
        disabled={!name.trim() || addInterest.isPending}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors duration-[var(--duration-fast)] hover:bg-[var(--accent-hover)] disabled:opacity-50"
      >
        {addInterest.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Plus className="h-4 w-4" aria-hidden />
        )}
        Add to my Brain
      </button>
      {addInterest.error instanceof ApiError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {addInterest.error.message}
        </p>
      )}
    </form>
  );
}
