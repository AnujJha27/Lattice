"use client";

import { motion } from "motion/react";
import { useMemo } from "react";

export function StarfieldEmergence({ count = 14, className = "" }: { count?: number; className?: string }) {
  const stars = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        id: i,
        x: 8 + Math.random() * 84,
        y: 15 + Math.random() * 70,
        size: Math.random() * 1.8 + 0.8,
        warm: Math.random() < 0.25,
        delay: i * 0.14 + Math.random() * 0.3,
      })),
    [count],
  );

  return (
    <div className={`relative overflow-hidden ${className}`} aria-hidden>
      {stars.map((s) => (
        <motion.span
          key={s.id}
          className="absolute rounded-full"
          style={{
            left: `${s.x}%`,
            top: `${s.y}%`,
            width: s.size,
            height: s.size,
            background: s.warm ? "#C9A961" : "#EAE5D9",
            boxShadow: s.warm ? "0 0 6px rgba(201,169,97,0.7)" : "0 0 4px rgba(234,229,217,0.5)",
          }}
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: [0, 1, 0.85], scale: [0, 1, 1] }}
          transition={{ duration: 1.4, delay: s.delay, ease: [0.22, 1, 0.36, 1], repeat: Infinity, repeatDelay: 3 + Math.random() * 2, repeatType: "reverse" }}
        />
      ))}
    </div>
  );
}
