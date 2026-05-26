"""CLI: fetch a Polymarket market (or top-N library) into the on-disk
cache and pretty-print the resulting `RawMarket`.

Usage (single market, live fetch + cache):
    set MARKETLENS_POLYMARKET_LIVE=1  # PowerShell: $env:MARKETLENS_POLYMARKET_LIVE = "1"
    python -m scripts.fetch_market --url https://polymarket.com/event/<slug>

Usage (top-N library seed):
    python -m scripts.fetch_market --library 25

Notes:
  * Without MARKETLENS_POLYMARKET_LIVE=1 the script will only succeed
    for URLs that are already cached — it never fabricates data.
  * --save-fixture copies the cached JSON files into
    `backend/tests/fixtures/polymarket/` for reuse as test fixtures.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app.ingestion import (
    IngestionUnavailable, fetch_library_markets, fetch_market,
)
from app.ingestion.cache import CACHE_DIR


def _dt(o):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"not JSON-serializable: {type(o).__name__}")


def _print_market(m) -> None:
    d = asdict(m)
    # trades can be long; truncate for printing
    n_trades = len(d.get("trades", []))
    if n_trades > 5:
        d["trades"] = d["trades"][:5] + [f"... ({n_trades - 5} more)"]
    print(json.dumps(d, indent=2, default=_dt))
    print(f"\n[summary] {n_trades} trades, "
          f"unique_traders={m.unique_traders}, "
          f"volume_usd={m.volume_usd:.0f}, "
          f"spread={m.spread:.4f}, "
          f"resolved={m.resolved}")


def _copy_cache_to_fixtures(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in CACHE_DIR.glob("*.json"):
        shutil.copy2(f, dest / f.name)
        n += 1
    print(f"[fixture] copied {n} cached responses -> {dest}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", help="Single Polymarket event URL")
    g.add_argument("--library", type=int,
                   help="Pull top-N most-active markets (seeds cache)")
    p.add_argument("--save-fixture", action="store_true",
                   help="After fetching, copy cached JSON files into the "
                        "tests/fixtures/polymarket/ directory.")
    args = p.parse_args(argv)

    live = os.environ.get("MARKETLENS_POLYMARKET_LIVE") == "1"
    if not live:
        print("[warn] MARKETLENS_POLYMARKET_LIVE not set; only cached "
              "URLs will succeed.", file=sys.stderr)

    try:
        if args.url:
            market = fetch_market(args.url)
            _print_market(market)
        else:
            markets = fetch_library_markets(args.library)
            print(f"[ok] fetched {len(markets)} markets")
            for m in markets:
                print(f"  - {m.question[:80]}  (vol=${m.volume_usd:.0f})")
    except IngestionUnavailable as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    if args.save_fixture:
        dest = Path(__file__).parent.parent / "tests" / "fixtures" / "polymarket"
        _copy_cache_to_fixtures(dest)

    print(f"\n[cache] {CACHE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
