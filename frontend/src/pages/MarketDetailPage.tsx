import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { MarketScore } from "../types";
import { getScore } from "../api";
import MarketReport from "../components/MarketReport";
import PageShell from "../ui/PageShell";
import Skeleton from "../ui/Skeleton";

function LoadingState() {
  return (
    <div className="grid items-start gap-6 lg:grid-cols-[340px_1fr]">
      <div className="card flex flex-col items-center gap-4 p-6">
        <Skeleton className="h-40 w-40 rounded-full" />
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-9 w-full" />
      </div>
      <div className="space-y-6">
        <Skeleton className="h-52" />
        <Skeleton className="h-64" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}

export default function MarketDetailPage() {
  const [params] = useSearchParams();
  const url = params.get("url") ?? "";
  const [data, setData] = useState<MarketScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!url) {
      setError("No market URL provided.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    getScore(url)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Lookup failed"))
      .finally(() => setLoading(false));
  }, [url]);

  return (
    <PageShell wide>
      {loading && <LoadingState />}
      {error && !loading && (
        <div className="card p-10 text-center">
          <p className="text-lg font-semibold text-ink">Couldn't analyze that market</p>
          <p className="mt-2 text-sm text-slate-500">{error}</p>
        </div>
      )}
      {data && !loading && <MarketReport data={data} />}
    </PageShell>
  );
}
