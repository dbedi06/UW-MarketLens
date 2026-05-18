import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { fadeUp, stagger } from "../lib/motion";

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
    <div>
      {/* ---- Statement masthead (full-bleed purple block) ---- */}
      <section className="block-purple">
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="show"
          className="mx-auto max-w-content px-5 sm:px-8 lg:px-14
            pt-16 pb-20 sm:pt-24 sm:pb-28"
        >
          <motion.div
            variants={fadeUp}
            className="flex items-center gap-3 font-mono text-[11px]
              font-medium uppercase tracking-[0.14em] text-gold"
          >
            <span>UW · Academic-grade</span>
            <span className="h-px w-10 bg-gold/50" />
            <span>Prediction-market reliability</span>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            className="display mt-8 max-w-[16ch] text-[clamp(2.75rem,8vw,7rem)]
              text-paper"
          >
            Is this market<br />
            <span className="text-gold">citable?</span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="mt-8 max-w-xl text-lg leading-relaxed text-paper/75"
          >
            MarketLens explains why a Polymarket market is or isn't reliable —
            in plain language — and issues a stable, dated citation you can
            defend in a paper.
          </motion.p>
        </motion.div>
      </section>

      {/* ---- Search bar on paper, thick rule ---- */}
      <section className="border-b-2 border-ink">
        <div className="mx-auto max-w-content px-5 sm:px-8 lg:px-14 py-8">
          <label className="caption">Market URL</label>
          <div className="mt-3 flex flex-col gap-3 sm:flex-row">
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
            <button onClick={() => go(url)} className="btn-primary px-8">
              Check reliability
            </button>
          </div>
          {err ? (
            <p className="mt-2 font-mono text-xs text-bad">{err}</p>
          ) : (
            <p className="mt-2 font-mono text-xs text-ink/45">
              Try the sample URL above, or paste any market link.
            </p>
          )}
        </div>
      </section>

      {/* ---- Pillars: big numbered panels ---- */}
      <section className="mx-auto grid max-w-content gap-px bg-ink/15
        md:grid-cols-2">
        {[
          {
            n: "01",
            t: "The why, not the number",
            d: "Every verdict ships with plain-language reasons and the flagged-window evidence — quote it to defend or caveat a citation.",
          },
          {
            n: "02",
            t: "A citation that stays true",
            d: "Markets move; a citation must not. Every lookup yields a dated permalink that always re-renders the identical report.",
          },
        ].map((p) => (
          <div key={p.n} className="bg-paper p-8 sm:p-12">
            <div className="numeral text-7xl text-brand-600/20">{p.n}</div>
            <h2 className="mt-4 font-display text-2xl font-extrabold
              uppercase tracking-tight text-ink">
              {p.t}
            </h2>
            <p className="mt-3 max-w-prose leading-relaxed text-ink/65">
              {p.d}
            </p>
          </div>
        ))}
      </section>

      {/* ---- Recent ---- */}
      {recent.length > 0 && (
        <section className="mx-auto max-w-content px-5 sm:px-8 lg:px-14 py-12">
          <div className="caption">Recent lookups</div>
          <ul className="mt-3 divide-y divide-line border-y-2 border-ink">
            {recent.map((r) => (
              <li key={r}>
                <button
                  onClick={() => go(r)}
                  className="flex w-full items-center justify-between gap-4
                    py-3.5 text-left font-mono text-[13px] text-ink/70
                    transition-colors hover:text-ink"
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
