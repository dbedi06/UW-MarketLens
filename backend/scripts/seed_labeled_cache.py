"""Warm the Polymarket ingestion cache for the labeled-eval set.

For each URL in `app/anomaly/data/labeled_cases.yaml`, call
`fetch_market(url)`. With `MARKETLENS_POLYMARKET_LIVE=1` set, that
triggers a live fetch and writes the on-disk cache; without the flag
it just verifies which URLs are already cached.

Once the cache is warm, `python -m scripts.eval_on_labeled --scorer
app.anomaly.scoring:score_market_url` can run fully offline.

Usage:
    $env:MARKETLENS_POLYMARKET_LIVE = "1"      # PowerShell
    python -m scripts.seed_labeled_cache
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.anomaly.labeled import DEFAULT_CASES_PATH, load_cases  # noqa: E402
from app.ingestion import IngestionUnavailable, fetch_market  # noqa: E402


def main() -> int:
    live = os.environ.get("MARKETLENS_POLYMARKET_LIVE") == "1"
    cases = load_cases(DEFAULT_CASES_PATH)
    print(f"UW MarketLens -- labeled-cases cache warmer")
    print("=" * 64)
    print(f"  cases file       : {DEFAULT_CASES_PATH}")
    print(f"  total URLs       : {len(cases)}")
    print(f"  live fetch       : {'ENABLED' if live else 'DISABLED (cache check only)'}")
    if not live:
        print("    -- set MARKETLENS_POLYMARKET_LIVE=1 to enable live fetches\n")

    n_ok = 0
    n_missing = 0
    n_err = 0
    seen: set[str] = set()
    for c in cases:
        if c.market_url in seen:
            continue  # dedupe: multiple labelers can hit the same URL
        seen.add(c.market_url)
        try:
            m = fetch_market(c.market_url)
            n_ok += 1
            print(f"  [ok]   {c.market_url}")
            print(f"           {len(m.trades)} trades, "
                  f"unique_traders={m.unique_traders}, "
                  f"resolved={m.resolved}")
        except IngestionUnavailable as exc:
            n_missing += 1
            print(f"  [miss] {c.market_url}")
            if live:
                # cached_get only raises IngestionUnavailable on miss-no-live,
                # so this branch shouldn't fire under live mode.
                print(f"           unexpected miss under live mode: {exc}")
        except Exception as exc:
            n_err += 1
            print(f"  [err]  {c.market_url}")
            print(f"           {type(exc).__name__}: {exc}")

    print()
    print(f"  cached/ok        : {n_ok}")
    print(f"  cache miss       : {n_missing}")
    print(f"  fetch errors     : {n_err}")
    if not live and n_missing:
        print(f"\n  Re-run with MARKETLENS_POLYMARKET_LIVE=1 to warm "
              f"the cache for the {n_missing} missing URL(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
