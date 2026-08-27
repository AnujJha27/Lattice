"use client";

import { useEffect, useState, type KeyboardEvent, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { PortraitModel, PortraitNode, PortraitThread, PortraitVisualSource } from "@/types/portrait";
import { insidePoint, orbitPoint, PORTRAIT_CENTER } from "@/lib/portraitLayout";
import { PUBLIC_CONFIG } from "@/lib/config";
import { trackPortraitEvent } from "@/lib/portraitAnalytics";
import { createClient } from "@/lib/supabase/client";

type Point = { x: number; y: number };

export type PortraitSelection = {
  kind: "anchor" | "bridge" | "frontier" | "emerging_thread" | "dormant_thread" | "visual";
  item: PortraitNode | PortraitThread | PortraitVisualSource;
};

function activate(event: KeyboardEvent<SVGGElement>, onSelect: () => void) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onSelect();
  }
}

function Region({ point, label, score, tone, snapshotId, elementId, onSelect, mobileSecondary = false, children }: {
  point: Point;
  label: string;
  score: number;
  tone: "anchor" | "bridge" | "frontier" | "emerging" | "dormant";
  snapshotId: string;
  elementId: string;
  onSelect: () => void;
  mobileSecondary?: boolean;
  children?: ReactNode;
}) {
  const color = tone === "dormant" ? "#565e73" : tone === "emerging" ? "#d8ba78" : tone === "frontier" ? "#7aa5d8" : "#c9a961";
  const radius = 8 + Math.round(score * 14);
  return <g role="button" tabIndex={0} aria-label={`${label}, ${tone}, signal ${Math.round(score * 100)} percent`} onMouseEnter={() => trackPortraitEvent("portrait_element_hovered", snapshotId, elementId)} onClick={onSelect} onKeyDown={(event) => activate(event, onSelect)} className={`group cursor-pointer outline-none${mobileSecondary ? " portrait-mobile-secondary" : ""}`} opacity={tone === "dormant" ? 0.5 : 1}>
    <title>{label} · {tone} · signal {Math.round(score * 100)}%</title>
    <circle cx={point.x} cy={point.y} r={radius + 9} fill="transparent" stroke={color} strokeOpacity="0.16" strokeWidth="1" />
    <circle cx={point.x} cy={point.y} r={radius} fill={color} fillOpacity={tone === "anchor" ? 0.75 : 0.28} stroke={color} strokeWidth="1.5" />
    <circle cx={point.x - radius * 0.25} cy={point.y - radius * 0.25} r={Math.max(2, radius * 0.2)} fill="#f4eddd" fillOpacity="0.8" />
    <circle cx={point.x} cy={point.y} r={radius + 13} fill="none" stroke="#f4eddd" strokeWidth="2" className="pointer-events-none opacity-0 transition-opacity group-focus-visible:opacity-100" />
    {children}
  </g>;
}

function RegionTransition({ origin, reducedMotion, className, children }: {
  origin?: Point;
  reducedMotion: boolean;
  className?: string;
  children: ReactNode;
}) {
  return <motion.g initial={reducedMotion ? false : { opacity: 0, scale: 0.86 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.86 }} transition={reducedMotion ? { duration: 0 } : { duration: 0.35, ease: "easeOut" }} style={origin ? { transformOrigin: `${origin.x}px ${origin.y}px` } : undefined} className={className}>{children}</motion.g>;
}

export function PortraitRenderer({ portrait, onSelect }: { portrait: PortraitModel; onSelect: (selection: PortraitSelection) => void }) {
  const anchors = portrait.anchors.slice(0, 8);
  const bridges = portrait.bridges.slice(0, 5);
  const frontiers = portrait.frontiers.slice(0, 8);
  const emerging = portrait.emerging_threads.slice(0, 5);
  const dormant = portrait.dormant_threads.slice(0, 4);
  const visuals = portrait.visual_sources.slice(0, 8);
  const reducedMotion = useReducedMotion() ?? false;
  const select = (kind: PortraitSelection["kind"], item: PortraitSelection["item"]) => {
    const elementId = "asset_id" in item ? item.asset_id : item.id;
    trackPortraitEvent("portrait_element_opened", portrait.snapshot_id, elementId);
    if (kind === "visual") trackPortraitEvent("portrait_visual_source_opened", portrait.snapshot_id, elementId);
    onSelect({ kind, item } as PortraitSelection);
  };

  return <div className="relative overflow-hidden rounded-2xl border border-[var(--border-strong)] bg-[var(--bg-surface)] shadow-[var(--shadow-lg)]" aria-label="Interactive intellectual portrait">
    <svg viewBox="0 0 1000 760" className="block h-auto w-full" role="group" aria-labelledby="portrait-title portrait-description">
      <title id="portrait-title">Your intellectual portrait</title>
      <desc id="portrait-description">An anonymous human silhouette surrounded by concepts from your Lattice Brain. Concepts inside the silhouette are anchors; crossing lines are bridges; outer regions are frontiers and threads.</desc>
      <defs>
        <radialGradient id="portrait-sky" cx="50%" cy="42%" r="68%"><stop offset="0" stopColor="#19233a" /><stop offset="0.72" stopColor="#101624" /><stop offset="1" stopColor="#0a0e1a" /></radialGradient>
        <linearGradient id="portrait-figure" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#eae5d9" stopOpacity="0.14" /><stop offset="0.52" stopColor="#c9a961" stopOpacity="0.18" /><stop offset="1" stopColor="#7aa5d8" stopOpacity="0.12" /></linearGradient>
        <filter id="portrait-soft-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="12" /></filter>
        <clipPath id="figure-mask"><path d="M500 72c-53 0-86 38-86 89 0 43 21 72 47 88-16 22-42 34-81 53-56 28-84 79-99 143l-31 247h500l-31-247c-15-64-43-115-99-143-39-19-65-31-81-53 26-16 47-45 47-88 0-51-33-89-86-89Z" /></clipPath>
      </defs>
      <rect width="1000" height="760" fill="url(#portrait-sky)" />
      <path d="M120 440C270 110 730 110 880 440" fill="none" stroke="#c9a961" strokeOpacity="0.09" strokeDasharray="2 14" />
      <path d="M180 595C310 210 690 210 820 595" fill="none" stroke="#7aa5d8" strokeOpacity="0.08" strokeDasharray="1 12" />
      <circle cx={PORTRAIT_CENTER.x} cy={PORTRAIT_CENTER.y + 80} r="250" fill="#c9a961" fillOpacity="0.08" filter="url(#portrait-soft-glow)" />
      {emerging.map((thread, index) => { const point = orbitPoint(thread.id, index, emerging.length, 310); return <ellipse key={`emerging-orbit-${thread.id}`} className={index >= 3 ? "portrait-mobile-secondary" : undefined} cx={PORTRAIT_CENTER.x} cy={PORTRAIT_CENTER.y} rx={Math.abs(point.x - PORTRAIT_CENTER.x) + 38} ry={Math.abs(point.y - PORTRAIT_CENTER.y) + 26} fill="none" stroke="#d8ba78" strokeOpacity="0.18" strokeDasharray="5 11" />; })}
      <path d="M500 72c-53 0-86 38-86 89 0 43 21 72 47 88-16 22-42 34-81 53-56 28-84 79-99 143l-31 247h500l-31-247c-15-64-43-115-99-143-39-19-65-31-81-53 26-16 47-45 47-88 0-51-33-89-86-89Z" fill="url(#portrait-figure)" stroke="#eae5d9" strokeOpacity="0.26" strokeWidth="2" />
      <g clipPath="url(#figure-mask)"><path d="M338 650C410 560 417 420 500 340c83 80 90 220 162 310" fill="none" stroke="#c9a961" strokeOpacity="0.13" strokeWidth="36" /><path d="M420 180c40 28 120 28 160 0" fill="none" stroke="#eae5d9" strokeOpacity="0.15" strokeWidth="2" /></g>
      <AnimatePresence initial={false} mode="sync">
        {bridges.map((item, index) => { const start = insidePoint(item.id, index); const end = orbitPoint(item.id, index, bridges.length, 330); return <RegionTransition key={`bridge-line-${item.id}`} origin={start} reducedMotion={reducedMotion} className={index >= 3 ? "portrait-mobile-secondary" : undefined}><path d={`M${start.x} ${start.y} C${start.x - 70} ${start.y - 60}, ${end.x + 70} ${end.y + 60}, ${end.x} ${end.y}`} fill="none" stroke="#c9a961" strokeOpacity="0.4" strokeWidth="2" strokeDasharray="7 7" /><Region point={start} label={item.name} score={item.score} tone="bridge" snapshotId={portrait.snapshot_id} elementId={item.id} onSelect={() => select("bridge", item)} mobileSecondary={index >= 3} /></RegionTransition>; })}
        {anchors.map((item, index) => <RegionTransition key={`anchor-${item.id}`} origin={insidePoint(item.id, index)} reducedMotion={reducedMotion}><Region point={insidePoint(item.id, index)} label={item.name} score={item.score} tone="anchor" snapshotId={portrait.snapshot_id} elementId={item.id} onSelect={() => select("anchor", item)} mobileSecondary={index >= 4} /></RegionTransition>)}
        {frontiers.map((item, index) => { const point = orbitPoint(item.id, index, frontiers.length, 305); return <RegionTransition key={`frontier-${item.id}`} origin={point} reducedMotion={reducedMotion} className={index >= 4 ? "portrait-mobile-secondary" : undefined}><path d={`M${PORTRAIT_CENTER.x} ${PORTRAIT_CENTER.y + 8} L${point.x} ${point.y}`} stroke="#7aa5d8" strokeOpacity="0.12" strokeDasharray="2 9" /><Region point={point} label={item.name} score={item.score} tone="frontier" snapshotId={portrait.snapshot_id} elementId={item.id} onSelect={() => select("frontier", item)} mobileSecondary={index >= 4} /></RegionTransition>; })}
        {emerging.map((item, index) => <RegionTransition key={`emerging-${item.id}`} origin={orbitPoint(item.id, index, emerging.length, 390)} reducedMotion={reducedMotion}><Region point={orbitPoint(item.id, index, emerging.length, 390)} label={item.name} score={item.score} tone="emerging" snapshotId={portrait.snapshot_id} elementId={item.id} onSelect={() => select("emerging_thread", item)} mobileSecondary={index >= 3} /></RegionTransition>)}
        {dormant.map((item, index) => <RegionTransition key={`dormant-${item.id}`} origin={orbitPoint(`${item.id}-dormant`, index, dormant.length, 360)} reducedMotion={reducedMotion}><Region point={orbitPoint(`${item.id}-dormant`, index, dormant.length, 360)} label={item.name} score={item.score} tone="dormant" snapshotId={portrait.snapshot_id} elementId={item.id} onSelect={() => select("dormant_thread", item)} mobileSecondary={index >= 2} /></RegionTransition>)}
        {visuals.map((source, index) => <VisualRegion key={`visual-${source.asset_id}`} source={source} point={orbitPoint(source.asset_id, index, visuals.length, 250)} snapshotId={portrait.snapshot_id} onSelect={() => select("visual", source)} mobileSecondary={index >= 4} reducedMotion={reducedMotion} />)}
      </AnimatePresence>
      <text className="portrait-caption" x="500" y="728" textAnchor="middle" fill="#8b93a7" fontFamily="var(--font-plex-mono)" fontSize="11" letterSpacing="3">ANONYMOUS FORM · DATA-BOUND COMPOSITION</text>
    </svg>
    <div className="pointer-events-none absolute inset-x-0 top-0 flex justify-between p-4"><span className="eyebrow">Intellectual portrait</span><span className="eyebrow">v{portrait.version}</span></div>
  </div>;
}

function VisualRegion({ source, point, snapshotId, onSelect, mobileSecondary = false, reducedMotion }: { source: PortraitVisualSource; point: Point; snapshotId: string; onSelect: () => void; mobileSecondary?: boolean; reducedMotion: boolean }) {
  const size = 42;
  const clipId = `visual-${source.asset_id}`;
  const [cacheFailed, setCacheFailed] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const cachedUrl = source.asset.cached_image_url ? `${PUBLIC_CONFIG.apiUrl}${source.asset.cached_image_url}` : null;
  const fallbackUrl = source.asset.thumbnail_url ?? source.asset.image_url;
  const [cachedImageUrl, setCachedImageUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!cachedUrl) {
      setCachedImageUrl(null);
      return;
    }
    let disposed = false;
    let objectUrl: string | null = null;
    const loadCachedImage = async () => {
      try {
        const { data } = await createClient().auth.getSession();
        const response = await fetch(cachedUrl, {
          headers: data.session?.access_token
            ? { Authorization: `Bearer ${data.session.access_token}` }
            : undefined,
        });
        if (!response.ok) throw new Error(`cached image request failed (${response.status})`);
        objectUrl = URL.createObjectURL(await response.blob());
        if (disposed) URL.revokeObjectURL(objectUrl);
        else {
          setCachedImageUrl(objectUrl);
          setCacheFailed(false);
          setImageFailed(false);
        }
      } catch {
        if (!disposed) setCacheFailed(true);
      }
    };
    void loadCachedImage();
    return () => {
      disposed = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [cachedUrl]);
  const imageUrl = cachedImageUrl && !cacheFailed ? cachedImageUrl : fallbackUrl;
  const onImageError = () => { if (cachedImageUrl && !cacheFailed) setCacheFailed(true); else setImageFailed(true); };
  return <motion.g initial={reducedMotion ? false : { opacity: 0, scale: 0.86 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.86 }} transition={reducedMotion ? { duration: 0 } : { duration: 0.35, ease: "easeOut" }} style={{ transformOrigin: `${point.x}px ${point.y}px` }}><g role="button" tabIndex={0} aria-label={`${source.represents}: ${source.asset.title} · ${source.asset.rights_class} visual source`} onMouseEnter={() => trackPortraitEvent("portrait_element_hovered", snapshotId, source.asset_id)} onClick={onSelect} onKeyDown={(event) => activate(event, onSelect)} className={`group cursor-pointer outline-none${mobileSecondary ? " portrait-mobile-secondary" : ""}`}><title>{source.represents} · {source.asset.title} · {source.asset.rights_class}</title><defs><clipPath id={clipId}><rect x={point.x - size} y={point.y - size / 2} width={size * 2} height={size} rx="6" /></clipPath></defs><rect x={point.x - size - 3} y={point.y - size / 2 - 3} width={size * 2 + 6} height={size + 6} rx="9" fill="#101624" stroke="#c9a961" strokeOpacity="0.45" /><rect x={point.x - size - 6} y={point.y - size / 2 - 6} width={size * 2 + 12} height={size + 12} rx="11" fill="none" stroke="#f4eddd" strokeWidth="2" className="pointer-events-none opacity-0 transition-opacity group-focus-visible:opacity-100" />{imageFailed ? <text x={point.x} y={point.y + 3} textAnchor="middle" fill="#8b93a7" fontSize="9">source unavailable</text> : <image href={imageUrl} onError={onImageError} x={point.x - size} y={point.y - size / 2} width={size * 2} height={size} preserveAspectRatio="xMidYMid slice" clipPath={`url(#${clipId})`} opacity="0.84" />}</g></motion.g>;
}
