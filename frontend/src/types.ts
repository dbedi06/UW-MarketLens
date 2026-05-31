// PLACEHOLDER types — mirror of backend/app/schemas.py.
// Keep in lockstep with the backend until S0 finalizes the real schema.

export type Band = "HIGH" | "MEDIUM" | "LOW";
export type Verdict = "HIGH" | "MEDIUM" | "LOW" | "UNVERIFIABLE";

export interface Subscores {
  liquidity_health: number;
  anomaly: number;
  resolution_quality: number;
}

export interface FeatureContribution {
  feature: string;
  value: number;
  shap: number;
}

export interface AnomalyResult {
  score: number;
  flagged_windows: number;
  top_features: string[];
  top_contributions?: FeatureContribution[];
}

export interface ResolutionSnippet {
  title?: string;
  description?: string;
  url: string;
}

export interface ResolutionVerdict {
  verdict: Verdict;
  reasoning: string;
  supporting_sources: string[];
  supporting_snippets?: ResolutionSnippet[];
}

export interface Tags {
  departments: string[];
  course_applicability: number;
}

export interface Citation {
  apa: string;
  mla: string;
  bibtex: string;
  ris?: string;
  reliability_flag: string;
}

export type Severity = "good" | "warn" | "bad";
export type Factor = "liquidity" | "anomaly" | "resolution";

export interface ReasonItem {
  factor: Factor;
  severity: Severity;
  headline: string;
  detail: string;
}

export interface MarketMeta {
  volume_usd: number;
  liquidity_usd: number;
  unique_traders: number;
  end_date: string;
  resolved: boolean;
}

export interface AnomalyPoint {
  window_index: number;
  price: number;
  anomaly_value: number;
  flagged: boolean;
}

export interface PendingTag {
  market_url: string;
  market_question: string;
  suggested_departments: string[];
  course_applicability: number;
  verified: boolean;
}

export interface MarketScore {
  market_url: string;
  market_question: string;
  reliability_score: number;
  band: Band;
  headline: string;
  reasons: ReasonItem[];
  meta: MarketMeta;
  anomaly_series: AnomalyPoint[];
  subscores: Subscores;
  anomaly: AnomalyResult;
  resolution: ResolutionVerdict;
  tags: Tags;
  citation: Citation;
  as_of: string;
  snapshot_id: string;
  permalink: string;
  source?: "live" | "mock";
}

export interface LibraryEntry {
  market_url: string;
  market_question: string;
  reliability_score: number;
  band: Band;
  departments: string[];
  verified: boolean;
}
