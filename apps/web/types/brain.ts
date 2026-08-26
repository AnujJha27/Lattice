export type MasteryState = "UNSEEN" | "AVAILABLE" | "LEARNING" | "FAMILIAR" | "MASTERED";

export interface BrainNode {
  id: string;
  name: string;
  domain: string | null;
  difficulty: number | null;
  mastery_score: number;
  state: MasteryState;
  interest_score: number;
}

export interface BrainEdge {
  source: string;
  target: string;
  type: "PREREQUISITE" | "RELATED_TO" | "PART_OF";
  confidence?: number | null;
  created_by?: string | null;
}

export interface BrainGraph {
  nodes: BrainNode[];
  edges: BrainEdge[];
  generated_at: string;
}

export interface ConceptRef {
  id: string;
  canonical_name: string;
  description: string | null;
  domain: string | null;
  difficulty: number | null;
}

export interface ConceptDetail extends ConceptRef {
  prerequisites: ConceptRef[];
  dependents: ConceptRef[];
  related: ConceptRef[];
  mastery_score: number;
  state: MasteryState;
  in_brain: boolean;
}

/** Mirrors backend mastery colors — see app/globals.css tokens. */
export const MASTERY_COLORS: Record<MasteryState, string> = {
  UNSEEN: "#8ea0c8",
  AVAILABLE: "#a8bee6",
  LEARNING: "#7fb3ff",
  FAMILIAR: "#e8dcc6",
  MASTERED: "#e6c07a",
};

const DOMAIN_PALETTE = [
  "#8b7cf7", // violet
  "#38bdf8", // sky
  "#fb923c", // orange
  "#4ade80", // green
  "#f472b6", // pink
  "#facc15", // yellow
  "#2dd4bf", // teal
  "#a78bfa", // light violet
];

export function domainColor(domain: string | null): string {
  if (!domain) return DOMAIN_PALETTE[0]!;
  let hash = 0;
  for (let i = 0; i < domain.length; i++) {
    hash = (hash * 31 + domain.charCodeAt(i)) >>> 0;
  }
  return DOMAIN_PALETTE[hash % DOMAIN_PALETTE.length]!;
}

export function nodeSize(node: BrainNode): number {
  return 5 + (node.mastery_score / 100) * 8 + (node.interest_score / 100) * 4;
}
