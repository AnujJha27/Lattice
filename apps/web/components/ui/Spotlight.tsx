"use client";

import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Spotlight card — a brass glow follows the cursor across a hairline card.
 * (Aceternity-style spotlight, implemented natively.)
 */
export function SpotlightCard({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);

  return (
    <div
      ref={ref}
      onMouseMove={(e) => {
        const rect = ref.current?.getBoundingClientRect();
        if (!rect) return;
        setPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
      }}
      onMouseLeave={() => setPos(null)}
      className={cn(
        "group relative overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]",
        className,
      )}
    >
      {pos && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 transition-opacity duration-300"
          style={{
            background: `radial-gradient(340px circle at ${pos.x}px ${pos.y}px, rgba(201,169,97,0.09), transparent 65%)`,
          }}
        />
      )}
      {children}
    </div>
  );
}

/**
 * Shimmer text — a slow light pass across display type. Used once, on the
 * login wordmark. (ReactBits-style shimmer, implemented natively.)
 */
export function ShimmerText({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn("bg-clip-text text-transparent", className)}
      style={{
        backgroundImage:
          "linear-gradient(110deg, #eae5d9 35%, #c9a961 50%, #eae5d9 65%)",
        backgroundSize: "250% 100%",
        animation: "shimmer 6s linear infinite",
      }}
    >
      {children}
    </span>
  );
}
