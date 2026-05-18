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

  return (
    <motion.div variants={fadeUp} className="card p-6">
      <SectionHeading
        eyebrow="Evidence"
        title="Trade-window price path"
        sub={
          hasFlag
            ? "The shaded span is the window the anomaly model flagged: an unusual price move on thin volume."
            : "No window was flagged: the price path stays within normal market behavior."
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
              domain={[0, 1]}
              tick={{ fontSize: 11, fill: "#8a8278", fontFamily: "JetBrains Mono Variable, monospace" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
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
