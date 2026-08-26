"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { api } from "@/lib/api";
import { AddInterest } from "@/components/brain/AddInterest";
import { useBrainGraph } from "@/hooks/useBrain";
import { BorderBeam, CountUp, Reveal } from "@/components/ui/effects";
import { SpotlightCard } from "@/components/ui/Spotlight";
import { Shimmer } from "@/components/ui/Shimmer";

type Health = {
  ok: boolean;
  environment: string;
  providers: {
    llm: string | null;
    embeddings: string | null;
    web_search: string | null;
    academic: string[];
  };
};

type Recommendation = { concept_id: string; name: string; score: number; factors?: { deterministic?: number; llm?: number } };
type DueReview = { concept_id: string; name: string; mastery_score: number };
type RecommendationEvaluation = { ctr: number; clicked_mastery_delta: number };

export default function OverviewPage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health"),
    refetchInterval: 60_000,
  });
  const brain = useBrainGraph();
  const dueReviews = useQuery({
    queryKey: ["reviews", "due"],
    queryFn: () => api<DueReview[]>("/reviews/due"),
  });
  const recommendations = useQuery({
    queryKey: ["recommendations"],
    queryFn: () => api<Recommendation[]>("/recommendations"),
  });
  const recommendationEvaluation = useQuery({
    queryKey: ["recommendations", "evaluation"],
    queryFn: () => api<RecommendationEvaluation>("/recommendations/evaluation"),
  });

  const concepts = brain.data?.nodes.length ?? 0;
  const connections = brain.data?.edges.length ?? 0;

  return (
    <div className="relative h-screen overflow-y-auto">
      {/* Sky behind everything */}
      <div className="relative p-8 lg:p-12">
        {/* Hero */}
        <Reveal>
          <header className="mb-10 max-w-3xl">
            <p className="eyebrow mb-4 flex items-center gap-3">
              <span aria-hidden className="inline-block h-px w-8 bg-[var(--accent)]" />
              Personal observatory
            </p>
            <h1 className="atlas-title text-6xl leading-[1.05] text-[var(--text-primary)]">
              See what you know.
              <br />
              <span className="bg-gradient-to-r from-[var(--accent)] via-[var(--text-primary)] to-[var(--accent)] bg-clip-text text-transparent">
                Find what is next.
              </span>
            </h1>
          </header>
        </Reveal>

        <Reveal delay={0.06} className="mb-5 max-w-5xl">
          <section className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[var(--border-strong)] bg-[var(--bg-surface)]/80 p-5 shadow-[var(--shadow-md)] backdrop-blur-sm">
            <div>
              <p className="eyebrow mb-2">Next move</p>
              <h2 className="atlas-title text-2xl">
                {dueReviews.data?.[0] ? `Review ${dueReviews.data[0].name}` : recommendations.data?.[0] ? `Explore ${recommendations.data[0].name}` : "Chart your first idea"}
              </h2>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">
                {dueReviews.data?.length ? `${dueReviews.data.length} review${dueReviews.data.length === 1 ? "" : "s"} ready to keep your lattice alive.` : "A focused next step keeps momentum better than a crowded dashboard."}
              </p>
            </div>
            <Link href={dueReviews.data?.[0] ? "/app/review" : recommendations.data?.[0] ? `/app/concepts/${recommendations.data[0].concept_id}` : "/app/brain"} className="btn-brass rounded-md px-5 py-2.5 text-sm font-semibold">
              {dueReviews.data?.[0] ? "Start review →" : recommendations.data?.[0] ? "Open concept →" : "Add an interest →"}
            </Link>
          </section>
        </Reveal>

        <div className="grid max-w-5xl gap-5 md:grid-cols-2">
          {/* Sky snapshot */}
          <Reveal delay={0.08}>
            <SpotlightCard className="h-full">
              <BorderBeam duration={8} />
              <div className="p-6">
                <p className="eyebrow mb-5">Tonight&apos;s sky</p>
                {brain.isPending ? (
                  <div className="space-y-2" aria-busy="true">
                    <Shimmer className="h-12 w-28" />
                    <Shimmer className="h-4 w-40" />
                  </div>
                ) : (
                  <>
                    <div className="flex items-baseline gap-5">
                      <CountUp
                        value={concepts}
                        className="atlas-title text-6xl text-[var(--text-primary)]"
                      />
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.6 }}
                        className="font-mono text-xs uppercase tracking-widest text-[var(--text-secondary)]"
                      >
                        stars ·{" "}
                        <CountUp value={connections} /> constellation
                        {connections === 1 ? "" : "s"}
                      </motion.span>
                    </div>
                    <Link
                      href="/app/brain"
                      className="btn-brass mt-6 inline-block rounded-md px-5 py-2.5 text-sm font-semibold"
                    >
                      Open the Brain →
                    </Link>
                  </>
                )}
              </div>
            </SpotlightCard>
          </Reveal>

          {/* Chart a new star */}
          <Reveal delay={0.16}>
            <SpotlightCard className="h-full">
              <div className="p-6">
                <p className="eyebrow mb-5">Chart a new star</p>
                <AddInterest />
              </div>
            </SpotlightCard>
          </Reveal>

          {/* Instruments */}
          <Reveal delay={0.24} className="md:col-span-2">
            <SpotlightCard>
              <div className="p-6">
                <p className="eyebrow mb-5">Instruments</p>
                {health.isPending ? (
                  <div className="space-y-2" aria-busy="true">
                    {[0, 1].map((i) => (
                      <Shimmer key={i} className="h-9" rounded="rounded-md" />
                    ))}
                  </div>
                ) : health.isError ? (
                  <div
                    role="alert"
                    className="flex items-center justify-between rounded-md border border-[var(--danger)] p-3.5 text-sm text-[var(--danger)]"
                  >
                    <span>Observatory unreachable — is the backend running?</span>
                    <button onClick={() => void health.refetch()} className="underline underline-offset-4">
                      Retry
                    </button>
                  </div>
                ) : (
                  <dl className="grid gap-2.5 sm:grid-cols-2">
                    <StatusRow label="API" value={`Online · ${health.data.environment}`} ok={health.data.ok} />
                    <StatusRow label="LLM" value={health.data.providers.llm ?? "Not configured"} ok={!!health.data.providers.llm} />
                    <StatusRow
                      label="Embeddings"
                      value={health.data.providers.embeddings ?? "Not configured"}
                      ok={!!health.data.providers.embeddings}
                    />
                    <StatusRow
                      label="Web search"
                      value={health.data.providers.web_search ?? "Not configured"}
                      ok={!!health.data.providers.web_search}
                    />
                    <StatusRow
                      label="Academic catalogues"
                      value={health.data.providers.academic.join(", ")}
                      ok={health.data.providers.academic.length > 0}
                    />
                  </dl>
                )}
              </div>
            </SpotlightCard>
          </Reveal>

          <Reveal delay={0.3} className="md:col-span-2">
            <SpotlightCard>
              <div className="p-6">
                <p className="eyebrow mb-5">What to explore next {recommendationEvaluation.data && <span className="ml-2 normal-case tracking-normal text-[var(--text-muted)]">· {Math.round(recommendationEvaluation.data.ctr * 100)}% clicked</span>}</p>
                {recommendations.isPending ? (
                  <Shimmer className="h-10" />
                ) : recommendations.data?.length ? (
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
                    {recommendations.data.map((item) => (
                      <Link key={item.concept_id} href={`/app/concepts/${item.concept_id}`} onClick={() => { void api(`/recommendations/${item.concept_id}/click`, { method: "POST", body: JSON.stringify({ score: item.score, factors: item.factors ?? {} }) }); }} className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] p-3 transition-colors hover:border-[var(--accent)]">
                        <span className="block truncate text-sm font-medium">{item.name}</span>
                        <span className="mt-1 block font-mono text-[10px] text-[var(--text-muted)]">{Math.round(item.score)} priority{item.factors?.llm ? ` · AI ${Math.round(item.factors.llm * 100)}` : ""}</span>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-[var(--text-secondary)]">Add a few interests to get your next recommendations.</p>
                )}
              </div>
            </SpotlightCard>
          </Reveal>
        </div>
      </div>
    </div>
  );
}

function StatusRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-[var(--bg-base)] px-3.5 py-2.5 text-sm">
      <dt className="text-[var(--text-secondary)]">{label}</dt>
      <dd className="flex items-center gap-2">
        <span
          aria-hidden
          className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-[var(--success)]" : "bg-[var(--mastery-0)]"}`}
        />
        <span className="font-mono text-xs">{value}</span>
      </dd>
    </div>
  );
}
