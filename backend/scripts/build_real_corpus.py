"""Build a real-market training corpus for S3.

Fetches the top-N resolved Polymarket events via Gamma, then runs each
through `fetch_market` (Data API for trades + optional Polygon
enrichment for counterparties) and saves the resulting `RawMarket`
objects as JSON under `backend/app/anomaly/data/corpus/`. The corpus
is what `train_from_corpus.py` then trains the IsoForest on, replacing
the synthetic `clean_streams_with_network` distribution.

Usage:
    $env:MARKETLENS_POLYMARKET_LIVE = "1"
    # optional, for counterparty data
    $env:MARKETLENS_POLYGON_LIVE = "1"
    python -m scripts.build_real_corpus --n 60

Resumable: skips condition_ids already on disk. Reruns can grow the
corpus over time.

Honest caveats:
- Volume-sorted Gamma query oversamples popular markets. The detector
  learns "normal high-volume Polymarket" which may not generalize to
  obscure markets. Documented in MODEL_STATUS.md.
- Resolved markets only — open markets have no terminal state and
  the trade tape is still evolving. Resolved = stable snapshot.
- Min-trades filter (default 50) skips thin markets where features
  are too noisy to inform training.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ingestion import IngestionUnavailable, fetch_market  # noqa: E402
from app.ingestion.polymarket import GAMMA_BASE  # noqa: E402

CORPUS_DIR = ROOT / "app" / "anomaly" / "data" / "corpus"


def _dt(o):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"not JSON-serializable: {type(o).__name__}")


def _list_top_resolved_events(limit: int) -> list[dict]:
    """Pull the top-N highest-volume resolved events from Gamma.
    Returns the raw event dicts so we can extract slugs."""
    with httpx.Client(
        headers={"User-Agent": "UW-MarketLens/0.1 (corpus build)"},
        follow_redirects=True,
    ) as client:
        r = client.get(
            f"{GAMMA_BASE}/events",
            params={
                "closed":    "true",        # resolved
                "active":    "false",       # not currently trading
                "order":     "volume",
                "ascending": "false",
                "limit":     limit,
            },
            timeout=30.0,
        )
        r.raise_for_status()
        data = r.json()
    return data if isinstance(data, list) else data.get("data", [])


def _save(market, path: Path) -> None:
    """Pickle-safe JSON dump of a RawMarket dataclass."""
    payload = asdict(market)
    path.write_text(
        json.dumps(payload, indent=2, default=_dt),
        encoding="utf-8",
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=60,
                   help="Number of events to attempt fetching (default 60)")
    p.add_argument("--min-trades", type=int, default=50,
                   help="Skip markets with fewer trades than this "
                        "(default 50; thinner markets have no signal)")
    p.add_argument("--corpus-dir", type=Path, default=CORPUS_DIR,
                   help="Output directory (default %(default)s)")
    p.add_argument("--force", action="store_true",
                   help="Re-fetch markets already on disk (default: skip)")
    args = p.parse_args()

    args.corpus_dir.mkdir(parents=True, exist_ok=True)
    live = os.environ.get("MARKETLENS_POLYMARKET_LIVE") == "1"
    if not live:
        print("[warn] MARKETLENS_POLYMARKET_LIVE not set; only "
              "already-cached markets will succeed.", file=sys.stderr)

    print(f"[fetch] requesting top {args.n} resolved events from Gamma...")
    try:
        events = _list_top_resolved_events(args.n)
    except Exception as exc:
        print(f"[error] Gamma /events query failed: {exc}",
              file=sys.stderr)
        return 2
    print(f"[fetch] got {len(events)} events")

    n_ok = 0
    n_skip_disk = 0
    n_skip_thin = 0
    n_err = 0
    seen_condition_ids: set[str] = set()

    for i, event in enumerate(events):
        slug = event.get("slug") or ""
        title = event.get("title") or "<no title>"
        # Each event has 1+ markets (binary outcomes). Pick the first.
        markets = event.get("markets") or []
        if not markets:
            print(f"[skip] {i:2d}: {title[:60]!r} - no markets in event")
            continue
        primary = markets[0]
        condition_id = primary.get("conditionId", "")
        if not condition_id or condition_id in seen_condition_ids:
            continue
        seen_condition_ids.add(condition_id)

        out_path = args.corpus_dir / f"{condition_id}.json"
        if out_path.exists() and not args.force:
            n_skip_disk += 1
            continue

        url = f"https://polymarket.com/event/{slug}"
        try:
            market = fetch_market(url, trade_limit=500)
        except IngestionUnavailable as exc:
            print(f"[skip] {i:2d}: {title[:60]!r} - cache miss + no LIVE")
            continue
        except Exception as exc:
            print(f"[err]  {i:2d}: {title[:60]!r} - {type(exc).__name__}: {exc}")
            n_err += 1
            continue

        if len(market.trades) < args.min_trades:
            print(f"[thin] {i:2d}: {title[:60]!r} - only "
                  f"{len(market.trades)} trades (< {args.min_trades})")
            n_skip_thin += 1
            continue

        _save(market, out_path)
        n_ok += 1
        with_taker = sum(1 for t in market.trades if t.taker_address)
        print(f"[ok]   {i:2d}: {title[:60]!r} - "
              f"{len(market.trades)} trades, "
              f"{market.unique_traders} traders, "
              f"{with_taker} on-chain takers")

    print()
    print(f"[summary] saved={n_ok}  already-on-disk={n_skip_disk}  "
          f"thin={n_skip_thin}  errors={n_err}")
    print(f"[corpus]  {args.corpus_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
