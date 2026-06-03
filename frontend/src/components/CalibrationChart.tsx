import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import type { CalibrationReport } from "../types";
import { getCalibrationReport } from "../api";
import SectionHeading from "../ui/SectionHeading";

function percentAxis(value: number) {
  return `${Math.round(value * 100)}%`;
}

export default function CalibrationChart() {
  const [report, setReport] = useState<CalibrationReport | null>(null);
  const [errored, setErrored] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCalibrationReport()
      .then((data) => {
        if (!cancelled) setReport(data);
      })
      .catch(() => {
        if (!cancelled) setErrored(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (errored) {
    return (
      <div className="card p-6">
        <SectionHeading
          eyebrow="Calibration"
          title="Confidence calibration report"
          sub="The backend has not produced a calibration report yet. Run the script to generate one."
        />
        <p className="mt-4 text-sm text-ink/65">
          Generate the report with{" "}
          <code className="font-mono">
            python -m scripts.calibration_report
          </code>{" "}
          and refresh.
        </p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="card p-6">
        <SectionHeading
          eyebrow="Calibration"
          title="Confidence calibration report"
          sub="Loading the latest labeled-set calibration data from the backend."
        />
        <p className="mt-4 text-sm text-ink/65">This may take a moment.</p>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <SectionHeading
        eyebrow="Calibration"
        title="Confidence vs. label agreement"
        sub="Accuracy is computed in five confidence buckets over the labeled cases. The line shows average reported confidence per bucket."
      />
      <div className="mt-6 h-80 w-full">
        <ResponsiveContainer width="100%" height="100%" minHeight={320}>
          <ComposedChart
            data={report.buckets}
            margin={{ top: 8, right: 16, bottom: 8, left: -10 }}
          >
            <CartesianGrid stroke="#E4DFD5" vertical={false} />
            <XAxis
              dataKey="bucket"
              tick={{
                fontSize: 11,
                fill: "#8a8278",
                fontFamily: "JetBrains Mono Variable, monospace",
              }}
              tickLine={false}
              axisLine={{ stroke: "#E4DFD5" }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{
                fontSize: 11,
                fill: "#8a8278",
                fontFamily: "JetBrains Mono Variable, monospace",
              }}
              tickLine={false}
              axisLine={false}
              tickFormatter={percentAxis}
            />
            <Tooltip
              formatter={(value) =>
                typeof value === "number"
                  ? `${Math.round(value * 100)}%`
                  : value
              }
              labelFormatter={(label) => `Confidence bucket ${label}`}
            />
            <Legend verticalAlign="top" height={32} />
            <Bar
              name="agreement"
              dataKey="accuracy"
              fill="#4B2E83"
              radius={[4, 4, 0, 0]}
            />
            <Line
              name="avg confidence"
              type="monotone"
              dataKey="avg_confidence"
              stroke="#F59E0B"
              strokeWidth={3}
              dot={{ r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-4 text-sm text-ink/65">
        A perfectly calibrated model would have the line and the bar heights
        match in each bucket. This is a small sanity check, not a
        high-confidence reliability diagram; the labeled set is intentionally
        tiny.
      </p>
    </div>
  );
}
