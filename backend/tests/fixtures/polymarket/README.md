# Polymarket test fixtures

Hand-crafted minimal JSON files matching the shape Lewi's parser reads.
Used by `tests/test_ingestion.py` and `tests/test_from_trades.py` so the
suite runs fully offline (no live calls, no `MARKETLENS_POLYMARKET_LIVE`).

These are **not** real Polymarket responses copied from the wire. They
are intentionally minimal — each field is present so the parser exercises
the same code path, but the values are placeholders. Document any
non-obvious shape choices below.

## Files

- **`gamma_event_fed_rates.json`** — single-event response from
  `GET /events?slug=...`. Two outcome markets (YES/NO) with one token
  each so we exercise the `outcomePrices`/`tokens` path. Includes
  `winner: "Yes"` to test resolution parsing.

- **`clob_trades_fed_rates.json`** — list of 10 trades for the YES
  token. Mix of:
  - ISO-string `timestamp` and Unix-int `matchTime` (parser tolerates both)
  - both `maker_address`/`taker_address` and bare `maker`/`taker` field
    name variants
  - one intentionally malformed record (missing price) the parser
    should skip silently
  - two trades sharing a maker address (proves `_derive_unique_traders`
    deduplicates)

## Regenerating from live data

When the team wants to refresh against the real API:

```
MARKETLENS_POLYMARKET_LIVE=1 python -m scripts.fetch_market \
  --url https://polymarket.com/event/<slug> --save-fixture
```

That will hit Polymarket live, write the raw responses into
`backend/app/ingestion/cache/`, and print a path you can copy into
this directory. See `app/ingestion/README.md` for the full workflow.
