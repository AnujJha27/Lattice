"use client";

import { Download, Share2 } from "lucide-react";
import { useRef } from "react";
import type { PortraitModel } from "@/types/portrait";
import { PORTRAIT_PALETTES, type PortraitTheme } from "@/lib/portraitThemes";

export function PortraitShareCard({ portrait, theme }: { portrait: PortraitModel; theme: PortraitTheme }) {
  const svg = useRef<SVGSVGElement>(null);
  const palette = PORTRAIT_PALETTES[theme];
  const highlights = [...portrait.anchors, ...portrait.bridges, ...portrait.frontiers].slice(0, 9);
  const summary = `${portrait.summary.concept_count} concepts across ${portrait.summary.domain_count} domains. ${portrait.narrative}`;

  const download = () => {
    const blob = serializedCard();
    if (!blob) return;
    save(blob, `lattice-portrait-v${portrait.version}-${theme.toLowerCase()}.svg`);
  };

  const downloadPng = () => {
    const blob = serializedCard();
    if (!blob) return;
    const sourceUrl = URL.createObjectURL(blob);
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 1520;
      canvas.height = 1120;
      canvas.getContext("2d")?.drawImage(image, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((png) => {
        if (png) save(png, `lattice-portrait-v${portrait.version}-${theme.toLowerCase()}.png`);
        URL.revokeObjectURL(sourceUrl);
      }, "image/png");
    };
    image.src = sourceUrl;
  };

  const serializedCard = () => {
    if (!svg.current) return null;
    const copy = svg.current.cloneNode(true) as SVGSVGElement;
    copy.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    return new Blob([new XMLSerializer().serializeToString(copy)], { type: "image/svg+xml" });
  };

  const save = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const share = async () => {
    if (navigator.share) await navigator.share({ title: "My Lattice portrait", text: summary });
    else await navigator.clipboard?.writeText(summary);
  };

  return <section className="mt-8 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6" aria-labelledby="portrait-edition-heading">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div><p className="eyebrow mb-2">Phase 6 · {theme} edition</p><h2 id="portrait-edition-heading" className="atlas-title text-2xl">A card for the shape of your curiosity.</h2><p className="mt-2 max-w-2xl text-sm text-[var(--text-secondary)]">A private, source-free share card. It exports the reading and signal structure, never your profile photo or licensed source imagery.</p></div>
      <div className="flex flex-wrap gap-2"><button type="button" onClick={download} className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--accent)]"><Download className="h-3.5 w-3.5" aria-hidden />Download SVG</button><button type="button" onClick={downloadPng} className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--accent)]"><Download className="h-3.5 w-3.5" aria-hidden />Download PNG</button><button type="button" onClick={() => void share()} className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--accent)]"><Share2 className="h-3.5 w-3.5" aria-hidden />Share summary</button></div>
    </div>
    <svg ref={svg} viewBox="0 0 760 560" className="mt-5 w-full rounded-xl border border-[var(--border-subtle)]" role="img" aria-labelledby="share-card-title share-card-description">
      <title id="share-card-title">Lattice portrait, {theme} edition</title>
      <desc id="share-card-description">A share card showing the learner&apos;s portrait summary and selected knowledge signals.</desc>
      <defs><radialGradient id="edition-sky"><stop offset="0" stopColor={palette.skyStart} /><stop offset="1" stopColor={palette.skyEnd} /></radialGradient></defs>
      <rect width="760" height="560" fill="url(#edition-sky)" />
      <circle cx="600" cy="170" r="150" fill={palette.figure} fillOpacity="0.1" />
      <path d="M80 410C180 110 580 80 690 360" fill="none" stroke={palette.rule} strokeOpacity="0.14" strokeDasharray="2 12" />
      <path d="M110 455C250 170 520 150 660 410" fill="none" stroke={palette.frontier} strokeOpacity="0.2" strokeDasharray="1 10" />
      {highlights.map((item, index) => {
        const x = 105 + (index % 5) * 135;
        const y = 170 + Math.floor(index / 5) * 120;
        const color = index < portrait.anchors.length ? palette.anchor : index < portrait.anchors.length + portrait.bridges.length ? palette.bridge : palette.frontier;
        return <g key={item.id}><path d={`M380 300 L${x} ${y}`} stroke={color} strokeOpacity="0.25" /><circle cx={x} cy={y} r={9 + Math.round(item.score * 10)} fill={color} fillOpacity="0.7" /><circle cx={x - 3} cy={y - 3} r="2" fill={palette.rule} /><text x={x} y={y + 31} textAnchor="middle" fill={palette.rule} fillOpacity="0.8" fontSize="10" fontFamily="ui-monospace, monospace">{item.name.slice(0, 18)}</text></g>;
      })}
      <circle cx="380" cy="300" r="56" fill={palette.figure} fillOpacity="0.18" stroke={palette.rule} strokeOpacity="0.45" />
      <path d="M352 300c0-18 12-30 28-30s28 12 28 30c0 13-7 22-15 27 17 7 27 18 34 37H333c7-19 17-30 34-37-8-5-15-14-15-27Z" fill={palette.rule} fillOpacity="0.32" />
      <text x="42" y="52" fill={palette.rule} fontSize="11" letterSpacing="3" fontFamily="ui-monospace, monospace">LATTICE · INTELLECTUAL PORTRAIT</text>
      <text x="42" y="102" fill={palette.rule} fontSize="30" fontFamily="Georgia, serif">The shape of your curiosity.</text>
      <text x="42" y="515" fill={palette.rule} fillOpacity="0.62" fontSize="10" letterSpacing="2" fontFamily="ui-monospace, monospace">{theme.toUpperCase()} EDITION · V{portrait.version} · DATA-BOUND</text>
    </svg>
  </section>;
}
