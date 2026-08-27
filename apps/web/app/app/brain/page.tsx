"use client";

import dynamic from "next/dynamic";
import { List, Network } from "lucide-react";
import { BrainListView } from "@/components/brain/BrainListView";
import { Inspector } from "@/components/brain/Inspector";
import { AddInterest } from "@/components/brain/AddInterest";
import { useBrainStore } from "@/lib/store/brain";
import { useBrainGraph, useCombineConcepts } from "@/hooks/useBrain";
import { Loader2, Sparkles, X } from "lucide-react";
import { motion } from "motion/react";

// Sigma.js touches WebGL globals at import time — browser-only.
const BrainCanvas = dynamic(
  () => import("@/components/brain/BrainCanvas").then((m) => m.BrainCanvas),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center" aria-busy="true">
        <p className="text-sm text-[var(--text-secondary)]">Loading canvas…</p>
      </div>
    ),
  },
);

export default function BrainPage() {
  const viewMode = useBrainStore((s) => s.viewMode);
  const setViewMode = useBrainStore((s) => s.setViewMode);
  const selectedId = useBrainStore((s) => s.selectedId);
  const domainFilter = useBrainStore((s) => s.domainFilter);
  const setDomainFilter = useBrainStore((s) => s.setDomainFilter);
  const combineMode = useBrainStore((s) => s.combineMode);
  const combinePicks = useBrainStore((s) => s.combinePicks);
  const toggleCombine = useBrainStore((s) => s.toggleCombine);
  const { data: graphData } = useBrainGraph();
  const combine = useCombineConcepts();

  const domains = [...new Set((graphData?.nodes ?? []).map((n) => n.domain).filter(Boolean))] as string[];

  return (
    <div className="relative flex h-[calc(100vh-4rem)] flex-col md:h-screen">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border-subtle)] px-3 py-2.5 sm:gap-3 sm:px-5">
        <h1 className="atlas-title text-base sm:text-lg">My Brain</h1>
        <span className="hidden font-mono text-[10px] uppercase tracking-widest text-[var(--text-muted)] sm:inline">
          {graphData?.nodes.length ?? 0} concepts · {graphData?.edges.length ?? 0} connections
        </span>

        {/* Domain filter */}
        <div className="order-3 flex w-full flex-nowrap items-center gap-1.5 overflow-x-auto pb-0.5 sm:order-none sm:w-auto sm:flex-wrap" role="group" aria-label="Filter by domain">
          <FilterChip active={!domainFilter} onClick={() => setDomainFilter(null)}>
            All
          </FilterChip>
          {domains.slice(0, 6).map((domain) => (
            <FilterChip
              key={domain}
              active={domainFilter === domain}
              onClick={() => setDomainFilter(domainFilter === domain ? null : domain)}
            >
              {domain}
            </FilterChip>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1" role="group" aria-label="View mode">
          <button
            onClick={() => setViewMode("graph")}
            aria-pressed={viewMode === "graph"}
            aria-label="Graph view"
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors ${
              viewMode === "graph"
                ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            <Network className="h-3.5 w-3.5" aria-hidden /> Graph
          </button>
          <button
            onClick={() => setViewMode("list")}
            aria-pressed={viewMode === "list"}
            aria-label="List view (accessible)"
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors ${
              viewMode === "list"
                ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            <List className="h-3.5 w-3.5" aria-hidden /> List
          </button>
        </div>

        {/* Combine mode */}
        <button
          onClick={toggleCombine}
          aria-pressed={combineMode}
          className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors duration-[var(--duration-fast)] ${
            combineMode
              ? "border-[var(--accent)] bg-[var(--accent-muted)] text-[var(--accent)]"
              : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--accent)]"
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          Fuse
        </button>

        {/* Quick add */}
        <details className="relative">
          <summary className="cursor-pointer list-none rounded-lg bg-[var(--accent)] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[var(--accent-hover)]">
            + Interest
          </summary>
          <div className="absolute right-0 z-20 mt-2 w-80 max-w-[calc(100vw-1.5rem)] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-lg)]">
            <AddInterest />
          </div>
        </details>
      </div>

      {/* Canvas / list + inspector */}
      <div className="relative min-h-0 flex-1">
        {viewMode === "graph" ? <BrainCanvas /> : <BrainListView />}
        {selectedId && <Inspector />}

        {combine.isPending && (
          <div className="glass absolute inset-0 z-30 flex flex-col items-center justify-center">
            <div className="relative mb-8 h-20 w-20">
              <div className="absolute inset-0 rounded-full border border-[var(--border-subtle)]" />
              <motion.div
                className="absolute inset-0"
                animate={{ rotate: 360 }}
                transition={{ duration: 2.6, repeat: Infinity, ease: "linear" }}
              >
                <span
                  aria-hidden
                  className="absolute left-1/2 top-0 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--accent)] shadow-[0_0_12px_rgba(201,169,97,0.9)]"
                />
              </motion.div>
              <div className="absolute inset-0 flex items-center justify-center">
                <Sparkles className="h-6 w-6 text-[var(--accent)]" aria-hidden />
              </div>
            </div>
            <p className="atlas-title text-2xl">Fusing concepts</p>
            <p className="mt-2 max-w-sm text-center text-sm leading-relaxed text-[var(--text-secondary)]">
              Searching for the idea that lives between them — this can take up
              to a minute.
            </p>
            <div className="mt-6 h-1 w-56 overflow-hidden rounded-full bg-[var(--bg-raised)]">
              <motion.div
                className="h-full w-2/5 rounded-full bg-gradient-to-r from-transparent via-[var(--accent)] to-transparent"
                animate={{ x: ["-120%", "320%"] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: [0.45, 0, 0.55, 1] }}
              />
            </div>
          </div>
        )}

        {combineMode && !combine.isPending && (
          <div className="glass absolute bottom-3 left-1/2 z-20 flex max-w-[calc(100%-1rem)] -translate-x-1/2 flex-wrap items-center justify-center gap-2 rounded-xl border border-[var(--border-strong)] px-3 py-2 shadow-[var(--shadow-lg)] sm:bottom-6 sm:gap-3 sm:px-5 sm:py-3">
            {combinePicks.length === 0 && (
              <p className="text-sm text-[var(--text-secondary)]">
                Pick two stars to fuse…
              </p>
            )}
            {combinePicks.map((id) => {
              const node = graphData?.nodes.find((n) => n.id === id);
              return (
                <span key={id} className="flex items-center gap-1.5 rounded-full bg-[var(--accent-muted)] px-3 py-1 text-xs font-medium text-[var(--accent)]">
                  {node?.name ?? id.slice(0, 8)}
                  <button onClick={() => useBrainStore.getState().pickForCombine(id)} aria-label="Remove pick">
                    <X className="h-3 w-3" aria-hidden />
                  </button>
                </span>
              );
            })}
            <button
              onClick={async () => {
                if (combinePicks.length !== 2) return;
                const result = await combine.mutateAsync({
                  concept_a: combinePicks[0]!,
                  concept_b: combinePicks[1]!,
                });
                useBrainStore.getState().toggleCombine();
                useBrainStore.getState().select(result.id);
              }}
              disabled={combinePicks.length !== 2 || combine.isPending}
              className="btn-brass flex items-center gap-1.5 rounded-md px-4 py-1.5 text-xs font-semibold disabled:opacity-50"
            >
              {combine.isPending && <Loader2 className="h-3 w-3 animate-spin" aria-hidden />}
              Fuse into new idea
            </button>
            <button
              onClick={toggleCombine}
              aria-label="Cancel combine"
              className="rounded-md p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-full border px-3 py-1 text-xs transition-colors duration-[var(--duration-fast)] ${
        active
          ? "border-[var(--accent)] bg-[var(--accent-muted)] text-[var(--accent)]"
          : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
      }`}
    >
      {children}
    </button>
  );
}
