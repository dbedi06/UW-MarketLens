import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto flex max-w-content flex-col gap-6 px-5 sm:px-8
        lg:px-14 py-12 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-md">
          <div className="font-display text-base font-semibold text-ink">
            UW MarketLens
          </div>
          <p className="mt-2 text-xs leading-relaxed text-ink/50">
            Academic-grade reliability scoring for Polymarket markets.
            Placeholder build — scores are deterministic mock data pending the
            real S1–S7 pipeline.
          </p>
        </div>
        <nav className="flex gap-8 font-mono text-xs text-ink/55">
          <Link to="/library" className="hover:text-ink">Library</Link>
          <Link to="/about" className="hover:text-ink">About</Link>
          <Link to="/admin" className="hover:text-ink">Admin</Link>
        </nav>
      </div>
    </footer>
  );
}
