"use client";

import Link from "next/link";
import { Compass, Network, Sparkles, TrendingUp } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Item = { concept_id?: string | null; name: string; domain: string; score: number; reason: string };
type Portrait = { bridges: Item[]; gaps: Item[]; emerging_interests: Item[]; adjacent_fields: string[]; evolution: Record<string, number> };
type History = { created_at: string; evolution: Record<string, number> };

export default function DiscoveryPage() {
  const portrait = useQuery({ queryKey: ["discovery", "portrait"], queryFn: () => api<Portrait>("/discovery/portrait") });
  const history = useQuery({ queryKey: ["discovery", "portrait", "history"], queryFn: () => api<History[]>("/discovery/portrait/history") });
  const data = portrait.data;
  return <div className="relative min-h-screen overflow-y-auto"><div className="relative mx-auto max-w-5xl p-8 lg:p-14">
    <header className="mb-10"><p className="eyebrow mb-3"><Compass className="h-3.5 w-3.5" aria-hidden /> Discovery</p><h1 className="atlas-title text-3xl">The shape of your curiosity.</h1><p className="mt-3 max-w-xl text-sm leading-relaxed text-[var(--text-secondary)]">Connections, gaps, and new directions inferred from your Brain and review history.</p></header>
    {portrait.isPending ? <p className="text-sm text-[var(--text-secondary)]">Reading your Brain…</p> : portrait.isError ? <p role="alert" className="text-sm text-[var(--danger)]">Couldn&apos;t load your portrait.</p> : data && <>
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[["Concepts", data.evolution.concepts], ["Mastered", data.evolution.mastered], ["Reviews", data.evolution.reviews], ["Last 30 days", data.evolution.recent_reviews], ["Mastery change", data.evolution.mastery_delta]].map(([label, value]) => <div key={label} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4"><p className="eyebrow">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p></div>)}</div>
      <div className="grid gap-6 lg:grid-cols-2"><Section title="Bridges" kind="BRIDGE" icon={<Network className="h-4 w-4" />} items={data.bridges} /><Section title="Gaps to close" kind="GAP" icon={<TrendingUp className="h-4 w-4" />} items={data.gaps} /><Section title="Emerging interests" kind="EMERGING_INTEREST" icon={<Sparkles className="h-4 w-4" />} items={data.emerging_interests} /><section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6"><h2 className="mb-4 flex items-center gap-2 text-sm font-semibold"><Compass className="h-4 w-4 text-[var(--accent)]" />Adjacent fields</h2>{data.adjacent_fields.length ? <div className="flex flex-wrap gap-2">{data.adjacent_fields.map((field) => <span key={field} className="rounded-full bg-[var(--accent-muted)] px-3 py-1.5 text-xs text-[var(--accent)]">{field}</span>)}</div> : <p className="text-sm text-[var(--text-secondary)]">Keep learning to reveal cross-domain bridges.</p>}</section></div>
      {history.data && history.data.length > 1 && <section className="mt-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6"><h2 className="mb-4 text-sm font-semibold">Portrait evolution</h2><div className="flex gap-3 overflow-x-auto pb-1">{history.data.map((snapshot) => <div key={snapshot.created_at} className="min-w-36 rounded-lg border border-[var(--border-subtle)] p-3"><p className="font-mono text-[10px] text-[var(--text-muted)]">{new Date(snapshot.created_at).toLocaleDateString()}</p><p className="mt-2 text-xs">{snapshot.evolution.mastered ?? 0} mastered</p><p className="text-xs text-[var(--text-secondary)]">Δ {snapshot.evolution.mastery_delta ?? 0}</p></div>)}</div></section>}
    </>}
  </div></div>;
}

function Section({ title, kind, icon, items }: { title: string; kind: string; icon: React.ReactNode; items: Item[] }) {
  return <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6"><h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">{icon}<span>{title}</span></h2>{items.length ? <ul className="space-y-2">{items.map((item, i) => <li key={`${item.name}-${i}`}><div className="rounded-lg border border-[var(--border-subtle)] p-3">{item.concept_id ? <Link href={`/app/concepts/${item.concept_id}`} className="block hover:text-[var(--accent)]"><p className="text-sm font-medium">{item.name}</p><p className="mt-1 text-[11px] text-[var(--text-muted)]">{item.domain} · {item.reason}</p></Link> : <><p className="text-sm font-medium">{item.name}</p><p className="mt-1 text-[11px] text-[var(--text-muted)]">{item.domain} · {item.reason}</p></>}<div className="mt-2 flex gap-3 text-[10px]"><button onClick={() => void api("/discovery/portrait/feedback", { method: "POST", body: JSON.stringify({ kind, subject: item.name, accepted: true }) })} className="text-[var(--accent)] hover:underline">Useful</button><button onClick={() => void api("/discovery/portrait/feedback", { method: "POST", body: JSON.stringify({ kind, subject: item.name, accepted: false }) })} className="text-[var(--text-muted)] hover:underline">Not me</button></div></div></li>)}</ul> : <p className="text-sm text-[var(--text-secondary)]">Nothing surfaced yet.</p>}</section>;
}
