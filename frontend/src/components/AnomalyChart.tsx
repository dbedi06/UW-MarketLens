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

export default function AnomalyChart({ series }: { series: AnomalyPoint[] }) {
  const flagged = series.filter((p) => p.flagged);
  const hasFlag = flagged.length > 0;
  const flagStart = hasFlag ? flagged[0].window_index : 0;
  const flagEnd = hasFlag ? flagged[flagged.length - 1].window_index : 0;

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

  return (
    <motion.div variants={fadeUp} className="card p-6">
      <SectionHeading
        eyebrow="Evidence"
        title="Trade-window price path"
        sub={
          (hasFlag
            ? "The shaded span is the window the anomaly model flagged: an unusual price move on thin volume."
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
            {hasFlag && (
              <ReferenceArea
                x1={flagStart}
                x2={flagEnd}
                fill="#b3261e"
                fillOpacity={0.07}
                label={{ value: "flagged", fontSize: 10, fill: "#b3261e" }}
              />
            )}
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
