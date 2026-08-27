"use client";

import Link from "next/link";
import { Compass, Network, RefreshCw, Sparkles, Target, TrendingUp } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";
import { api } from "@/lib/api";
import { trackPortraitEvent } from "@/lib/portraitAnalytics";
import { usePortrait, usePortraitHistory, useRefreshPortrait } from "@/hooks/usePortrait";
import { selectedSnapshot } from "@/lib/portraitHistory";
import type { PortraitNode, PortraitThread } from "@/types/portrait";
import { useEffect, useState } from "react";

type Insight = PortraitNode | PortraitThread;
type FeedbackKind = "BRIDGE" | "GAP" | "EMERGING_INTEREST";

export default function DiscoveryPage() {
  const portrait = usePortrait();
  const history = usePortraitHistory();
  const refresh = useRefreshPortrait();
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
  const data = portrait.data;
  const selectedHistory = selectedSnapshot(history.data ?? [], selectedHistoryId);

  useEffect(() => {
    if (data?.snapshot_id) trackPortraitEvent("portrait_viewed", data.snapshot_id);
  }, [data?.snapshot_id]);

  useEffect(() => {
    if (history.data && history.data.length > 1) trackPortraitEvent("portrait_history_opened", data?.snapshot_id);
  }, [data?.snapshot_id, history.data?.length]);

  return <div className="relative min-h-screen overflow-y-auto"><div className="relative mx-auto max-w-5xl p-4 sm:p-6 lg:p-14">
    <header className="mb-10 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow mb-3"><Compass className="h-3.5 w-3.5" aria-hidden /> Discovery</p><h1 className="atlas-title text-3xl">The shape of your curiosity.</h1><p className="mt-3 max-w-xl text-sm leading-relaxed text-[var(--text-secondary)]">A versioned portrait of what you know, what connects it, and where your learning may be heading.</p></div><button type="button" onClick={() => refresh.mutate()} disabled={refresh.isPending} className="inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${refresh.isPending ? "animate-spin" : ""}`} />Refresh portrait</button></header>{refresh.isError && <p role="alert" className="-mt-6 mb-6 text-xs text-[var(--danger)]">Couldn&apos;t refresh the portrait. The last successful reading is unchanged.</p>}
    {portrait.isPending ? <p className="text-sm text-[var(--text-secondary)]">Reading your Brain…</p> : portrait.isError ? <p role="alert" className="text-sm text-[var(--danger)]">Couldn&apos;t load your portrait.</p> : data && <>
      <section className="mb-6 rounded-2xl border border-[var(--accent)]/30 bg-[var(--bg-surface)] p-6"><p className="eyebrow mb-3">Current reading</p><p className="max-w-3xl text-base leading-relaxed text-[var(--text-primary)]">{data.narrative}</p><div className="mt-5 flex flex-wrap gap-2">{data.summary.dominant_domains.map((domain) => <span key={domain} className="rounded-full bg-[var(--accent-muted)] px-3 py-1.5 text-xs text-[var(--accent)]">{domain}</span>)}</div></section>
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[["Concepts", data.summary.concept_count], ["Mastered", data.summary.mastered_concept_count], ["Domains", data.summary.domain_count], ["Frontier", data.summary.active_frontier_count], ["Reviews · 30d", data.evolution.recent_reviews ?? 0]].map(([label, value]) => <div key={label} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4"><p className="eyebrow">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p></div>)}</div>
      <div className="grid gap-6 lg:grid-cols-2"><Section title="Anchors" icon={<Target className="h-4 w-4" />} items={data.anchors} snapshotId={data.snapshot_id} /><Section title="Bridges" kind="BRIDGE" icon={<Network className="h-4 w-4" />} items={data.bridges} snapshotId={data.snapshot_id} /><Section title="Learning frontier" kind="GAP" icon={<TrendingUp className="h-4 w-4" />} items={data.frontiers} snapshotId={data.snapshot_id} /><Section title="Emerging threads" kind="EMERGING_INTEREST" icon={<Sparkles className="h-4 w-4" />} items={data.emerging_threads} snapshotId={data.snapshot_id} /><Section title="Dormant threads" icon={<Compass className="h-4 w-4" />} items={data.dormant_threads} snapshotId={data.snapshot_id} /></div>
      {data.changes_since_previous.length > 0 && <section className="mt-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6"><h2 className="mb-4 text-sm font-semibold">Since the last portrait</h2><ul className="space-y-2 text-sm text-[var(--text-secondary)]">{data.changes_since_previous.map((change) => <li key={change.text}>· {change.text}</li>)}</ul></section>}
      {history.data && history.data.length > 1 && <section className="mt-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6"><h2 className="mb-4 text-sm font-semibold">Portrait timeline</h2><div className="relative space-y-3 border-l border-[var(--border-subtle)] pl-5">{history.data.map((snapshot) => <div key={snapshot.snapshot_id} className="relative"><span className={`absolute -left-[1.55rem] top-4 h-2.5 w-2.5 rounded-full border-2 border-[var(--bg-surface)] ${selectedHistory?.snapshot_id === snapshot.snapshot_id ? "bg-[var(--accent)]" : "bg-[var(--text-muted)]"}`} /><button type="button" onClick={() => { setSelectedHistoryId(snapshot.snapshot_id); trackPortraitEvent("portrait_snapshot_selected", snapshot.snapshot_id); }} aria-pressed={selectedHistory?.snapshot_id === snapshot.snapshot_id} className={`w-full rounded-lg border p-3 text-left transition-colors duration-200 ${selectedHistory?.snapshot_id === snapshot.snapshot_id ? "border-[var(--accent)]" : "border-[var(--border-subtle)]"}`}><div className="flex items-baseline justify-between gap-3"><p className="font-mono text-[10px] text-[var(--text-muted)]">{new Date(snapshot.generated_at).toLocaleDateString()}</p><span className="font-mono text-[10px] text-[var(--text-muted)]">v{snapshot.version}</span></div><p className="mt-2 text-xs">{snapshot.summary.mastered_concept_count} mastered · {snapshot.summary.domain_count} domains</p></button></div>)}</div><AnimatePresence initial={false} mode="popLayout"><motion.div key={selectedHistory?.snapshot_id ?? "empty"} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.2, ease: "easeOut" }} className="mt-5 border-t border-[var(--border-subtle)] pt-5">{selectedHistory && <><p className="eyebrow mb-2">Selected snapshot · v{selectedHistory.version}</p><p className="text-sm leading-relaxed text-[var(--text-secondary)]">{selectedHistory.narrative}</p>{selectedHistory.changes_since_previous.length > 0 && <ul className="mt-3 space-y-1 text-xs text-[var(--text-muted)]">{selectedHistory.changes_since_previous.map((change) => <li key={change.text}>· {change.text}</li>)}</ul>}</>}</motion.div></AnimatePresence></section>}
    </>}
  </div></div>;
}

function isNode(item: Insight): item is PortraitNode {
  return "domain" in item;
}

function itemHref(item: Insight) {
  return isNode(item) ? `/app/concepts/${item.id}` : item.concept_ids[0] ? `/app/concepts/${item.concept_ids[0]}` : "/app/brain";
}

function trackInsightNavigation(item: Insight, snapshotId: string) {
  const event = itemHref(item) === "/app/brain" ? "portrait_brain_navigation" : "portrait_discovery_navigation";
  trackPortraitEvent(event, snapshotId, isNode(item) ? item.id : item.concept_ids[0] ?? item.id);
}

function Section({ title, kind, icon, items, snapshotId }: { title: string; kind?: FeedbackKind; icon: ReactNode; items: Insight[]; snapshotId: string }) {
  return <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6"><h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">{icon}<span>{title}</span></h2>{items.length ? <ul className="space-y-2">{items.map((item) => <li key={`${title}-${item.id}`}><div className="rounded-lg border border-[var(--border-subtle)] p-3">{isNode(item) ? <Link href={itemHref(item)} onClick={() => trackInsightNavigation(item, snapshotId)} className="block hover:text-[var(--accent)]"><p className="text-sm font-medium">{item.name}</p><p className="mt-1 text-[11px] text-[var(--text-muted)]">{item.domain} · {item.reason}</p></Link> : <Link href={itemHref(item)} onClick={() => trackInsightNavigation(item, snapshotId)} className="block hover:text-[var(--accent)]"><p className="text-sm font-medium">{item.name}</p><p className="mt-1 text-[11px] text-[var(--text-muted)]">{item.reason} · {item.concept_ids.length} concepts</p></Link>}<div className="mt-2 flex items-center justify-between"><span className="font-mono text-[10px] text-[var(--text-muted)]">signal {Math.round(item.score * 100)}%</span>{kind && <div className="flex gap-3 text-[10px]"><button onClick={() => void api("/discovery/portrait/feedback", { method: "POST", body: JSON.stringify({ kind, subject: item.name, accepted: true }) })} className="text-[var(--accent)] hover:underline">Useful</button><button onClick={() => void api("/discovery/portrait/feedback", { method: "POST", body: JSON.stringify({ kind, subject: item.name, accepted: false }) })} className="text-[var(--text-muted)] hover:underline">Not me</button></div>}</div></div></li>)}</ul> : <p className="text-sm text-[var(--text-secondary)]">Nothing surfaced yet.</p>}</section>;
}
