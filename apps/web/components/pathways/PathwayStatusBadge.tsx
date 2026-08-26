import { motion } from "motion/react";

export function PathwayStatusBadge({ status }: { status: string }) {
  if (status === "GENERATING") {
    return (
      <span className="flex shrink-0 items-center gap-2 rounded-full bg-[var(--accent-muted)] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--accent)]">
        {/* Smooth indeterminate sweep — no spinner jank */}
        <span aria-hidden className="relative block h-1 w-10 overflow-hidden rounded-full bg-[rgba(201,169,97,0.18)]">
          <motion.span
            className="absolute inset-y-0 w-1/2 rounded-full bg-[var(--accent)]"
            animate={{ x: ["-100%", "220%"] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: [0.45, 0, 0.55, 1] }}
          />
        </span>
        Charting
      </span>
    );
  }
  if (status === "FAILED") {
    return (
      <span className="shrink-0 rounded-full bg-[rgba(207,102,121,0.12)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--danger)]">
        Failed
      </span>
    );
  }
  return (
    <span className="shrink-0 rounded-full bg-[rgba(127,176,105,0.14)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--success)]">
      Ready
    </span>
  );
}
