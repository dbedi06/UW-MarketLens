# `app.ingestion` — S1 Polymarket adapter

Pulls real market metadata + trade history from Polymarket's public APIs
(no auth required) and emits the `RawMarket` dataclass that S2 feature
engineering, S3 anomaly scoring, and the live API route consume.

## Public surface

```python
from app.ingestion import fetch_market, fetch_library_markets, RawMarket, RawTrade
from app.ingestion import IngestionUnavailable
```

- `fetch_market(url) -> RawMarket` — one market by polymarket.com URL
- `fetch_library_markets(limit) -> list[RawMarket]` — top-N most-active
- `RawMarket` / `RawTrade` — output dataclasses (see
  [polymarket.py](polymarket.py) for field-by-field docstrings)
- `IngestionUnavailable` — raised when a request would need a live call
  but the env flag is unset

## Cache + live-call gate

All HTTP goes through `app.ingestion.cache.cached_get`, which behaves
identically to the Polygon cache in `app/anomaly/network`:

| State                                                        | Behavior                                  |
| ------------------------------------------------------------ | ----------------------------------------- |
| Cache hit                                                    | Return cached JSON, no network            |
| Cache miss **and** `MARKETLENS_POLYMARKET_LIVE=1` is set     | Live fetch, write cache, return           |
| Cache miss **and** `MARKETLENS_POLYMARKET_LIVE` is not set   | Raise `IngestionUnavailable` (no fab)     |

Cached responses live in [cache/](cache/) (SHA-256 keyed by method, URL,
sorted params). The directory is gitkept; entries are not. Tests
monkeypatch `cache.CACHE_DIR` to a `tmp_path` so they never read or
write the real cache.

## Seeding the cache (CLI)

```powershell
$env:MARKETLENS_POLYMARKET_LIVE = "1"
python -m scripts.fetch_market --url https://polymarket.com/event/<slug>
python -m scripts.fetch_market --library 25
python -m scripts.fetch_market --url <...> --save-fixture   # also copy into tests/fixtures/polymarket/
```

The script prints the parsed `RawMarket` and the cache path. Without
the env flag, only URLs already in the cache will succeed.

## Three-host architecture

Polymarket splits its public surface across three hosts. Our adapter
talks to each for a different concern:

| Host | What we fetch | Auth |
|------|---------------|------|
| `gamma-api.polymarket.com` | Market metadata, `clobTokenIds`, `volumeNum`, `endDate`, `closed`, `winner` | Public |
| `data-api.polymarket.com`  | Trade history (`?market=<conditionId>`) | **Public, no auth** |
| `clob.polymarket.com`      | Point-in-time `/spread` snapshot | Public (best-effort) |

**Do not switch trade history back to `clob.polymarket.com/trades`.**
That endpoint requires Level 2 (EIP-712-signed) authentication per
Polymarket's `llms.txt` docs index and the official `py-clob-client`
SDK (which calls `assert_level_2_auth()` before any /trades request).
Production was returning 401 on every real market for two weeks
because of this. The fix is to use the Data API.

## API quirks (known, documented)

- **Data API doesn't expose the trade counterparty.** Each trade record
  carries only `proxyWallet` (the initiator). We map this to
  `maker_address` and leave `taker_address` empty. Our trader-graph
  features therefore see only one side of each edge — documented loss
  of signal vs the (unavailable) authenticated CLOB endpoint.
- **Filter client-side by `asset == yes_token_id`** to keep only YES-side
  trades. The Data API returns both YES and NO outcome trades for the
  market by default.
- **Trade timestamps** are Unix-int seconds on the Data API. The parser
  falls back to ISO 8601 parsing for robustness.
- **`uniqueTraderCount`** on Gamma market objects is unreliable
  (often 0). The parser overrides it with `_derive_unique_traders`
  which counts distinct wallets across all fetched trades.
- **`clobTokenIds`** comes back as a JSON-encoded *string* on modern
  Gamma responses (e.g., `'["0x...", "0x..."]'`). `_extract_token_ids`
  parses the string before subscripting — naively reading the first
  character (an open bracket) and sending it to CLOB was the original
  production 401 trigger before this fix.
- **`spread`** is fetched separately from CLOB `/spread`; the Gamma
  response does not include it. If CLOB tightens auth on /spread
  too, the call fails silently and `RawMarket.spread` stays at 0.0
  — feature engineering tolerates this.

If Polymarket renames a field we depend on, the offline tests will
still pass (they use committed fixtures) but the manual live smoke
(`python -m scripts.fetch_market --url ...`) will fail loudly. That
script is intended as the canary.

## Honest caveats

- `RawMarket.unique_traders` counts only wallets that *executed* trades.
  Participants with unfilled orders are not visible from `/trades`.
- `RawMarket.spread` is a single point-in-time snapshot, not a history.
- We only fetch the YES token's trade tape. Markets with multi-outcome
  structures beyond binary YES/NO need a separate adapter.

## How this wires into the rest of the backend

```
RawMarket  ──>  app.anomaly.features.from_trades(...)  ──>  (X_base, mid, widx)
                                                            │
                                                            ▼
                              app.anomaly.features.feature_matrix_streams(...)
                                                            │
                                                            ▼
                                      app.anomaly.model.IsoForestDetector.score(...)
                                                            │
                                                            ▼
                                   POST /api/live/score  →  MarketScore (existing schema)
```

The mock `POST /api/score` route is unchanged. The live route is
additive (`POST /api/live/score`) so the frontend keeps working during
the transition.
