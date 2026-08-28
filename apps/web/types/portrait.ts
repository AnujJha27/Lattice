export interface PortraitSummary {
  concept_count: number;
  mastered_concept_count: number;
  domain_count: number;
  active_frontier_count: number;
  dominant_domains: string[];
  strongest_thread: string | null;
  emerging_thread: string | null;
  primary_bridge: string | null;
  primary_frontier: string | null;
}

export interface PortraitDomain {
  id: string;
  name: string;
  concept_count: number;
  mastery: number;
  activity: number;
  interest: number;
  recency: number;
  breadth: number;
  depth: number;
  portrait_weight: number;
  dominant_concept_ids: string[];
}

export interface PortraitNode {
  id: string;
  name: string;
  domain: string;
  score: number;
  mastery: number;
  activity: number;
  reason: string;
  connected_domains: string[];
}

export interface PortraitThread {
  id: string;
  name: string;
  score: number;
  concept_ids: string[];
  reason: string;
}

export interface PortraitConnection {
  source_id: string;
  target_id: string;
  type: string;
  confidence: number | null;
}

export interface PortraitChange {
  kind: string;
  text: string;
}

export interface VisualAsset {
  id: string;
  title: string;
  source_url: string;
  canonical_url: string;
  creator: string | null;
  institution: string | null;
  date: string | null;
  license: string | null;
  rights_class: string;
  attribution_text: string | null;
  image_url: string;
  thumbnail_url: string | null;
  width: number | null;
  height: number | null;
  provider: string;
  relevance_score: number;
  aesthetic_score: number;
  rights_score: number;
  quality_score: number;
  cached_image_url: string | null;
}

export interface PortraitVisualSource {
  asset_id: string;
  represents: string;
  concept_ids: string[];
  portrait_role: string;
  asset: VisualAsset;
}

export interface PortraitModel {
  snapshot_id: string;
  generated_at: string;
  version: number;
  algorithm_version: string;
  config_version: string;
  input_hash: string;
  summary: PortraitSummary;
  domains: PortraitDomain[];
  anchors: PortraitNode[];
  bridges: PortraitNode[];
  frontiers: PortraitNode[];
  emerging_threads: PortraitThread[];
  dormant_threads: PortraitThread[];
  connections: PortraitConnection[];
  visual_sources: PortraitVisualSource[];
  evolution: Record<string, number>;
  narrative: string;
  confidence: Record<string, number>;
  changes_since_previous: PortraitChange[];
  portrait_photo_enabled: boolean;
}
