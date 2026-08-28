"use client";

import { useState } from "react";
import { ExternalLink, Loader2, Plus, Search } from "lucide-react";
import { useAcceptSource, useDiscover } from "@/hooks/useSources";
import { SOURCE_TYPE_LABELS, type RankedCandidate } from "@/types/sources";

export function DiscoverySearch({ onAdded }: { onAdded?: () => void }) {
  const [input, setInput] = useState("");
  const [domain, setDomain] = useState("");
  const [submitted, setSubmitted] = useState<{ query: string; domain: string } | null>(null);
  const discovery = useDiscover(submitted?.query ?? null, submitted?.domain || null);
  const accept = useAcceptSource();

  function search(e: React.FormEvent) {
    e.preventDefault();
    if (input.trim().length >= 3) {
      setSubmitted({ query: input.trim(), domain: domain.trim() });
    }
  }

  async function add(ranked: RankedCandidate) {
    const c = ranked.candidate;
    await accept.mutateAsync({
      title: c.title,
      url: c.url,
      source_type: c.source_type,
      authority: c.authority,
      published: c.published,
      publisher: null,
      authors: c.authors,
      doi: c.doi,
      arxiv_id: c.arxiv_id,
      content: typeof c.extra.raw_content === "string" ? c.extra.raw_content : undefined,
    });
    onAdded?.();
  }

  return (
    <div className="space-y-4">
      <form onSubmit={search} className="space-y-2.5">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" aria-hidden />
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Search trusted sources — e.g. spectral graph theory"
              aria-label="Search query"
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] py-2.5 pl-9 pr-3 text-sm outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
            />
          </div>
          <button
            type="submit"
            disabled={input.trim().length < 3 || discovery.isFetching}
            className="rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-white transition-colors duration-[var(--duration-fast)] hover:bg-[var(--accent-hover)] disabled:opacity-50"
          >
            {discovery.isFetching ? "Searching…" : "Discover"}
          </button>
        </div>
        <input
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder="Domain for ranking policy (optional) — mathematics, computer science…"
          aria-label="Domain"
          className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3.5 py-2 text-xs outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
        />
      </form>

      {discovery.isError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          Search failed. Check your Tavily key or try again.
        </p>
      )}

      {discovery.data && (
        <>
          <p className="text-xs text-[var(--text-muted)]">
            {discovery.data.candidates.length} results
            {discovery.data.deduped_from > discovery.data.candidates.length &&
              ` (deduplicated from ${discovery.data.deduped_from})`}
            {" · "}ranked by authority, relevance, freshness, primary-source preference
          </p>
          <ul className="space-y-2">
            {discovery.data.candidates.map((ranked, i) => (
              <CandidateCard
                key={`${ranked.candidate.url}-${i}`}
                ranked={ranked}
                onAdd={() => void add(ranked)}
                adding={accept.isPending}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function CandidateCard({
  ranked,
  onAdd,
  adding,
}: {
  ranked: RankedCandidate;
  onAdd: () => void;
  adding: boolean;
}) {
  const c = ranked.candidate;
  const factors = ranked.factors;

  return (
    <li className="group rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 transition-colors duration-[var(--duration-fast)] hover:border-[var(--border-strong)]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
            <span className="rounded-md bg-[var(--accent-muted)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--accent)]">
              {SOURCE_TYPE_LABELS[c.source_type] ?? c.source_type}
            </span>
            {c.publisher && (
              <span className="text-xs text-[var(--text-secondary)]">{c.publisher}</span>
            )}
            {c.published && (
              <span className="text-xs text-[var(--text-muted)]">{c.published.slice(0, 4)}</span>
            )}
            {c.provider === "arxiv" && (
              <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">arXiv</span>
            )}
          </div>
          <a
            href={c.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block truncate text-sm font-medium text-[var(--text-primary)] underline-offset-2 hover:underline"
          >
            {c.title}
          </a>
          {c.snippet && (
            <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-[var(--text-secondary)]">
              {c.snippet}
            </p>
          )}
          {/* Factor breakdown — rankings are debuggable (spec §19) */}
          <p className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-[var(--text-muted)]">
            <span>score {(Number(factors.total) * 100).toFixed(0)}</span>
            <span>authority {(Number(factors.authority) * 100).toFixed(0)}</span>
            <span>relevance {(Number(factors.relevance) * 100).toFixed(0)}</span>
            <span>freshness {(Number(factors.freshness) * 100).toFixed(0)}</span>
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <button
            onClick={onAdd}
            disabled={adding}
            aria-label={`Add ${c.title} to library`}
            title="Save to library + start ingestion"
            className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-raised)] px-3 py-1.5 text-xs font-medium transition-colors duration-[var(--duration-fast)] hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-50"
          >
            {adding ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            ) : (
              <Plus className="h-3.5 w-3.5" aria-hidden />
            )}
            Save
          </button>
          <a
            href={c.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Open source externally"
            className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
          >
            open <ExternalLink className="h-3 w-3" aria-hidden />
          </a>
        </div>
      </div>
    </li>
  );
}
