// PILLAR 2 — opening a permalink renders the frozen report by id. Because the
// backend is deterministic in (url, as_of), this is byte-identical to the
// report the citation was generated from.

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import type { MarketScore } from "../types";
import { getSnapshot } from "../api";
import MarketReport from "../components/MarketReport";
import PageShell from "../ui/PageShell";
import Skeleton from "../ui/Skeleton";

export default function SnapshotPage() {
  const { id = "" } = useParams();
  const [data, setData] = useState<MarketScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSnapshot(id)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Snapshot not found"))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <PageShell wide>
      {loading && (
        <div className="grid items-start gap-6 lg:grid-cols-[340px_1fr]">
          <div className="card flex flex-col items-center gap-4 p-6">
            <Skeleton className="h-40 w-40 rounded-full" />
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-9 w-full" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-52" />
            <Skeleton className="h-64" />
          </div>
        </div>
      )}
      {error && !loading && (
        <div className="card p-10 text-center">
          <p className="text-lg font-semibold text-ink">Snapshot unavailable</p>
          <p className="mt-2 text-sm text-slate-500">{error}</p>
        </div>
      )}
      {data && !loading && (
        <>
          <div className="mb-4 rounded-xl bg-brand-600 px-4 py-2.5 text-sm
            font-medium text-white">
            Viewing a saved snapshot ({id}) — frozen and reproducible.
          </div>
          <MarketReport data={data} />
        </>
      )}
    </PageShell>
  );
}
