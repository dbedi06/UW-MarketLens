import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const SAMPLE = "https://polymarket.com/event/will-the-fed-cut-rates-in-2025";
const LS_KEY = "ml_recent_lookups";

function loadRecent(): string[] {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export default function HomePage() {
  const nav = useNavigate();
  const [url, setUrl] = useState(SAMPLE);
  const [recent, setRecent] = useState<string[]>([]);

  useEffect(() => setRecent(loadRecent()), []);

  function go(target: string) {
    const u = target.trim();
    if (!u) return;
    const next = [u, ...loadRecent().filter((x) => x !== u)].slice(0, 6);
    localStorage.setItem(LS_KEY, JSON.stringify(next));
    nav(`/market?url=${encodeURIComponent(u)}`);
  }

  return (
    <div>
      <section className="home-hero">
        <h2>Is this prediction market citable?</h2>
        <p>
          Paste a Polymarket market URL. MarketLens explains <em>why</em> a market is
          or isn't reliable — in plain language — and gives you a stable, dated
          citation you can defend in a paper.
        </p>
        <div className="lookup">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://polymarket.com/event/..."
            onKeyDown={(e) => e.key === "Enter" && go(url)}
          />
          <button onClick={() => go(url)}>Check reliability</button>
        </div>
        <p className="hint">Try the sample URL above, or paste any polymarket.com/event/... link.</p>
      </section>

      {recent.length > 0 && (
        <div className="card">
          <h2>Recent lookups</h2>
          <ul className="recent">
            {recent.map((r) => (
              <li key={r}>
                <button className="linkish" onClick={() => go(r)}>
                  {r}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
