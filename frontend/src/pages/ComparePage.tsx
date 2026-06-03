import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { MarketScore } from "../types";
import { ApiError, scoreInMode } from "../api";
import { useScoringMode } from "../lib/scoringMode";
import { metrics, leader } from "../lib/compare";
import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";
import Skeleton from "../ui/Skeleton";
import CompareColumn from "../components/CompareColumn";

// Default URLs the compare page prefills. Both must be verified-real
// Polymarket event slugs so reviewers see a real comparison instead
// of two 404s. Refresh in lockstep with `backend/app/mock.py:_SAMPLE_URLS`.
const SAMPLE_A = "https://polymarket.com/event/fed-decision-in-june-825";
const SAMPLE_B = "https://polymarket.com/event/world-cup-winner";

export default function ComparePage() {
  const [params, setParams] = useSearchParams();
  const { mode, setMode } = useScoringMode();
  const [a, setA] = useState(params.get("a") || SAMPLE_A);
  const [b, setB] = useState(params.get("b") || SAMPLE_B);
  const [ra, setRa] = useState<MarketScore | null>(null);
  const [rb, setRb] = useState<MarketScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<ApiError | Error | null>(null);

  const qa = params.get("a");
  const qb = params.get("b");

  useEffect(() => {
    if (!qa || !qb) return;
    if (!qa.includes("polymarket.com") || !qb.includes("polymarket.com")) {
      setErr(new Error("Both URLs must be polymarket.com market links."));
      return;
    }
    setLoading(true);
    setErr(null);
    Promise.all([scoreInMode(mode, qa), scoreInMode(mode, qb)])
      .then(([x, y]) => {
        setRa(x);
        setRb(y);
      })
      .catch((e) =>
        setErr(
          e instanceof ApiError || e instanceof Error
            ? e
            : new Error("Comparison failed"),
        ),
      )
      .finally(() => setLoading(false));
  }, [qa, qb, mode]);

  const apiStatus = err instanceof ApiError ? err.status : null;

  function run() {
    if (!a.includes("polymarket.com") || !b.includes("polymarket.com")) {
      setErr(new Error("Both URLs must be polymarket.com market links."));
      return;
    }
    setParams({ a: a.trim(), b: b.trim() }, { replace: true });
  }

  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="Compare"
        title="Two markets, side by side"
        sub="Useful when choosing which of two markets to cite. Deltas show how the second compares to the first."
      />

      <div className="grid gap-3 border-y border-line py-4 sm:grid-cols-2">
        <input
          value={a}
          onChange={(e) => setA(e.target.value)}
          placeholder="First market URL"
          className="field font-mono text-[13px]"
        />
        <input
          value={b}
          onChange={(e) => setB(e.target.value)}
          placeholder="Second market URL"
          className="field font-mono text-[13px]"
        />
      </div>
      <button onClick={run} className="btn-primary mt-4">
        Compare
      </button>

      {mode === "live" && (
        <div className="mt-4 rounded border border-warn/30 bg-warn/10 px-4 py-3 text-[12.5px] text-warn">
          <span className="font-bold uppercase tracking-wider">Live mode</span>
          <span className="mx-2 opacity-60">·</span>
          Scores come from real Polymarket data via the S1→S2→S3 chain; the
          detector is synthetic-trained, so treat as directional.
        </div>
      )}

      {err && (
        <div className="mt-4 text-sm text-bad">
          <p>{err.message}</p>
          {(apiStatus === 503 || apiStatus === 422) && mode === "live" && (
            <button
              onClick={() => setMode("mock")}
              className="btn-primary mt-3"
            >
              Switch to Mock mode
            </button>
          )}
        </div>
      )}

      {loading && (
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      )}

      {ra && rb && !loading && (
        <div className="mt-8">
          <div className="grid gap-6 lg:grid-cols-2">
            <CompareColumn data={ra} />
            <CompareColumn data={rb} />
          </div>

          <div className="card mt-6 p-6">
            <h3 className="font-sans text-lg font-extrabold tracking-tight text-ink">
              Difference
            </h3>
            <p className="caption mt-1">
              {leader(ra, rb) === "tie"
                ? "Both markets score equally overall."
                : `The ${
                    leader(ra, rb) === "a" ? "first" : "second"
                  } market is more reliable overall.`}
            </p>
            <ul className="mt-4 divide-y divide-line border-t border-line">
              {metrics(ra, rb).map((m) => {
                const better = m.delta > 0;
                const same = m.delta === 0;
                return (
                  <li
                    key={m.key}
                    className="flex items-center justify-between gap-4 py-3
                      text-sm"
                  >
                    <span className="text-ink/70">{m.label}</span>
                    <span className="flex items-center gap-4 font-mono
                      tabular-nums">
                      <span className="text-ink/45">{m.a}</span>
                      <span className="text-ink/30">vs</span>
                      <span className="text-ink/45">{m.b}</span>
                      <span
                        className={`w-14 text-right font-bold ${
                          same
                            ? "text-ink/30"
                            : better
                            ? "text-good"
                            : "text-bad"
                        }`}
                      >
                        {same ? "0" : `${better ? "+" : ""}${m.delta}`}
                      </span>
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </PageShell>
  );
}
