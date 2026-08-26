"use client";

import { motion } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * Shimmer — the app-wide skeleton. A soft brass light glides across a quiet
 * plate: smooth linear motion, no opacity pulsing, no flicker.
 */
export function Shimmer({
  className,
  rounded = "rounded-lg",
}: {
  className?: string;
  rounded?: string;
}) {
  return (
    <div
      aria-hidden
      className={cn(
        "relative overflow-hidden bg-[var(--bg-raised)]",
        rounded,
        className,
      )}
    >
      <motion.div
        className="absolute inset-y-0 w-1/2"
        style={{
          background:
            "linear-gradient(90deg, transparent, rgba(201,169,97,0.10), transparent)",
        }}
        animate={{ x: ["-120%", "320%"] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: [0.45, 0, 0.55, 1] }}
      />
    </div>
  );
}

/** Standard stacked-skeleton block for list/card loading states. */
export function ShimmerRows({
  rows = 3,
  className,
  rowClassName,
}: {
  rows?: number;
  className?: string;
  rowClassName?: string;
}) {
  return (
    <div className={cn("space-y-2", className)} aria-busy="true" role="status">
      {Array.from({ length: rows }).map((_, i) => (
        <Shimmer
          key={i}
          className={cn("h-16", rowClassName)}
          rounded="rounded-xl"
        />
      ))}
    </div>
  );
}
