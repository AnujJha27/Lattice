"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView, useMotionValue, useSpring } from "motion/react";
import { cn } from "@/lib/utils";

/** Fade-and-rise entrance. Stagger children with `delay`. */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/** Animated number that counts up when scrolled into view. */
export function CountUp({
  value,
  duration = 1.2,
  className,
}: {
  value: number;
  duration?: number;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const progress = Math.min((now - start) / (duration * 1000), 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(eased * value));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, value, duration]);

  return (
    <span ref={ref} className={className}>
      {display}
    </span>
  );
}

/** Aurora — two vast, slow-drifting nebulas behind the content. */
export function AuroraBackground({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      <div className="aurora-blob aurora-a" />
      <div className="aurora-blob aurora-b" />
    </div>
  );
}

/** BorderBeam — a comet of brass light orbiting a card's border. */
export function BorderBeam({
  size = 120,
  duration = 6,
  className,
}: {
  size?: number;
  duration?: number;
  className?: string;
}) {
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-0 rounded-[inherit] border border-transparent [mask-clip:padding-box,border-box] [mask-composite:intersect]",
        className,
      )}
      style={{
        maskImage:
          "linear-gradient(#000 0 0), linear-gradient(#000 0 0)",
      }}
    >
      <motion.div
        className="absolute aspect-square rounded-full"
        style={{
          width: size,
          background:
            "conic-gradient(from 0deg, transparent 0 340deg, rgba(201,169,97,0.9) 355deg, transparent 360deg)",
          offsetPath: "rect(0 auto auto 0 round 12px)",
          offsetRotate: "0deg",
          animation: `border-orbit ${duration}s linear infinite`,
        }}
      />
    </div>
  );
}

/** Magnetic hover — subtle pull toward the cursor (aceternity-style). */
export function Magnetic({ children, strength = 0.25 }: { children: React.ReactNode; strength?: number }) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 200, damping: 18 });
  const sy = useSpring(y, { stiffness: 200, damping: 18 });

  return (
    <motion.div
      style={{ x: sx, y: sy }}
      onMouseMove={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        x.set((e.clientX - rect.left - rect.width / 2) * strength);
        y.set((e.clientY - rect.top - rect.height / 2) * strength);
      }}
      onMouseLeave={() => {
        x.set(0);
        y.set(0);
      }}
      className="inline-block"
    >
      {children}
    </motion.div>
  );
}
