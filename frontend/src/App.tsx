import { useState } from "react";
import "./theme.css";
import type { MarketScore } from "./types";
import { getScore } from "./api";
import ScoreCard from "./components/ScoreCard";
import CitationBox from "./components/CitationBox";
import Library from "./components/Library";

const SAMPLE = "https://polymarket.com/event/will-the-fed-cut-rates-in-2025";

export default function App() {
  const [url, setUrl] = useState(SAMPLE);
  const [result, setResult] = useState<MarketScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function lookup() {
    setLoading(true);
    setError(null);
    try {
      setResult(await getScore(url));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <h1>UW MarketLens</h1>
        <p>AI-Powered Prediction Market Reliability Platform — placeholder build</p>
      </header>

      <main>
        <div className="lookup">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste a Polymarket market URL"
            onKeyDown={(e) => e.key === "Enter" && lookup()}
          />
          <button onClick={lookup} disabled={loading}>
            {loading ? "Checking…" : "Check reliability"}
          </button>
        </div>
        <p className="hint">Try the sample URL or paste any polymarket.com/event/... link.</p>

        {error && <p className="error">{error}</p>}

        {result && (
          <>
            <ScoreCard data={result} />
            <CitationBox citation={result.citation} />
          </>
        )}

        <Library />

        <p className="placeholder-note">
          All scores are deterministic mock data (backend <code>app/mock.py</code>).
          Replaced by the real S1–S7 pipeline later — no frontend changes required.
        </p>
      </main>
    </div>
  );
}
