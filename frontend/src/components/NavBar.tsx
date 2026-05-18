// Editorial masthead nav: solid paper, a single bottom hairline, serif
// wordmark, active item marked by an underline rule (no glass/pill/glow).

import { useState } from "react";
import { NavLink, Link } from "react-router-dom";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/library", label: "Library" },
  { to: "/admin", label: "Admin" },
  { to: "/about", label: "About" },
];

export default function NavBar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b-2 border-ink bg-paper">
      <div className="mx-auto flex max-w-content items-center justify-between
        px-5 sm:px-8 lg:px-14 py-3.5">
        <Link to="/" className="flex items-baseline gap-2.5">
          <span className="font-sans text-lg font-extrabold tracking-tight text-ink">
            UW MarketLens
          </span>
          <span className="caption hidden sm:inline">reliability</span>
        </Link>

        <nav className="hidden sm:flex items-center gap-7">
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
          className="sm:hidden -mr-2 p-2 text-ink/70"
          onClick={() => setOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {open ? <path d="M6 6l12 12M6 18L18 6" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
      </div>

      {open && (
        <nav className="sm:hidden border-t border-line px-5 py-1">
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
        </nav>
      )}
    </header>
  );
}
