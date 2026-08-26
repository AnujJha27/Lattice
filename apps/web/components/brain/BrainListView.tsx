"use client";

import { useBrainGraph } from "@/hooks/useBrain";
import { Shimmer } from "@/components/ui/Shimmer";
import { MASTERY_COLORS, type BrainNode } from "@/types/brain";
import { useBrainStore } from "@/lib/store/brain";

/** Accessible alternative to the graph canvas: semantic list grouped by domain. */
export function BrainListView() {
  const { data: graphData, isPending, isError, refetch } = useBrainGraph();
  const select = useBrainStore((s) => s.select);
  const selectedId = useBrainStore((s) => s.selectedId);
  const domainFilter = useBrainStore((s) => s.domainFilter);

  if (isPending) {
    return (
      <div className="mx-auto max-w-2xl space-y-3 p-8" aria-busy="true">
        {[0, 1, 2, 3].map((i) => (
          <Shimmer key={i} className="h-14" rounded="rounded-xl" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center">
        <div role="alert" className="text-center">
          <p className="mb-3 text-sm text-[var(--danger)]">Couldn&apos;t load your Brain.</p>
          <button onClick={() => void refetch()} className="text-sm text-[var(--accent)] underline underline-offset-2">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const nodes = (graphData?.nodes ?? []).filter(
    (n) => !domainFilter || n.domain === domainFilter,
  );

  if (nodes.length === 0) {
    return (
      <p className="p-10 text-center text-sm text-[var(--text-secondary)]">
        No concepts{domainFilter ? ` in ${domainFilter}` : ""} yet.
      </p>
    );
  }

  const byDomain = new Map<string, BrainNode[]>();
  for (const node of nodes) {
    const key = node.domain ?? "Uncategorized";
    if (!byDomain.has(key)) byDomain.set(key, []);
    byDomain.get(key)!.push(node);
  }

  return (
    <nav aria-label="Concept list" className="mx-auto max-w-2xl space-y-6 overflow-y-auto p-6 lg:p-10">
      {[...byDomain.entries()].map(([domain, domainNodes]) => (
        <section key={domain}>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            {domain} · {domainNodes.length}
          </h2>
          <ul className="space-y-1.5">
            {domainNodes.map((node) => (
              <li key={node.id}>
                <button
                  onClick={() => select(node.id)}
                  aria-current={selectedId === node.id ? "true" : undefined}
                  className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition-colors duration-[var(--duration-fast)] ${
                    selectedId === node.id
                      ? "border-[var(--accent)] bg-[var(--accent-muted)]"
                      : "border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:bg-[var(--bg-raised)]"
                  }`}
                >
                  <span className="flex items-center gap-3">
                    <span
                      aria-hidden
                      className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ background: MASTERY_COLORS[node.state] }}
                    />
                    <span>
                      <span className="block text-sm font-medium">{node.name}</span>
                      <span className="block text-xs text-[var(--text-muted)]">
                        {Math.round(node.mastery_score)}% mastery · interest{" "}
                        {Math.round(node.interest_score)}%
                      </span>
                    </span>
                  </span>
                  <span className="text-xs text-[var(--text-muted)]">View →</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </nav>
  );
}
