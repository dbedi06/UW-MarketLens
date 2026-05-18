// PILLAR 2 — opening a permalink renders the frozen report by id. Because the
// backend is deterministic in (url, as_of), this is byte-identical to the
// report the citation was generated from.

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import type { MarketScore } from "../types";
import { getSnapshot } from "../api";
import MarketReport from "../components/MarketReport";

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

  if (loading) return <p className="question">Loading snapshot…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <div className="snapshot-banner">
        Viewing a saved snapshot ({id}). This view is frozen and reproducible.
      </div>
      <MarketReport data={data} />
    </div>
  );
}
