// PLACEHOLDER types — mirror of backend/app/schemas.py.
// Keep in lockstep with the backend until S0 finalizes the real schema.

export type Band = "HIGH" | "MEDIUM" | "LOW";
export type Verdict = "HIGH" | "MEDIUM" | "LOW" | "UNVERIFIABLE";

export interface Subscores {
  liquidity_health: number;
  anomaly: number;
  resolution_quality: number;
}

export interface AnomalyResult {
  score: number;
  flagged_windows: number;
  top_features: string[];
}

export interface ResolutionVerdict {
  verdict: Verdict;
  reasoning: string;
  supporting_sources: string[];
}

export interface Tags {
  departments: string[];
  course_applicability: number;
}

export interface Citation {
  apa: string;
  mla: string;
  reliability_flag: string;
}

export interface MarketScore {
  market_url: string;
  market_question: string;
  reliability_score: number;
  band: Band;
  subscores: Subscores;
  anomaly: AnomalyResult;
  resolution: ResolutionVerdict;
  tags: Tags;
  citation: Citation;
}

export interface LibraryEntry {
  market_url: string;
  market_question: string;
  reliability_score: number;
  band: Band;
  departments: string[];
  verified: boolean;
}
