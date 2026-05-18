// Sticky translucent nav with a shared-layout active pill.

import { useState } from "react";
import { NavLink, Link } from "react-router-dom";
import { motion } from "framer-motion";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/library", label: "Library" },
  { to: "/admin", label: "Admin" },
  { to: "/about", label: "About" },
];

export default function NavBar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70
      bg-white/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-content items-center justify-between
        px-5 sm:px-8 py-3.5">
        <Link to="/" className="group flex items-center gap-2.5">
          <span className="relative grid h-8 w-8 place-items-center
            rounded-xl bg-gradient-to-br from-brand-600 to-brand-800
            font-display text-sm font-bold text-white shadow-lift
            ring-1 ring-white/10 transition group-hover:scale-105">
            M
            <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2
              rounded-full bg-gold ring-2 ring-white" />
          </span>
          <span className="font-display text-[15px] font-bold tracking-tight
            text-ink">
            UW <span className="text-brand-600">MarketLens</span>
          </span>
        </Link>

        <nav className="hidden sm:flex items-center gap-1">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}>
              {({ isActive }) => (
                <span className="relative px-3.5 py-2 text-sm font-medium">
                  {isActive && (
                    <motion.span
                      layoutId="nav-pill"
                      className="absolute inset-0 rounded-lg bg-brand-600/10"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                  <span
                    className={`relative ${
                      isActive ? "text-brand-700" : "text-slate-500 hover:text-ink"
                    }`}
                  >
                    {l.label}
                  </span>
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <button
          className="sm:hidden rounded-lg p-2 text-slate-600 hover:bg-slate-100"
          onClick={() => setOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {open ? <path d="M6 6l12 12M6 18L18 6" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
      </div>

      {open && (
        <motion.nav
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="sm:hidden border-t border-slate-200/70 px-5 py-2"
        >
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2.5 text-sm font-medium ${
                  isActive ? "bg-brand-600/10 text-brand-700" : "text-slate-600"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </motion.nav>
      )}
    </header>
  );
}
