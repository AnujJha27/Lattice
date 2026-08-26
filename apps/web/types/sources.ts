export type IngestStatus = "PENDING" | "FETCHED" | "EXTRACTED" | "CHUNKED" | "EMBEDDED" | "FAILED";

export interface SourceCandidate {
  title: string;
  url: string;
  snippet: string;
  published: string | null;
  provider: string;
  source_type: string;
  authority: number;
  publisher: string | null;
  doi: string | null;
  arxiv_id: string | null;
  authors: string[];
}

export interface RankedCandidate {
  candidate: SourceCandidate;
  factors: Record<string, number | string>;
}

export interface DiscoverResponse {
  candidates: RankedCandidate[];
  policy: string;
  deduped_from: number;
}

export interface SourceAcceptPayload {
  title: string;
  url: string;
  source_type: string;
  authority: number;
  published: string | null;
  publisher?: string | null;
  authors: string[];
  doi?: string | null;
  arxiv_id?: string | null;
  concept_id?: string | null;
}

export interface SourceItem {
  id: string;
  title: string;
  url: string | null;
  source_type: string;
  origin: string;
  publisher: string | null;
  authors: string[];
  published: string | null;
  ingest_status: IngestStatus;
  chunk_count: number;
  created_at: string | null;
}

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  OFFICIAL_DOCUMENTATION: "Docs",
  TEXTBOOK: "Textbook",
  ACADEMIC_PAPER: "Paper",
  UNIVERSITY_MATERIAL: "University",
  GOVERNMENT: "Government",
  STANDARDS_BODY: "Standards",
  REFERENCE_WORK: "Reference",
  PRIMARY_SOURCE: "Primary",
  HIGH_QUALITY_EXPLAINER: "Explainer",
  NEWS: "News",
  BLOG: "Blog",
  FORUM: "Forum",
  USER_SOURCE: "Yours",
  OTHER: "Source",
};
