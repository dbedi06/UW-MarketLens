// PILLAR 1 evidence — shows the suspicious window in context. A shaded band
// over the flagged trades is what backs up the "anomaly" reason in plain view.

import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip,
  ReferenceArea, CartesianGrid,
} from "recharts";
import type { AnomalyPoint } from "../types";

export default function AnomalyChart({ series }: { series: AnomalyPoint[] }) {
  const flagged = series.filter((p) => p.flagged);
  const hasFlag = flagged.length > 0;
  const flagStart = hasFlag ? flagged[0].window_index : 0;
  const flagEnd = hasFlag ? flagged[flagged.length - 1].window_index : 0;

  return (
    <div className="card">
      <h2>Trade-window price path</h2>
      <p className="question">
        {hasFlag
          ? "The shaded span is the window the anomaly model flagged — an unusual price move on thin volume."
          : "No window was flagged: the price path stays within normal market behavior."}
      </p>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <LineChart data={series} margin={{ top: 8, right: 16, bottom: 4, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="window_index"
              tick={{ fontSize: 11 }}
              label={{ value: "Trade window", position: "insideBottom", offset: -2, fontSize: 11 }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
            />
            <Tooltip
              formatter={(v) => [`${Math.round(Number(v) * 100)}%`, "Implied prob."]}
              labelFormatter={(l) => `Window ${l}`}
            />
            {hasFlag && (
              <ReferenceArea
                x1={flagStart}
                x2={flagEnd}
                fill="#b91c1c"
                fillOpacity={0.12}
                label={{ value: "flagged", fontSize: 10, fill: "#b91c1c" }}
              />
            )}
            <Line
              type="monotone"
              dataKey="price"
              stroke="#2E5C8A"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
