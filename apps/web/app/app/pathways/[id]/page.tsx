"use client";

import { use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, X } from "lucide-react";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Shimmer, ShimmerRows } from "@/components/ui/Shimmer";
import { PathwayStatusBadge } from "@/components/pathways/PathwayStatusBadge";
import { useCreatePathway, usePathway } from "@/hooks/usePathways";
import { useConceptDetail } from "@/hooks/useBrain";
import { MASTERY_COLORS, type ConceptDetail } from "@/types/brain";

export default function PathwayPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const pathway = usePathway(id);
  const router = useRouter();
  const createPathway = useCreatePathway();
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="relative h-screen overflow-y-auto">
      <div className="relative mx-auto max-w-3xl p-4 sm:p-6 lg:p-14">
        <Link
          href="/app/pathways"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden /> All pathways
        </Link>

        {pathway.isPending && (
          <>
            <Shimmer className="mb-4 h-9 w-2/3" />
            <ShimmerRows rows={3} rowClassName="h-32 rounded-2xl" />
          </>
        )}

        {pathway.isError && (
          <p role="alert" className="text-sm text-[var(--danger)]">Failed to load this pathway.</p>
        )}

        {pathway.data?.status === "GENERATING" && (
          <GeneratingState title={pathway.data.title} />
        )}

        {pathway.data && pathway.data.status !== "GENERATING" && (
          <>
            <header className="mb-8">
              <div className="flex items-center gap-3">
                <h1 className="atlas-title text-3xl">{pathway.data.title}</h1>
                <PathwayStatusBadge status={pathway.data.status} />
              </div>
              <p className="mt-1.5 text-xs text-[var(--text-muted)]">
                {pathway.data.concept_count} concepts · {pathway.data.section_count} sections
                {pathway.data.skipped_edges > 0 &&
                  ` · ${pathway.data.skipped_edges} circular prerequisite(s) dropped`}
              </p>
            </header>

            <ol className="space-y-8">
              {pathway.data.sections.map((section) => (
                <li key={section.id} aria-label={`Section ${section.position + 1}: ${section.title}`}>
                  <div className="mb-3 flex items-baseline gap-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-muted)] text-xs font-bold text-[var(--accent)]">
                      {section.position + 1}
                    </span>
                    <div>
                      <h2 className="font-semibold">{section.title}</h2>
                      {section.summary && (
                        <p className="text-xs text-[var(--text-secondary)]">{section.summary}</p>
                      )}
                    </div>
                  </div>
                  <ul className="ml-10 space-y-1.5">
                    {section.concepts.length === 0 && (
                      <li className="text-xs text-[var(--text-muted)] italic">No concepts in this section.</li>
                    )}
                    {section.concepts.map((concept) => (
                      <li key={concept.concept_id}>
                        <button
                          onClick={() => setSelected(concept.concept_id)}
                          className="flex w-full items-center justify-between rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-3 text-left transition-colors duration-[var(--duration-fast)] hover:border-[var(--accent)]"
                        >
                          <span className="flex min-w-0 items-center gap-3">
                            <span
                              aria-hidden
                              className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                              style={{ background: MASTERY_COLORS[concept.state as keyof typeof MASTERY_COLORS] }}
                            />
                            <span className="min-w-0">
                              <span className="block truncate text-sm font-medium">{concept.name}</span>
                              {concept.description && (
                                <span className="block truncate text-xs text-[var(--text-secondary)]">
                                  {concept.description}
                                </span>
                              )}
                            </span>
                          </span>
                          <span className="shrink-0 pl-3 text-xs tabular-nums text-[var(--text-muted)]">
                            {Math.round(concept.mastery_score)}%
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
            {pathway.data.status === "READY" && pathway.data.next_depth && (
              <section className="mt-10 rounded-2xl border border-[var(--border-strong)] bg-[var(--bg-surface)] p-6">
                <p className="eyebrow mb-2">Next layer</p>
                <h2 className="atlas-title text-2xl">Ready for {pathway.data.next_depth} depth?</h2>
                <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--text-secondary)]">
                  Keep this topic and build on the route you just finished with more concepts, applications, and harder prerequisites.
                </p>
                <button
                  onClick={async () => {
                    const next = await createPathway.mutateAsync({
                      topic: pathway.data!.topic ?? pathway.data!.title,
                      target_depth: pathway.data!.next_depth!,
                    });
                    router.push(`/app/pathways/${next.id}`);
                  }}
                  disabled={createPathway.isPending}
                  className="btn-brass mt-5 rounded-md px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
                >
                  {createPathway.isPending ? "Charting next route…" : `Continue to ${pathway.data.next_depth} →`}
                </button>
              </section>
            )}
          </>
        )}
      </div>

      {selected && <ConceptSidePanel conceptId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

const GENERATING_STEPS = [
  "Decomposing the topic into sections",
  "Ordering concepts from foundations to frontiers",
  "Mapping prerequisite structure",
  "Checking the graph stays acyclic",
];

function GeneratingState({ title }: { title: string }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setStep((s) => (s + 1) % GENERATING_STEPS.length), 2800);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-28 text-center" aria-busy="true" role="status">
      <div className="relative mb-10 h-20 w-20">
        <div className="absolute inset-0 rounded-full border border-[var(--border-subtle)]" />
        <motion.div
          className="absolute inset-0"
          animate={{ rotate: 360 }}
          transition={{ duration: 3.2, repeat: Infinity, ease: "linear" }}
        >
          <span
            aria-hidden
            className="absolute left-1/2 top-0 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--accent)] shadow-[0_0_12px_rgba(201,169,97,0.9)]"
          />
        </motion.div>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="atlas-title text-xl text-[var(--accent)]">L</span>
        </div>
      </div>

      <h1 className="atlas-title text-3xl font-light tracking-tight">Designing “{title}”</h1>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-[var(--text-secondary)]">
        Charting sections and prerequisite paths. This page will reveal itself when ready.
      </p>

      <div className="relative mt-8 h-4 w-80 overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, filter: "blur(4px)" }}
            animate={{ opacity: 1, filter: "blur(0px)" }}
            exit={{ opacity: 0, filter: "blur(4px)" }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="absolute inset-0 font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--accent)]"
          >
            {GENERATING_STEPS[step]}
          </motion.p>
        </AnimatePresence>
      </div>

      <div className="mt-6 h-px w-64 overflow-hidden bg-[var(--border-subtle)]">
        <motion.div
          className="h-full w-1/2 bg-[var(--accent)]"
          style={{ filter: "blur(0.5px)" }}
          animate={{ x: ["-100%", "200%"] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: [0.4, 0, 0.6, 1] }}
        />
      </div>
    </div>
  );
}

function ConceptSidePanel({ conceptId, onClose }: { conceptId: string; onClose: () => void }) {
  const detail = useConceptDetail(conceptId);
  const concept = detail.data as ConceptDetail | undefined;

  return (
    <aside
      aria-label="Concept details"
      className="fixed inset-y-0 right-0 z-30 w-full max-w-sm overflow-y-auto border-l border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-[var(--shadow-lg)]"
    >
      <div className="mb-4 flex items-start justify-between">
        <h2 className="text-lg font-semibold leading-tight">
          {concept?.canonical_name ?? "Loading…"}
        </h2>
        <button onClick={onClose} aria-label="Close panel"
                className="rounded-lg p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-raised)]">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      {detail.isPending && (
        <div className="space-y-2" aria-busy="true">
          {[0, 1, 2].map((i) => <Shimmer key={i} className="h-4" />)}
        </div>
      )}

      {concept && (
        <>
          <div
            role="progressbar" aria-valuenow={Math.round(concept.mastery_score)}
            aria-valuemin={0} aria-valuemax={100}
            className="mb-4 h-2 overflow-hidden rounded-full bg-[var(--bg-base)]"
          >
            <div
              className="h-full rounded-full transition-all duration-[var(--duration-slow)]"
              style={{
                width: `${Math.max(concept.mastery_score, 2)}%`,
                background: MASTERY_COLORS[concept.state],
              }}
            />
          </div>
          {concept.description && (
            <p className="text-sm leading-relaxed text-[var(--text-primary)]">{concept.description}</p>
          )}
          <MiniChips title="Prerequisites" ids={concept.prerequisites} />
          <MiniChips title="Unlocks" ids={concept.dependents} />

          <div className="mt-6 border-t border-[var(--border-subtle)] pt-4">
            <Link
              href={`/app/concepts/${conceptId}`}
              className="btn-brass block rounded-md px-4 py-2.5 text-center text-sm font-semibold"
            >
              Learn this →
            </Link>
          </div>
        </>
      )}
    </aside>
  );
}

function MiniChips({ title, ids }: { title: string; ids: { id: string; canonical_name: string }[] }) {
  if (ids.length === 0) return null;
  return (
    <div className="mt-4">
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">{title}</h3>
      <div className="flex flex-wrap gap-1.5">
        {ids.map((c) => (
          <span key={c.id} className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3 py-1 text-xs text-[var(--text-secondary)]">
            {c.canonical_name}
          </span>
        ))}
      </div>
    </div>
  );
}
