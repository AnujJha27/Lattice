"use client";

import { CheckCircle2, ExternalLink, FileText, RotateCcw, XCircle } from "lucide-react";
import { motion } from "motion/react";
import { useLibrary, useRetrySource } from "@/hooks/useSources";
import { ShimmerRows } from "@/components/ui/Shimmer";
import { SOURCE_TYPE_LABELS, type SourceItem } from "@/types/sources";

const STATUS_META: Record<SourceItem["ingest_status"], { label: string; tone: "ok" | "working" | "error" }> = {
  PENDING: { label: "Queued", tone: "working" },
  FETCHED: { label: "Fetched", tone: "working" },
  EXTRACTED: { label: "Extracted", tone: "working" },
  CHUNKED: { label: "Chunked", tone: "working" },
  EMBEDDED: { label: "Ready", tone: "ok" },
  FAILED: { label: "Failed", tone: "error" },
};

export function SourceLibraryList() {
  const library = useLibrary();

  if (library.isPending) {
    return (
      <ShimmerRows rows={3} rowClassName="h-16" />
    );
  }

  if (library.isError) {
    return (
      <div role="alert" className="rounded-xl border border-[var(--danger)] p-4 text-sm text-[var(--danger)]">
        Couldn&apos;t load your library.
      </div>
    );
  }

  const sources = library.data ?? [];
  if (sources.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-[var(--border-subtle)] p-6 text-center text-sm text-[var(--text-secondary)]">
        Nothing saved yet. Discover sources above — everything you save is fetched,
        chunked, and embedded in the background so lessons can cite it.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {sources.map((source) => (
        <SourceRow key={source.id} source={source} />
      ))}
    </ul>
  );
}

function SourceRow({ source }: { source: SourceItem }) {
  const status = STATUS_META[source.ingest_status];
  const retry = useRetrySource();

  return (
    <li className="flex items-center justify-between gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <div className="flex min-w-0 items-start gap-3">
        <FileText className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-hidden />
        <div className="min-w-0">
          {source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block truncate text-sm font-medium underline-offset-2 hover:underline"
            >
              {source.title}
            </a>
          ) : (
            <span className="block truncate text-sm font-medium">{source.title}</span>
          )}
          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-[var(--text-muted)]">
            <span className="rounded-md bg-[var(--bg-base)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              {SOURCE_TYPE_LABELS[source.source_type] ?? source.source_type}
            </span>
            {source.publisher && <span>{source.publisher}</span>}
            {source.authors.length > 0 && <span>{source.authors.slice(0, 3).join(", ")}</span>}
            {source.published && <span>{source.published.slice(0, 4)}</span>}
          </p>
          {source.ingest_error && (
            <p role="alert" className="mt-2 max-w-2xl break-words text-xs text-[var(--danger)]">
              {source.ingest_error}
            </p>
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        {source.ingest_status === "FAILED" && (
          <button
            onClick={() => retry.mutate(source.id)}
            disabled={retry.isPending}
            aria-label={`Retry ingesting ${source.title}`}
            className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)] transition-colors hover:text-[var(--accent)] disabled:opacity-50"
          >
            <RotateCcw className="h-3 w-3" aria-hidden />
            retry
          </button>
        )}
        <StatusBadge status={status.label} tone={status.tone}
                     title={source.chunk_count ? `${source.chunk_count} indexed chunks` : undefined} />
        {source.url && (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Open externally"
            className="text-[var(--text-muted)] transition-colors hover:text-[var(--text-secondary)]"
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden />
          </a>
        )}
      </div>
    </li>
  );
}

function StatusBadge({
  status,
  tone,
  title,
}: {
  status: string;
  tone: "ok" | "working" | "error";
  title?: string;
}) {
  return (
    <span
      title={title}
      className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
        tone === "ok"
          ? "bg-[rgba(127,176,105,0.14)] text-[var(--success)]"
          : tone === "error"
            ? "bg-[rgba(207,102,121,0.12)] text-[var(--danger)]"
            : "bg-[var(--accent-muted)] text-[var(--accent)]"
      }`}
    >
      {tone === "ok" && <CheckCircle2 className="h-3 w-3" aria-hidden />}
      {tone === "error" && <XCircle className="h-3 w-3" aria-hidden />}
      {tone === "working" && (
        <span aria-hidden className="relative block h-1 w-7 overflow-hidden rounded-full bg-[rgba(201,169,97,0.18)]">
          <motion.span
            className="absolute inset-y-0 w-1/2 rounded-full bg-[var(--accent)]"
            animate={{ x: ["-100%", "220%"] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: [0.45, 0, 0.55, 1] }}
          />
        </span>
      )}
      {status}
    </span>
  );
}
