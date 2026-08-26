import { create } from "zustand";
import type { BrainEdge, BrainNode } from "@/types/brain";

interface BrainUIState {
  hoveredId: string | null;
  selectedId: string | null;
  viewMode: "graph" | "list";
  /** Domain filter — null shows everything. */
  domainFilter: string | null;
  /** Combine mode: pick two concepts to fuse into a new one. */
  combineMode: boolean;
  combinePicks: string[];
  setHovered: (id: string | null) => void;
  select: (id: string | null) => void;
  setViewMode: (mode: "graph" | "list") => void;
  setDomainFilter: (domain: string | null) => void;
  toggleCombine: () => void;
  pickForCombine: (id: string) => void;
}

export const useBrainStore = create<BrainUIState>()((set) => ({
  hoveredId: null,
  selectedId: null,
  viewMode: "graph",
  domainFilter: null,
  combineMode: false,
  combinePicks: [],
  setHovered: (id) => set({ hoveredId: id }),
  select: (id) => set({ selectedId: id }),
  setViewMode: (viewMode) => set({ viewMode }),
  setDomainFilter: (domainFilter) => set({ domainFilter }),
  toggleCombine: () =>
    set((s) => ({ combineMode: !s.combineMode, combinePicks: [], selectedId: null })),
  pickForCombine: (id) =>
    set((s) => {
      if (s.combinePicks.includes(id)) return { combinePicks: s.combinePicks.filter((x) => x !== id) };
      if (s.combinePicks.length >= 2) return { combinePicks: [s.combinePicks[1]!, id] };
      return { combinePicks: [...s.combinePicks, id] };
    }),
}));

/** Non-hook accessor so sigma reducers can read fresh state without re-binding. */
export const brainUI = () => useBrainStore.getState();

export function neighborsOf(graph: { edges: BrainEdge[] }, id: string): Set<string> {
  const result = new Set<string>();
  for (const edge of graph.edges) {
    if (edge.source === id) result.add(edge.target);
    if (edge.target === id) result.add(edge.source);
  }
  return result;
}

export function visibleNodes(nodes: BrainNode[], domainFilter: string | null): BrainNode[] {
  if (!domainFilter) return nodes;
  return nodes.filter((n) => n.domain === domainFilter);
}
