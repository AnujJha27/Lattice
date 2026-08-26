export interface PathwayConcept {
  concept_id: string;
  name: string;
  description: string | null;
  difficulty: number | null;
  mastery_score: number;
  state: string;
  position: number;
}

export interface PathwaySection {
  id: string;
  position: number;
  title: string;
  summary: string | null;
  concepts: PathwayConcept[];
}

export interface PathwaySummary {
  id: string;
  title: string;
  topic: string | null;
  status: "GENERATING" | "READY" | "FAILED" | "ARCHIVED";
  created_at: string | null;
  section_count: number;
  concept_count: number;
  target_depth: "beginner" | "intermediate" | "advanced";
  next_depth: "intermediate" | "advanced" | null;
}

export interface PathwayDetail extends PathwaySummary {
  description: string | null;
  sections: PathwaySection[];
  skipped_edges: number;
}
