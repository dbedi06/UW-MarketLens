import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { MarketScore } from "../types";
import { ApiError, scoreInMode } from "../api";
import { useScoringMode } from "../lib/scoringMode";
import MarketReport from "../components/MarketReport";
import PageShell from "../ui/PageShell";
import Skeleton from "../ui/Skeleton";
import DateField from "../ui/DateField";

function LoadingState() {
  return (
    <div className="grid items-start gap-x-16 gap-y-10 lg:grid-cols-[380px_minmax(0,1fr)]">
      <div className="card flex flex-col items-center gap-4 p-7">
        <Skeleton className="h-40 w-40 rounded-full" />
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-9 w-full" />
      </div>
      <div className="space-y-10">
        <Skeleton className="h-52" />
        <Skeleton className="h-64" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}

function LiveDisclaimer() {
  return (
    <div className="mb-6 rounded border border-warn/30 bg-warn/10 px-4 py-3 text-[12.5px] text-warn">
      <span className="font-bold uppercase tracking-wider">Live mode</span>
      <span className="mx-2 opacity-60">·</span>
      Real Polymarket data through the S1→S2→S3 chain. The detector is
      synthetic-trained, so this score is directional, not authoritative.
      See the project's <code>MODEL_STATUS.md</code> for the honest read.
    </div>
  );
}

const TODAY = new Date().toISOString().slice(0, 10);

export default function MarketDetailPage() {
  const [params, setParams] = useSearchParams();
  const url = params.get("url") ?? "";
  const asOf = params.get("as_of") || TODAY;
  const { mode, setMode } = useScoringMode();
  const [data, setData] = useState<MarketScore | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!url) {
      setError(new Error("No market URL provided."));
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    scoreInMode(mode, url, asOf)
      .then(setData)
      .catch((e) =>
        setError(
          e instanceof ApiError || e instanceof Error
            ? e
            : new Error("Lookup failed"),
        ),
      )
      .finally(() => setLoading(false));
  }, [url, asOf, mode]);

  function setAsOf(next: string) {
    const p = new URLSearchParams(params);
    if (!next || next === TODAY) p.delete("as_of");
    else p.set("as_of", next);
    setParams(p, { replace: true });
  }

  const apiStatus = error instanceof ApiError ? error.status : null;

  return (
    <PageShell wide>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3
        border-b border-line pb-4">
        <DateField
          label="Reliability as of"
          value={asOf}
          max={TODAY}
          onChange={setAsOf}
        />
        {asOf !== TODAY && (
          <button
            onClick={() => setAsOf(TODAY)}
            className="caption hover:text-ink"
          >
            Reset to today
          </button>
        )}
      </div>

      {mode === "live" && <LiveDisclaimer />}

      {loading && <LoadingState />}
      {error && !loading && (
        <div className="card p-10 text-center">
          <p className="text-lg font-semibold text-ink">
            {apiStatus === 503
              ? "This market isn't cached yet"
              : apiStatus === 422
              ? "Not enough trade history"
              : "Couldn't analyze that market"}
          </p>
          <p className="mt-2 text-sm text-ink/55">{error.message}</p>
          {(apiStatus === 503 || apiStatus === 422) && mode === "live" && (
            <button
              onClick={() => setMode("mock")}
              className="btn-primary mt-5"
            >
              Switch to Mock mode
            </button>
          )}
        </div>
      )}
      {data && !loading && <MarketReport data={data} />}
    </PageShell>
  );
}
