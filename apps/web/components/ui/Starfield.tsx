"use client";

import { useEffect, useRef } from "react";

/**
 * Ambient starfield — a slow-drifting field of faint points, like a long
 * exposure of the night sky. Canvas-based (one draw pass per frame budget),
 * pauses under reduced motion. Inspired by reactbits/aceternity ambience
 * but purpose-built for the Observatory direction.
 */
export function Starfield({ density = 90 }: { density?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let width = (canvas.width = canvas.offsetWidth);
    let height = (canvas.height = canvas.offsetHeight);

    const stars = Array.from({ length: density }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      r: Math.random() * 1.1 + 0.2,
      vx: (Math.random() - 0.5) * 0.05,
      vy: (Math.random() - 0.5) * 0.05,
      tw: Math.random() * Math.PI * 2,
      twSpeed: Math.random() * 0.01 + 0.003,
      warm: Math.random() < 0.12, // a few brass-tinted stars
    }));

    const onResize = () => {
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    };
    window.addEventListener("resize", onResize);

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      for (const s of stars) {
        s.x += s.vx;
        s.y += s.vy;
        s.tw += s.twSpeed;
        if (s.x < 0) s.x = width;
        if (s.x > width) s.x = 0;
        if (s.y < 0) s.y = height;
        if (s.y > height) s.y = 0;

        const alpha = 0.25 + Math.abs(Math.sin(s.tw)) * 0.45;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = s.warm
          ? `rgba(201, 169, 97, ${alpha})`
          : `rgba(234, 229, 217, ${alpha * 0.8})`;
        ctx.fill();
      }
      raf = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [density]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
}
