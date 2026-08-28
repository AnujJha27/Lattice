"use client";

import { useEffect, useState } from "react";
import { PORTRAIT_THEMES, readPortraitTheme, type PortraitTheme } from "@/lib/portraitThemes";

export function usePortraitTheme() {
  const [theme, setTheme] = useState<PortraitTheme>("Editorial");
  useEffect(() => setTheme(readPortraitTheme()), []);
  const updateTheme = (next: PortraitTheme) => {
    setTheme(next);
    window.localStorage.setItem("lattice-portrait-theme", next);
  };
  return [theme, updateTheme] as const;
}

export function PortraitThemePicker({ theme, onChange }: { theme: PortraitTheme; onChange: (theme: PortraitTheme) => void }) {
  return <label className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
    <span className="eyebrow">Edition</span>
    <select aria-label="Portrait theme" value={theme} onChange={(event) => onChange(event.target.value as PortraitTheme)} className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-1.5 text-xs text-[var(--text-primary)]">
      {PORTRAIT_THEMES.map((option) => <option key={option}>{option}</option>)}
    </select>
  </label>;
}
