// PILLAR 1 evidence — the suspicious window in context. Gradient area that
// draws in on mount; the flagged span is shaded.

import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip,
  ReferenceArea, CartesianGrid,
} from "recharts";
import { motion } from "framer-motion";
import type { AnomalyPoint } from "../types";
import { fadeUp } from "../lib/motion";
import SectionHeading from "../ui/SectionHeading";

type FlaggedSpan = { x1: number; x2: number };

// Group flagged windows into contiguous runs so the chart shades the
// actual suspicious spans, not the entire range between the first and
// last flag. With 700+ windows and flags at both ends (a market that
// resolved with anomalous activity at open *and* close), shading the
// whole span makes it look like 95% of the chart is suspicious.
function flaggedSpans(series: AnomalyPoint[]): FlaggedSpan[] {
  const out: FlaggedSpan[] = [];
  let i = 0;
  while (i < series.length) {
    if (!series[i].flagged) { i += 1; continue; }
    const start = series[i].window_index;
    let end = start;
    while (i < series.length && series[i].flagged) {
      end = series[i].window_index;
      i += 1;
    }
    // Pad each span ±0.5 windows so single-window flags (x1===x2)
    // still render as a visible band — recharts ReferenceArea with
    // zero domain width draws nothing.
    out.push({ x1: start - 0.5, x2: end + 0.5 });
  }
  return out;
}

export default function AnomalyChart({ series }: { series: AnomalyPoint[] }) {
  const flagged = series.filter((p) => p.flagged);
  const hasFlag = flagged.length > 0;
  const spans = flaggedSpans(series);

  // Auto-scale Y-axis when the implied probability barely moves
  // (e.g. a long-shot World Cup team trading between 16.7%–16.8%).
  // On the hardcoded [0, 1] axis those reads as a flat line — visually
  // identical to the pre-fix bug where every window got `yes_price`.
  // Widen to at least an 8pp window so the movement is visible.
  const prices = series.map((p) => p.price).filter((v) => Number.isFinite(v));
  const pMin = prices.length ? Math.min(...prices) : 0;
  const pMax = prices.length ? Math.max(...prices) : 1;
  const rangeNarrow = prices.length > 1 && pMax - pMin < 0.08;
  const yDomain: [number, number] = rangeNarrow
    ? [Math.max(0, pMin - 0.02), Math.min(1, pMax + 0.02)]
    : [0, 1];
  const yAutoScaled = rangeNarrow;

  // When auto-scaled, force 5 evenly-spaced ticks across the domain.
  // Without this recharts' nice-tick heuristic picks uneven values on
  // narrow domains (e.g. 15.8 / 16.5 / 18.0 / 19.1 for a market
  // trading 16-17%), which reads as "broken" to users expecting round
  // percentage gridlines.
  const yTicks: number[] | undefined = yAutoScaled
    ? Array.from({ length: 5 }, (_, i) =>
        yDomain[0] + ((yDomain[1] - yDomain[0]) * i) / 4
      )
    : undefined;

  return (
    <motion.div variants={fadeUp} className="card p-6">
      <SectionHeading
        eyebrow="Evidence"
        title="Trade-window price path"
        sub={
          (hasFlag
            ? "The shaded spans are the windows the anomaly model flagged. The Feature attribution panel below explains why the most-anomalous one scored as unusual."
            : "No window was flagged: the price path stays within normal market behavior.")
          + (yAutoScaled
            ? " Y-axis zoomed to the traded range — this outcome moved less than 8pp."
            : "")
        }
      />
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={256}>
          <AreaChart data={series} margin={{ top: 8, right: 12, bottom: 4, left: -10 }}>
            <CartesianGrid stroke="#E4DFD5" vertical={false} />
            <XAxis
              dataKey="window_index"
              tick={{ fontSize: 11, fill: "#8a8278", fontFamily: "JetBrains Mono Variable, monospace" }}
              tickLine={false}
              axisLine={{ stroke: "#E4DFD5" }}
            />
            <YAxis
              domain={yDomain}
              ticks={yTicks}
              tick={{ fontSize: 11, fill: "#8a8278", fontFamily: "JetBrains Mono Variable, monospace" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${(v * 100).toFixed(yAutoScaled ? 1 : 0)}%`}
            />
            <Tooltip
              formatter={(v) => [`${Math.round(Number(v) * 100)}%`, "Implied prob."]}
              labelFormatter={(l) => `Window ${l}`}
              contentStyle={{
                borderRadius: 4,
                border: "1px solid #E4DFD5",
                fontSize: 12,
                fontFamily: "JetBrains Mono Variable, monospace",
              }}
            />
            {spans.map((s, i) => (
              // Hardcoded hex (matches the OG card). recharts drops a
              // `rgb(var(--bad))` fill — its color handling doesn't
              // resolve CSS vars — which made the shading invisible
              // in-page while the snapshot card still showed it.
              // No text label: it collided with the left-edge y-axis
              // ticks; the subhead already explains the shaded spans.
              <ReferenceArea
                key={`${s.x1}-${s.x2}-${i}`}
                x1={s.x1}
                x2={s.x2}
                fill="#E0584F"
                fillOpacity={0.2}
              />
            ))}
            <Area
              type="monotone"
              dataKey="price"
              stroke="#4B2E83"
              strokeWidth={3}
              fill="#4B2E83"
              fillOpacity={0.08}
              animationDuration={1100}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
