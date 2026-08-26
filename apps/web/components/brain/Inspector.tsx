"use client";

import { X } from "lucide-react";
import { Shimmer } from "@/components/ui/Shimmer";
import Link from "next/link";
import { useConceptDetail } from "@/hooks/useBrain";
import { useBrainStore } from "@/lib/store/brain";
import { MASTERY_COLORS } from "@/types/brain";

const STATE_LABELS: Record<string, string> = {
  UNSEEN: "Not started",
  AVAILABLE: "Ready to learn",
  LEARNING: "Learning",
  FAMILIAR: "Familiar",
  MASTERED: "Mastered",
};

export function Inspector() {
  const selectedId = useBrainStore((s) => s.selectedId);
  const select = useBrainStore((s) => s.select);
  const { data: concept, isPending, isError } = useConceptDetail(selectedId);

  if (!selectedId) return null;

  return (
    <aside
      aria-label="Concept inspector"
      className="absolute right-0 top-0 z-10 flex h-full w-full max-w-sm flex-col border-l border-[var(--border-subtle)] bg-[var(--bg-surface)]/95 backdrop-blur-md shadow-[var(--shadow-lg)]"
    >
      <div className="flex items-start justify-between p-5 pb-3">
        {isPending && (
          <div className="w-full space-y-2" aria-busy="true">
            <Shimmer className="h-6 w-3/4" />
            <Shimmer className="h-4 w-1/3" />
          </div>
        )}
        {concept && (
          <>
            <div>
              <h2 className="text-lg font-semibold leading-tight">{concept.canonical_name}</h2>
              <p className="mt-0.5 text-xs uppercase tracking-wider text-[var(--text-muted)]">
                {concept.domain ?? "Uncategorized"}
              </p>
            </div>
            <button
              onClick={() => select(null)}
              aria-label="Close inspector"
              className="rounded-lg p-1.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-raised)] hover:text-[var(--text-primary)]"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </>
        )}
      </div>

      {isError && (
        <div className="mx-5 rounded-lg border border-[var(--danger)] p-3 text-sm text-[var(--danger)]" role="alert">
          Failed to load this concept.
        </div>
      )}

      {concept && (
        <div className="flex-1 space-y-6 overflow-y-auto px-5 pb-6">
          {/* Mastery */}
          <section>
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="font-medium uppercase tracking-wider text-[var(--text-secondary)]">
                Mastery
              </span>
              <span style={{ color: MASTERY_COLORS[concept.state] }}>
                {STATE_LABELS[concept.state]} · {Math.round(concept.mastery_score)}%
              </span>
            </div>
            <div
              role="progressbar"
              aria-valuenow={Math.round(concept.mastery_score)}
              aria-valuemin={0}
              aria-valuemax={100}
              className="h-2 overflow-hidden rounded-full bg-[var(--bg-base)]"
            >
              <div
                className="h-full rounded-full transition-all duration-[var(--duration-slow)]"
                style={{
                  width: `${Math.max(concept.mastery_score, 2)}%`,
                  background: MASTERY_COLORS[concept.state],
                }}
              />
            </div>
            {concept.difficulty != null && (
              <p className="mt-2 text-xs text-[var(--text-muted)]">
                Difficulty {"●".repeat(concept.difficulty)}
                {"○".repeat(5 - concept.difficulty)}
              </p>
            )}
          </section>

          {concept.description && (
            <section>
              <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">
                About
              </h3>
              <p className="text-sm leading-relaxed text-[var(--text-primary)]">
                {concept.description}
              </p>
            </section>
          )}

          <ConceptSection title="Prerequisites" concepts={concept.prerequisites} onSelect={select} />
          <ConceptSection title="Unlocks" concepts={concept.dependents} onSelect={select} />
          <ConceptSection title="Related" concepts={concept.related} onSelect={select} />

          <section className="border-t border-[var(--border-subtle)] pt-4">
            {selectedId && (
              <Link
                href={`/app/concepts/${selectedId}`}
                className="block w-full rounded-lg bg-[var(--accent)] px-4 py-2.5 text-center text-sm font-semibold text-white transition-colors duration-[var(--duration-fast)] hover:bg-[var(--accent-hover)]"
              >
                Learn this →
              </Link>
            )}
          </section>
        </div>
      )}
    </aside>
  );
}

function ConceptSection({
  title,
  concepts,
  onSelect,
}: {
  title: string;
  concepts: { id: string; canonical_name: string; domain: string | null }[];
  onSelect: (id: string) => void;
}) {
  if (concepts.length === 0) return null;
  return (
    <section>
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">
        {title}
      </h3>
      <div className="flex flex-wrap gap-1.5">
        {concepts.map((c) => (
          <button
            key={c.id}
            onClick={() => onSelect(c.id)}
            className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-colors duration-[var(--duration-fast)] hover:border-[var(--accent)] hover:text-[var(--text-primary)]"
          >
            {c.canonical_name}
          </button>
        ))}
      </div>
    </section>
  );
}
