export const PORTRAIT_THEMES = [
  "Editorial",
  "Constellation",
  "Archive",
  "Topographic",
  "Sigil",
  "Botanical",
  "Orbital",
  "Minimal",
] as const;

export type PortraitTheme = (typeof PORTRAIT_THEMES)[number];

export type PortraitPalette = {
  skyStart: string;
  skyEnd: string;
  figure: string;
  anchor: string;
  bridge: string;
  frontier: string;
  emerging: string;
  dormant: string;
  rule: string;
};

const EDITORIAL: PortraitPalette = {
  skyStart: "#19233a", skyEnd: "#0a0e1a", figure: "#c9a961", anchor: "#c9a961",
  bridge: "#c9a961", frontier: "#7aa5d8", emerging: "#d8ba78", dormant: "#565e73", rule: "#eae5d9",
};

export const PORTRAIT_PALETTES: Record<PortraitTheme, PortraitPalette> = {
  Editorial: EDITORIAL,
  Constellation: { ...EDITORIAL, skyStart: "#1b2144", anchor: "#b9c7ff", bridge: "#d6a8ff", frontier: "#75d4e8", emerging: "#f4cf83" },
  Archive: { ...EDITORIAL, skyStart: "#3b3026", skyEnd: "#17130f", figure: "#d7b77a", anchor: "#e0c18c", bridge: "#c69c68", frontier: "#a8b29c", emerging: "#e8d6a8", rule: "#f0e0c2" },
  Topographic: { ...EDITORIAL, skyStart: "#19333a", skyEnd: "#0a171b", figure: "#83c6aa", anchor: "#8fd3ad", bridge: "#e4bd70", frontier: "#82b5d5", emerging: "#bedb8d", rule: "#d6eadf" },
  Sigil: { ...EDITORIAL, skyStart: "#281b3a", skyEnd: "#100b18", figure: "#e5a8ce", anchor: "#f0c0d8", bridge: "#ddb4ff", frontier: "#9fbbff", emerging: "#f4c889", rule: "#f8e7f2" },
  Botanical: { ...EDITORIAL, skyStart: "#193126", skyEnd: "#0b1711", figure: "#9fc982", anchor: "#b8d887", bridge: "#dfc37b", frontier: "#8cc7a0", emerging: "#d3de8d", rule: "#e5eed9" },
  Orbital: { ...EDITORIAL, skyStart: "#102b42", skyEnd: "#071018", figure: "#8bc9ed", anchor: "#a6ddff", bridge: "#f0c978", frontier: "#71a8ff", emerging: "#b9e3ff", rule: "#e2f3ff" },
  Minimal: { ...EDITORIAL, skyStart: "#17191f", skyEnd: "#0d0e12", figure: "#aeb4bf", anchor: "#e7e9ed", bridge: "#b7a36c", frontier: "#8896aa", emerging: "#c6b986", dormant: "#626876", rule: "#f0f1f3" },
};

export function readPortraitTheme(): PortraitTheme {
  if (typeof window === "undefined") return "Editorial";
  const value = window.localStorage.getItem("lattice-portrait-theme");
  return PORTRAIT_THEMES.includes(value as PortraitTheme) ? value as PortraitTheme : "Editorial";
}
