import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="mt-24 block-purple">
      <div className="mx-auto flex max-w-content flex-col gap-6 px-5 sm:px-8
        lg:px-14 py-14 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-md">
          <div className="display text-xl text-paper">UW MARKETLENS</div>
          <p className="mt-3 text-xs leading-relaxed text-paper/55">
            Academic-grade reliability scoring for Polymarket markets.
            Placeholder build — scores are deterministic mock data pending the
            real S1–S7 pipeline.
          </p>
        </div>
        <nav className="flex gap-8 font-mono text-xs uppercase tracking-wide
          text-paper/65">
          <Link to="/library" className="hover:text-gold">Library</Link>
          <Link to="/about" className="hover:text-gold">About</Link>
          <Link to="/admin" className="hover:text-gold">Admin</Link>
        </nav>
      </div>
    </footer>
  );
}
