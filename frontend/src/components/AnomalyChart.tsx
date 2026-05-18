// PILLAR 1 evidence — the suspicious window in context. Gradient area that
// draws in on mount; the flagged span is shaded.

import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip,
  ReferenceArea, CartesianGrid,
} from "recharts";
import { motion } from "framer-motion";
import type { AnomalyPoint } from "../types";
import { fadeUp } from "../lib/motion";

export default function AnomalyChart({ series }: { series: AnomalyPoint[] }) {
  const flagged = series.filter((p) => p.flagged);
  const hasFlag = flagged.length > 0;
  const flagStart = hasFlag ? flagged[0].window_index : 0;
  const flagEnd = hasFlag ? flagged[flagged.length - 1].window_index : 0;

  return (
    <motion.div variants={fadeUp} className="card p-6">
      <h2 className="text-xl font-semibold">Trade-window price path</h2>
      <p className="mt-1 text-sm text-slate-500">
        {hasFlag
          ? "The shaded span is the window the anomaly model flagged — an unusual price move on thin volume."
          : "No window was flagged: the price path stays within normal market behavior."}
      </p>
      <div className="mt-4 h-64 w-full">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={256}>
          <AreaChart data={series} margin={{ top: 8, right: 12, bottom: 4, left: -10 }}>
            <defs>
              <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4B2E83" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#4B2E83" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" vertical={false} />
            <XAxis
              dataKey="window_index"
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={{ stroke: "#e2e8f0" }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
            />
            <Tooltip
              formatter={(v) => [`${Math.round(Number(v) * 100)}%`, "Implied prob."]}
              labelFormatter={(l) => `Window ${l}`}
              contentStyle={{
                borderRadius: 12,
                border: "1px solid #e2e8f0",
                fontSize: 12,
                boxShadow: "0 8px 30px rgba(75,46,131,.12)",
              }}
            />
            {hasFlag && (
              <ReferenceArea
                x1={flagStart}
                x2={flagEnd}
                fill="#dc2626"
                fillOpacity={0.1}
                label={{ value: "flagged", fontSize: 10, fill: "#dc2626" }}
              />
            )}
            <Area
              type="monotone"
              dataKey="price"
              stroke="#4B2E83"
              strokeWidth={2.5}
              fill="url(#priceFill)"
              animationDuration={1100}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
