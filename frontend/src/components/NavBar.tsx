// Editorial masthead nav: solid paper, a single bottom hairline, serif
// wordmark, active item marked by an underline rule (no glass/pill/glow).

import { useState } from "react";
import { NavLink, Link } from "react-router-dom";
import { useScoringMode } from "../lib/scoringMode";

const links = [
  { to: "/", label: "Home", end: true },
  // PISAN line 14 critique: "UW connection is thin in practice."
  // Surfacing the For UW page right after Home means the framing
  // appears on every page load, not buried behind functional pages.
  { to: "/uw", label: "For UW" },
  { to: "/library", label: "Library" },
  { to: "/compare", label: "Compare" },
  { to: "/admin", label: "Admin" },
  { to: "/about", label: "About" },
];

type Theme = "light" | "dark";

function MoonIcon() {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      className="h-4 w-4"
    >
      <path d="M16.25 12.5A7.5 7.5 0 0 1 7.5 3.75 7.5 7.5 0 1 0 16.25 12.5Z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      className="h-4 w-4"
    >
      <circle cx="10" cy="10" r="3.5" />
      <path d="M10 2.5v2M10 15.5v2M2.5 10h2M15.5 10h2M4.8 4.8l1.4 1.4M13.8 13.8l1.4 1.4M4.8 15.2l1.4-1.4M13.8 6.2l1.4-1.4" />
    </svg>
  );
}

export default function NavBar({
  theme,
  toggleTheme,
}: {
  theme: Theme;
  toggleTheme: () => void;
}) {
  const [open, setOpen] = useState(false);
  const { mode, toggle } = useScoringMode();
  const isLive = mode === "live";

  return (
    <header className="sticky top-0 z-40 border-b-2 border-ink bg-paper">
      <div className="mx-auto flex max-w-content items-center justify-between px-5 py-3.5 sm:px-8 lg:px-14">
        <Link to="/" className="flex items-baseline gap-2.5">
          <span className="font-sans text-lg font-extrabold tracking-tight text-ink">
            UW MarketLens
          </span>
          <span className="caption hidden sm:inline">reliability</span>
        </Link>

        <div className="flex items-center gap-2 sm:gap-3">
          <nav
            aria-label="Primary"
            className="hidden items-center gap-7 sm:flex"
          >
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  `border-b-2 pb-0.5 text-sm transition-colors ${
                    isActive
                      ? "border-brand-600 text-ink font-medium"
                      : "border-transparent text-ink/55 hover:text-ink"
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>

          <button
            type="button"
            onClick={toggle}
            aria-label={
              isLive
                ? "Switch scoring to mock data"
                : "Switch scoring to live data"
            }
            aria-pressed={isLive}
            title={
              isLive
                ? "Live: real Polymarket data via S1→S7 (detector trained on real corpus; labeled AUC preliminary)"
                : "Mock: deterministic placeholder data"
            }
            className="hidden items-center gap-1.5 rounded-full border border-line bg-panel px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-ink/75 transition-colors hover:text-ink sm:inline-flex"
          >
            <span
              aria-hidden
              className={`h-1.5 w-1.5 rounded-full ${
                isLive ? "bg-good" : "bg-ink/30"
              }`}
            />
            {isLive ? "Live" : "Mock"}
          </button>

          <button
            type="button"
            onClick={toggleTheme}
            aria-label={
              theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
            }
            aria-pressed={theme === "dark"}
            className="inline-flex items-center justify-center gap-2 rounded-full border border-line bg-panel px-3 py-2 text-sm text-ink/75 transition-colors hover:text-ink"
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            <span className="hidden sm:inline">
              {theme === "dark" ? "Light" : "Dark"}
            </span>
          </button>

          <button
            className="-mr-2 p-2 text-ink/70 sm:hidden"
            onClick={() => setOpen((o) => !o)}
            aria-label="Toggle menu"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              {open ? (
                <path d="M6 6l12 12M6 18L18 6" />
              ) : (
                <path d="M4 7h16M4 12h16M4 17h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {open && (
        <nav
          aria-label="Mobile"
          className="border-t border-line px-5 py-1 sm:hidden"
        >
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `block border-b border-line py-3 text-sm last:border-0 ${
                  isActive ? "text-ink font-medium" : "text-ink/60"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
          <button
            type="button"
            onClick={() => {
              toggle();
              setOpen(false);
            }}
            className="flex w-full items-center justify-between py-3 text-sm text-ink/60"
          >
            <span>Scoring mode</span>
            <span className="flex items-center gap-1.5 font-bold uppercase tracking-wider">
              <span
                aria-hidden
                className={`h-1.5 w-1.5 rounded-full ${
                  isLive ? "bg-good" : "bg-ink/30"
                }`}
              />
              {isLive ? "Live" : "Mock"}
            </span>
          </button>
        </nav>
      )}
    </header>
  );
}
