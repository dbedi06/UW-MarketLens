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
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => setRecent(loadRecent()), []);

  function go(target: string) {
    const u = target.trim();
    if (!u) return;
    if (!u.includes("polymarket.com")) {
      setErr("Enter a polymarket.com market URL.");
      return;
    }
    const next = [u, ...loadRecent().filter((x) => x !== u)].slice(0, 6);
    localStorage.setItem(LS_KEY, JSON.stringify(next));
    nav(`/market?url=${encodeURIComponent(u)}`);
  }

  return (
    <div className="mx-auto max-w-content px-5 sm:px-8 lg:px-14">
      {/* ---- Masthead ---- */}
      <header className="border-b border-line pb-12 pt-16 sm:pt-24">
        <div className="caption flex items-center gap-3">
          <span>UW · Academic-grade</span>
          <span className="h-px w-8 bg-line" />
          <span>Prediction-market reliability</span>
        </div>

        <h1 className="mt-6 max-w-[14ch] font-display text-5xl font-semibold
          leading-[1.04] tracking-[-0.01em] text-ink sm:text-7xl">
          Is this prediction market citable?
        </h1>

        <p className="mt-6 max-w-prose font-display text-lg italic
          leading-relaxed text-ink/70">
          MarketLens explains why a Polymarket market is or isn't reliable —
          in plain language — and issues a stable, dated citation you can
          defend in a paper.
        </p>

        <div className="mt-10 max-w-2xl">
          <label className="caption">Market URL</label>
          <div className="mt-2 flex flex-col gap-3 sm:flex-row">
            <input
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setErr(null);
              }}
              onKeyDown={(e) => e.key === "Enter" && go(url)}
              placeholder="https://polymarket.com/event/..."
              className="field flex-1 font-mono text-[13px]"
            />
            <button onClick={() => go(url)} className="btn-primary px-7">
              Check reliability
            </button>
          </div>
          {err ? (
            <p className="mt-2 text-sm text-bad">{err}</p>
          ) : (
            <p className="mt-2 text-sm text-ink/45">
              Try the sample URL above, or paste any market link.
            </p>
          )}
        </div>
      </header>

      {/* ---- Pillars ---- */}
      <section className="grid gap-px border-b border-line bg-line
        md:grid-cols-2">
        <article className="bg-paper p-8 sm:p-12">
          <div className="caption">Pillar 01</div>
          <h2 className="mt-3 font-display text-2xl font-semibold text-ink">
            The why, not the number
          </h2>
          <p className="mt-3 max-w-prose leading-relaxed text-ink/70">
            Every verdict ships with plain-language reasons and the
            flagged-window evidence — quote it to defend or caveat a citation.
          </p>
          <ul className="mt-6 divide-y divide-line border-y border-line">
            {[
              ["Healthy liquidity", "good"],
              ["Suspicious trading window", "bad"],
              ["Resolution partially corroborated", "warn"],
            ].map(([label, sev]) => (
              <li
                key={label}
                className="flex items-center gap-3 py-2.5 text-sm text-ink/80"
              >
                <span
                  className={`font-mono text-xs ${
                    sev === "good"
                      ? "text-good"
                      : sev === "warn"
                      ? "text-warn"
                      : "text-bad"
                  }`}
                >
                  {sev === "good" ? "[ok]" : sev === "warn" ? "[?]" : "[x]"}
                </span>
                {label}
              </li>
            ))}
          </ul>
        </article>

        <article className="bg-paper p-8 sm:p-12">
          <div className="caption">Pillar 02</div>
          <h2 className="mt-3 font-display text-2xl font-semibold text-ink">
            A citation that stays true
          </h2>
          <p className="mt-3 max-w-prose leading-relaxed text-ink/70">
            Markets move; a citation must not. Every lookup yields a dated
            permalink that always re-renders the identical report.
          </p>
          <pre className="mt-6 overflow-x-auto border border-line bg-ink/[0.03]
            p-4 font-mono text-xs leading-relaxed text-ink/80">
{`Polymarket. (n.d.). … [Prediction market].
UW MarketLens reliability snapshot 2026-05-18.
/snapshot/0476950e8428`}
          </pre>
          <p className="mt-3 text-xs text-ink/45">
            Reopen the link next quarter — byte-identical.
          </p>
        </article>
      </section>

      {/* ---- Recent ---- */}
      {recent.length > 0 && (
        <section className="py-12">
          <div className="caption">Recent lookups</div>
          <ul className="mt-3 divide-y divide-line border-y border-line">
            {recent.map((r) => (
              <li key={r}>
                <button
                  onClick={() => go(r)}
                  className="flex w-full items-center justify-between gap-4
                    py-3 text-left font-mono text-[13px] text-ink/70
                    hover:text-ink"
                >
                  <span className="truncate">
                    {r.replace("https://polymarket.com/event/", "")}
                  </span>
                  <span className="caption shrink-0">open</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
