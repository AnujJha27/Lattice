"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, Route, Trash2 } from "lucide-react";
import { useCreatePathway, useDeletePathway, usePathways } from "@/hooks/usePathways";
import { PathwayStatusBadge } from "@/components/pathways/PathwayStatusBadge";
import { motion } from "motion/react";
import { StarfieldEmergence } from "@/components/ui/StarfieldEmergence";
import { Reveal } from "@/components/ui/effects";
import { ShimmerRows } from "@/components/ui/Shimmer";
import { SpotlightCard } from "@/components/ui/Spotlight";

const DEPTHS = [
  { value: "beginner", label: "Beginner — start from foundations" },
  { value: "intermediate", label: "Intermediate — assume some background" },
  { value: "advanced", label: "Advanced — go deep, fast" },
] as const;

export default function PathwaysPage() {
  const [topic, setTopic] = useState("");
  const [depth, setDepth] = useState<"beginner" | "intermediate" | "advanced">("beginner");
  const create = useCreatePathway();
  const remove = useDeletePathway();
  const pathways = usePathways();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (topic.trim().length < 3) return;
    await create.mutateAsync({ topic: topic.trim(), target_depth: depth });
    setTopic("");
  }

  const list = pathways.data ?? [];
  const totalConcepts = list.reduce((sum, p) => sum + p.concept_count, 0);
  const readyCount = list.filter((p) => p.status === "READY").length;

  return (
    <div className="relative h-screen overflow-y-auto">

      <div className="relative mx-auto max-w-3xl p-4 sm:p-6 lg:p-14">
        {/* Atlas header */}
        <Reveal>
          <header className="mb-10 text-center">
            <p className="eyebrow mb-4 flex items-center justify-center gap-3">
              <span aria-hidden className="inline-block h-px w-8 bg-[var(--accent)]" />
              Route atlas
              <span aria-hidden className="inline-block h-px w-8 bg-[var(--accent)]" />
            </p>
            <h1 className="atlas-title text-4xl leading-tight">
              Routes through what you want to understand.
            </h1>
            {list.length > 0 && (
              <p className="mt-3 font-mono text-[11px] uppercase tracking-widest text-[var(--text-secondary)]">
                {list.length} charted · {readyCount} ready · {totalConcepts} concepts surveyed
              </p>
            )}
          </header>
        </Reveal>

        {/* Composer */}
        <Reveal delay={0.08}>
          <SpotlightCard>
            <form onSubmit={submit} className="space-y-4 p-6">
              <label htmlFor="topic" className="eyebrow block">
                What do you want to master?
              </label>
              <input
                id="topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. Learn category theory · Understand diffusion models"
                className="w-full rounded-md border border-[var(--border-subtle)] bg-[var(--bg-base)] px-4 py-3 text-sm outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
              />
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <select
                  value={depth}
                  onChange={(e) => setDepth(e.target.value as "beginner" | "intermediate" | "advanced")}
                  aria-label="Target depth"
                  className="flex-1 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
                >
                  {DEPTHS.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
                <button
                  type="submit"
                  disabled={topic.trim().length < 3 || create.isPending}
                  className="btn-brass flex items-center justify-center gap-2 rounded-md px-6 py-2.5 text-sm font-semibold disabled:opacity-50"
                >
                  {create.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
                  Chart a route
                </button>
              </div>
              {create.isError && (
                <p role="alert" className="text-sm text-[var(--danger)]">
                  {(create.error as Error).message}
                </p>
              )}
            </form>
          </SpotlightCard>
        </Reveal>

        {/* List */}
        <div className="mt-8 space-y-3">
          {pathways.isPending ? (
            <ShimmerRows rows={2} rowClassName="h-20" />
          ) : list.length === 0 ? (
            <Reveal delay={0.16}>
              <p className="rounded-xl border border-dashed border-[var(--border-subtle)] p-8 text-center text-sm text-[var(--text-secondary)]">
                No routes charted yet — the atlas is waiting for its first entry.
              </p>
            </Reveal>
          ) : (
            list.map((p, i) => (
              <Reveal key={p.id} delay={0.1 + i * 0.05}>
                <SpotlightCard>
                  {p.status === "GENERATING" && (
                    <StarfieldEmergence className="absolute inset-0 opacity-60" count={12} />
                  )}
                  <div className="flex items-center justify-between gap-4 p-5">
                    <Link href={`/app/pathways/${p.id}`} className="min-w-0 flex-1">
                      <h3 className="atlas-title text-lg transition-colors duration-[var(--duration-fast)] group-hover:text-[var(--accent)]">
                        {p.title}
                      </h3>
                      <p className="mt-1 font-mono text-[11px] uppercase tracking-widest text-[var(--text-muted)]">
                        {p.status === "GENERATING"
                          ? "Decomposing topic · mapping prerequisites"
                        : `${p.concept_count} concepts · ${p.section_count} sections · ${p.target_depth}`}
                      </p>
                    </Link>
                    <div className="flex shrink-0 items-center gap-2">
                      <PathwayStatusBadge status={p.status} />
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete "${p.title}"? Concepts stay in your Brain.`)) {
                            void remove.mutateAsync(p.id);
                          }
                        }}
                        disabled={remove.isPending}
                        aria-label={`Delete pathway ${p.title}`}
                        title="Delete pathway"
                        className="rounded-md p-2 text-[var(--text-muted)] transition-colors duration-[var(--duration-fast)] hover:bg-[rgba(207,102,121,0.12)] hover:text-[var(--danger)] disabled:opacity-50"
                      >
                        <Trash2 className="h-4 w-4" aria-hidden />
                      </button>
                    </div>
                  </div>
                </SpotlightCard>
              </Reveal>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
