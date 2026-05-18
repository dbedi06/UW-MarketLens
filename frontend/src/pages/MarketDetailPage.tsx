import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { MarketScore } from "../types";
import { getScore } from "../api";
import MarketReport from "../components/MarketReport";

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

  if (loading) return <p className="question">Analyzing market…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!data) return null;
  return <MarketReport data={data} />;
}
