import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-slate-200/70 bg-white">
      <div className="mx-auto flex max-w-content flex-col gap-4 px-5 sm:px-8
        py-10 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="grid h-7 w-7 place-items-center rounded-lg
              bg-brand-600 font-display text-xs font-bold text-white">
              M
            </span>
            <span className="font-display text-sm font-bold text-ink">
              UW MarketLens
            </span>
          </div>
          <p className="mt-2 max-w-md text-xs leading-relaxed text-slate-400">
            Academic-grade reliability scoring for Polymarket markets.
            Placeholder build — scores are deterministic mock data pending the
            real S1–S7 pipeline.
          </p>
        </div>
        <nav className="flex gap-6 text-sm text-slate-500">
          <Link to="/library" className="hover:text-brand-600">Library</Link>
          <Link to="/about" className="hover:text-brand-600">About</Link>
          <Link to="/admin" className="hover:text-brand-600">Admin</Link>
        </nav>
      </div>
    </footer>
  );
}
