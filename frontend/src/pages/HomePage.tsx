import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { fadeUp, stagger, reveal } from "../lib/motion";
import { toast } from "../ui/Toast";
import Card from "../ui/Card";
import SectionHeading from "../ui/SectionHeading";

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
    if (!u.includes("polymarket.com")) {
      toast("Enter a polymarket.com market URL");
      return;
    }
    const next = [u, ...loadRecent().filter((x) => x !== u)].slice(0, 6);
    localStorage.setItem(LS_KEY, JSON.stringify(next));
    nav(`/market?url=${encodeURIComponent(u)}`);
  }

  return (
    <div className="overflow-clip">
      {/* ---- Hero ---- */}
      <section className="relative">
        <div className="absolute inset-0 -z-10 bg-gradient-to-b
          from-brand-900 via-brand-800 to-brand-700" />
        <div className="absolute inset-0 -z-10 opacity-[0.18]
          [background-image:radial-gradient(circle_at_20%_20%,#fff_0,transparent_40%),radial-gradient(circle_at_80%_0,#B7A57A_0,transparent_45%)]" />
        <div className="absolute inset-0 -z-10
          [background-image:linear-gradient(rgba(255,255,255,.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.04)_1px,transparent_1px)]
          [background-size:44px_44px]" />

        <motion.div
          variants={stagger}
          initial="hidden"
          animate="show"
          className="mx-auto max-w-content px-5 sm:px-8 pt-20 pb-24 sm:pt-28 sm:pb-32"
        >
          <motion.div variants={fadeUp}>
            <span className="inline-flex items-center gap-2 rounded-full
              border border-white/20 bg-white/10 px-3 py-1 text-xs
              font-semibold text-white/80 backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-gold" />
              For the UW community · academic-grade
            </span>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            className="mt-6 max-w-3xl font-display text-4xl sm:text-6xl
              font-extrabold leading-[1.05] text-white"
          >
            Is this prediction market
            <span className="bg-gradient-to-r from-gold-soft to-gold
              bg-clip-text text-transparent"> actually citable?</span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="mt-5 max-w-xl text-lg leading-relaxed text-white/70"
          >
            MarketLens explains <em>why</em> a Polymarket market is or isn't
            reliable — in plain language — and gives you a stable, dated
            citation you can defend in a paper.
          </motion.p>

          <motion.div variants={fadeUp} className="mt-9 max-w-xl">
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && go(url)}
                placeholder="https://polymarket.com/event/..."
                className="field flex-1 border-0 bg-white/95 text-ink
                  placeholder:text-slate-400 focus:ring-gold/50"
              />
              <motion.button
                whileTap={{ scale: 0.97 }}
                onClick={() => go(url)}
                className="btn rounded-xl bg-gold px-6 py-3 font-semibold
                  text-brand-900 hover:brightness-105 shadow-lift"
              >
                Check reliability →
              </motion.button>
            </div>
            <p className="mt-3 text-sm text-white/50">
              Try the sample URL above, or paste any market link.
            </p>
          </motion.div>
        </motion.div>

        <svg
          className="block w-full text-slate-50"
          viewBox="0 0 1440 80"
          preserveAspectRatio="none"
          style={{ height: 56 }}
        >
          <path fill="currentColor" d="M0 80h1440V0c-240 53-560 70-720 70S240 53 0 0z" />
        </svg>
      </section>

      {/* ---- Pillars ---- */}
      <section className="mx-auto max-w-content px-5 sm:px-8 py-16">
        <motion.div {...reveal}>
          <SectionHeading
            eyebrow="What makes it trustworthy"
            title="Two things most market screeners skip"
            sub="A number you can't explain is a number you can't cite."
          />
        </motion.div>

        <motion.div
          variants={stagger}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
          className="grid gap-5 md:grid-cols-2"
        >
          <Card hover>
            <div className="eyebrow">Pillar 1</div>
            <h3 className="mt-2 text-lg font-semibold">The "why," not the number</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Every verdict ships with plain-language reasons and the
              flagged-window evidence — quote it to defend or caveat a citation.
            </p>
            <div className="mt-5 space-y-2">
              {[
                ["good", "Healthy liquidity"],
                ["bad", "Suspicious trading window"],
                ["warn", "Resolution partially corroborated"],
              ].map(([sev, label]) => (
                <div
                  key={label}
                  className="flex items-center gap-3 rounded-lg border
                    border-slate-200/70 bg-slate-50 px-3 py-2 text-sm"
                >
                  <span
                    className={`grid h-5 w-5 place-items-center rounded-full
                      text-[11px] font-bold text-white ${
                        sev === "good" ? "bg-good" : sev === "warn" ? "bg-warn" : "bg-bad"
                      }`}
                  >
                    {sev === "good" ? "✓" : sev === "warn" ? "!" : "✕"}
                  </span>
                  <span className="text-slate-600">{label}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card hover>
            <div className="eyebrow">Pillar 2</div>
            <h3 className="mt-2 text-lg font-semibold">A citation that stays true</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Markets move; a citation must not. Every lookup yields a dated
              permalink that always re-renders the identical report.
            </p>
            <div className="mt-5 rounded-xl bg-ink p-4 font-mono text-xs
              leading-relaxed text-slate-300">
              <span className="text-gold">Polymarket.</span> (n.d.). …{"\n"}
              UW MarketLens snapshot <span className="text-white">2026-05-18</span>
              {"\n"}
              <span className="text-brand-300">/snapshot/0476950e8428</span>
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Reopen the link next quarter — byte-identical.
            </p>
          </Card>
        </motion.div>
      </section>

      {/* ---- Recent ---- */}
      {recent.length > 0 && (
        <section className="mx-auto max-w-content px-5 sm:px-8 pb-20">
          <motion.div {...reveal}>
            <SectionHeading eyebrow="Pick up where you left off" title="Recent lookups" />
            <div className="flex flex-wrap gap-2">
              {recent.map((r) => (
                <button
                  key={r}
                  onClick={() => go(r)}
                  className="max-w-full truncate rounded-full border
                    border-slate-200 bg-white px-4 py-2 text-sm text-slate-600
                    shadow-soft transition hover:border-brand-600/40
                    hover:text-brand-700"
                >
                  {r.replace("https://polymarket.com/event/", "")}
                </button>
              ))}
            </div>
          </motion.div>
        </section>
      )}
    </div>
  );
}
