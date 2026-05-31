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

- **`clob_trades_fed_rates.json`** — list of 10 trade records in the
  **Data API** response shape (`https://data-api.polymarket.com/trades`).
  Despite the historical filename, the content matches what
  `_fetch_market_trades` actually consumes today. Mix of:
  - Unix-int `timestamp` field (Data API's native shape)
  - `proxyWallet` per trade (initiator only — Data API does not expose
    the counterparty; our parser maps to `maker_address` and leaves
    `taker_address` empty)
  - `asset` field identifying the YES vs NO token; one record uses the
    NO token (`no-token-0xbeef`) to verify our client-side YES filter
  - one intentionally malformed record (missing timestamp) the parser
    should skip silently
  - two trades sharing a proxyWallet (proves `_derive_unique_traders`
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
