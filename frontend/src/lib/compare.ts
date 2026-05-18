// Pure delta helpers for the side-by-side comparison.

import type { MarketScore } from "../types";

export type Metric = {
  key: string;
  label: string;
  a: number;
  b: number;
  delta: number; // b - a
};

export function metrics(a: MarketScore, b: MarketScore): Metric[] {
  return [
    {
      key: "overall",
      label: "Reliability",
      a: a.reliability_score,
      b: b.reliability_score,
      delta: b.reliability_score - a.reliability_score,
    },
    {
      key: "liquidity",
      label: "Liquidity health",
      a: a.subscores.liquidity_health,
      b: b.subscores.liquidity_health,
      delta: b.subscores.liquidity_health - a.subscores.liquidity_health,
    },
    {
      key: "anomaly",
      label: "Trading-pattern integrity",
      a: a.subscores.anomaly,
      b: b.subscores.anomaly,
      delta: b.subscores.anomaly - a.subscores.anomaly,
    },
    {
      key: "resolution",
      label: "Resolution quality",
      a: a.subscores.resolution_quality,
      b: b.subscores.resolution_quality,
      delta: b.subscores.resolution_quality - a.subscores.resolution_quality,
    },
  ];
}

// Which side is stronger overall (higher reliability), for a headline.
export function leader(a: MarketScore, b: MarketScore): "a" | "b" | "tie" {
  if (a.reliability_score === b.reliability_score) return "tie";
  return a.reliability_score > b.reliability_score ? "a" : "b";
}
