"use client";

import { ExternalLink } from "lucide-react";
import type { LessonSourceContext } from "@/types/lessons";

/**
 * Inline citation marker with a source preview popover (overrides §20-21).
 */
export function CitationMarker({
  number,
  source,
}: {
  number: number;
  source: LessonSourceContext;
}) {
  return (
    <span className="mx-0.5 inline-flex h-4 min-w-4 cursor-default items-center justify-center rounded-full bg-[var(--accent-muted)] align-super px-1 text-[9px] font-semibold leading-none text-[var(--accent)]">
      {number}
    </span>
  );
}

/**
 * Renders paragraph text, appending its citation markers at the end.
 */
export function CitedParagraph({
  text,
  sourceIds,
  sourcesByIdIndex,
  serif = false,
}: {
  text: string;
  sourceIds: number[];
  sourcesByIdIndex: Map<number, LessonSourceContext>;
  serif?: boolean;
}) {
  return (
    <p
      className={`leading-8 text-[var(--text-primary)] ${serif ? "font-[var(--font-display)] text-[15px]" : "text-sm"}`}
    >
      {text}
      {sourceIds.length > 0 && (
        <span className="ml-1 whitespace-nowrap">
          {sourceIds.map((idx, position) => {
            const source = sourcesByIdIndex.get(idx);
            if (!source) return null;
            return <CitationMarker key={idx} number={position + 1} source={source} />;
          })}
        </span>
      )}
    </p>
  );
}

/** Source preview chip used in the sources grid. */
export function SourceChip({
  index,
  source,
}: {
  index: number;
  source: LessonSourceContext;
}) {
  return (
    <a
      href={source.url ?? "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="flex h-full items-start gap-2.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3.5 transition-colors duration-[var(--duration-fast)] hover:border-[var(--accent)]"
    >
      <span className="mt-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--accent-muted)] px-1 text-[9px] font-bold text-[var(--accent)]">
        {index}
      </span>
      <span className="min-w-0">
        <span className="block truncate text-xs font-medium">{source.title}</span>
        <span className="block truncate text-[10px] text-[var(--text-muted)]">
          {[...source.authors.slice(0, 2), source.publisher].filter(Boolean).join(" · ")}
        </span>
      </span>
      <ExternalLink className="ml-auto mt-0.5 h-3 w-3 shrink-0 text-[var(--text-muted)]" aria-hidden />
    </a>
  );
}
