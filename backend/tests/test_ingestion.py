"""Tests for S1 — Polymarket ingestion (B1-B5 from the plan).

Fully offline:
  * `MARKETLENS_POLYMARKET_LIVE` is never set in the suite.
  * HTTP is exercised via `httpx.MockTransport`, never live.
  * Gamma + CLOB responses come from committed JSON fixtures under
    `tests/fixtures/polymarket/`.

Net effect: ingestion is reproducible, CI-safe, and the cache module's
miss-without-live behavior is verified explicitly.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from app.ingestion import (
    IngestionUnavailable,
    RawMarket,
    RawTrade,
    fetch_market,
)
from app.ingestion.cache import (
    LIVE_ENV_FLAG,
    cache_key,
    cached_get,
    read,
    write,
)
from app.ingestion.polymarket import (
    _derive_unique_traders,
    _fetch_market_trades,
    _parse_gamma_market,
    _slug_from_url,
)


FIX = Path(__file__).parent / "fixtures" / "polymarket"
GAMMA_FIXTURE = json.loads((FIX / "gamma_event_fed_rates.json").read_text())
CLOB_FIXTURE = json.loads((FIX / "clob_trades_fed_rates.json").read_text())


# --------------------------------------------------------------------------
# Slug parsing
# --------------------------------------------------------------------------

def test_slug_parses_basic_url():
    url = "https://polymarket.com/event/will-the-fed-cut-rates-in-2025"
    assert _slug_from_url(url) == "will-the-fed-cut-rates-in-2025"


def test_slug_parses_url_with_query_string():
    url = "https://polymarket.com/event/some-market?tid=abc123"
    assert _slug_from_url(url) == "some-market"


def test_slug_parses_url_with_trailing_slash():
    url = "https://polymarket.com/event/foo/"
    assert _slug_from_url(url) == "foo"


def test_slug_rejects_non_event_url():
    with pytest.raises(ValueError, match="event"):
        _slug_from_url("https://polymarket.com/markets/foo")


def test_slug_rejects_bare_domain():
    with pytest.raises(ValueError):
        _slug_from_url("https://polymarket.com/")


# --------------------------------------------------------------------------
# Gamma parse
# --------------------------------------------------------------------------

def test_gamma_parse_extracts_canonical_fields():
    event = GAMMA_FIXTURE[0]
    parsed = _parse_gamma_market(event, "https://polymarket.com/event/x")
    assert parsed["condition_id"] == "0xabc123def456"
    assert parsed["question_id"] == "qid-fed-rates-2025"
    assert parsed["question"] == "Will the Fed cut rates in 2025?"
    assert parsed["token_ids"] == ["yes-token-0xdead", "no-token-0xbeef"]
    assert parsed["yes_price"] == pytest.approx(0.62)
    assert parsed["volume_usd"] == pytest.approx(154300.75)
    assert parsed["liquidity_usd"] == pytest.approx(12450.00)
    assert parsed["resolved"] is True
    assert parsed["resolution"] == "YES"


def test_gamma_parse_spread_defaults_to_zero():
    """B2 verification: the old `abs(1.0 - yes - (1.0-yes))` formula is
    gone; spread is 0.0 by default (real spread comes from CLOB
    /spread, fetched separately)."""
    parsed = _parse_gamma_market(GAMMA_FIXTURE[0],
                                 "https://polymarket.com/event/x")
    assert parsed["spread"] == 0.0


def test_gamma_parse_end_date_parsed_as_aware_datetime():
    parsed = _parse_gamma_market(GAMMA_FIXTURE[0],
                                 "https://polymarket.com/event/x")
    assert isinstance(parsed["end_date"], datetime)
    assert parsed["end_date"].tzinfo is not None


def test_gamma_parse_handles_modern_clobtokenids_json_string():
    """Regression: production 401 was caused by `clobTokenIds` arriving
    as a JSON-encoded *string*, which the old parser assigned directly to
    a list variable — so `token_ids[0]` returned the literal '['."""
    from copy import deepcopy
    event = deepcopy(GAMMA_FIXTURE[0])
    # Strip the older `tokens` array and replace with the modern shape
    event["markets"][0].pop("tokens", None)
    event["markets"][0]["clobTokenIds"] = (
        '["0xaaaaaaaaaaaaaaaa", "0xbbbbbbbbbbbbbbbb"]'
    )
    parsed = _parse_gamma_market(event, "https://polymarket.com/event/x")
    assert parsed["token_ids"] == [
        "0xaaaaaaaaaaaaaaaa", "0xbbbbbbbbbbbbbbbb",
    ]
    # Critically, the first id is NOT a single bracket character.
    assert parsed["token_ids"][0] != "["


def test_gamma_parse_handles_clobtokenids_as_list():
    """Belt-and-braces: same field but already a proper list."""
    from copy import deepcopy
    event = deepcopy(GAMMA_FIXTURE[0])
    event["markets"][0].pop("tokens", None)
    event["markets"][0]["clobTokenIds"] = [
        "0xccccccccccccccc", "0xddddddddddddddd",
    ]
    parsed = _parse_gamma_market(event, "https://polymarket.com/event/x")
    assert parsed["token_ids"] == [
        "0xccccccccccccccc", "0xddddddddddddddd",
    ]


def test_market_trades_refuse_malformed_condition_id(tmp_path, monkeypatch):
    """Defensive guard: refuse to despatch a bare bracket to the Data API."""
    monkeypatch.delenv(LIVE_ENV_FLAG, raising=False)
    monkeypatch.setattr("app.ingestion.cache.CACHE_DIR", tmp_path)
    with httpx.Client() as client:
        with pytest.raises(ValueError, match="malformed condition_id"):
            _fetch_market_trades(client, "[", "yes-token", limit=500)


# --------------------------------------------------------------------------
# Data API trade parse — verifies proxyWallet + YES-token filter + Unix ts
# --------------------------------------------------------------------------

CONDITION_ID = "0xabc123def456"
YES_TOKEN = "yes-token-0xdead"


def _seed_data_api_cache(tmp_path, monkeypatch):
    """Pre-seed the cache with the Data API trades response."""
    monkeypatch.delenv(LIVE_ENV_FLAG, raising=False)
    monkeypatch.setattr("app.ingestion.cache.CACHE_DIR", tmp_path)
    from app.ingestion.cache import cache_key as _ck, write as _w
    key = _ck(
        "GET", "https://data-api.polymarket.com/trades",
        {"market": CONDITION_ID, "limit": 500},
    )
    _w(key, {"method": "GET",
             "url": "https://data-api.polymarket.com/trades",
             "params": {"market": CONDITION_ID, "limit": 500}},
       CLOB_FIXTURE, cache_dir=tmp_path)


def test_data_api_parse_maps_proxywallet_to_maker_address(tmp_path,
                                                          monkeypatch):
    """Data API exposes only `proxyWallet` (the trade initiator). Our
    parser maps it to `maker_address` and leaves `taker_address` empty
    — documented loss of counterparty signal vs the auth-required CLOB."""
    _seed_data_api_cache(tmp_path, monkeypatch)
    with httpx.Client() as client:
        trades = _fetch_market_trades(
            client, CONDITION_ID, YES_TOKEN, limit=500,
        )
    # 10 fixture entries minus: 1 malformed (no timestamp) + 1 NO-side
    # filtered out by YES-token client filter = 8 successes
    assert len(trades) == 8
    # All trades carry the YES token id and have proxyWallet → maker_address
    for t in trades:
        assert t.token_id == YES_TOKEN
        assert t.maker_address  # non-empty proxyWallet
        assert t.taker_address == ""  # Data API doesn't expose counterparty
    # transactionHash propagates to trade_id
    assert any(t.trade_id.startswith("0xTxHash") for t in trades)


def test_data_api_filters_out_no_token_trades(tmp_path, monkeypatch):
    """The fixture includes a single NO-side trade; the YES filter must
    drop it from the returned list."""
    _seed_data_api_cache(tmp_path, monkeypatch)
    with httpx.Client() as client:
        trades = _fetch_market_trades(
            client, CONDITION_ID, YES_TOKEN, limit=500,
        )
    # The no-side proxyWallet doesn't appear in any returned trade
    assert all(t.maker_address != "no-token-trader" for t in trades)


def test_data_api_parse_unix_timestamps_become_aware(tmp_path, monkeypatch):
    """Data API returns Unix-int timestamps. Every parsed trade must
    have a tz-aware datetime."""
    _seed_data_api_cache(tmp_path, monkeypatch)
    with httpx.Client() as client:
        trades = _fetch_market_trades(
            client, CONDITION_ID, YES_TOKEN, limit=500,
        )
    assert all(t.timestamp.tzinfo is not None for t in trades)


def test_data_api_parse_skips_records_without_timestamp(tmp_path, monkeypatch):
    """The fixture includes one entry without a timestamp; parser must
    skip silently rather than crashing."""
    _seed_data_api_cache(tmp_path, monkeypatch)
    with httpx.Client() as client:
        trades = _fetch_market_trades(
            client, CONDITION_ID, YES_TOKEN, limit=500,
        )
    # The malformed record's tx hash must NOT appear
    assert all(t.trade_id != "0xTxHashNoTimestamp" for t in trades)


# --------------------------------------------------------------------------
# B3: unique_traders derivation
# --------------------------------------------------------------------------

def _trade(tid: str, maker: str = "", taker: str = "") -> RawTrade:
    return RawTrade(
        trade_id=tid, token_id="t", price=0.5, size=10.0, side="BUY",
        timestamp=datetime.now(timezone.utc),
        maker_address=maker, taker_address=taker,
    )


def test_derive_unique_traders_counts_distinct_wallets():
    trades = [
        _trade("1", "0xA", "0xB"),
        _trade("2", "0xA", "0xC"),  # A repeats
        _trade("3", "0xD", "0xB"),  # B repeats
    ]
    # Unique addresses: A, B, C, D = 4
    assert _derive_unique_traders(trades) == 4


def test_derive_unique_traders_excludes_empty_addresses():
    trades = [
        _trade("1", "0xA", ""),
        _trade("2", "", ""),
    ]
    assert _derive_unique_traders(trades) == 1


def test_derive_unique_traders_handles_self_trade():
    trades = [_trade("1", "0xA", "0xA")]
    # Same address on both sides counts once
    assert _derive_unique_traders(trades) == 1


def test_derive_unique_traders_empty_list_returns_zero():
    assert _derive_unique_traders([]) == 0


# --------------------------------------------------------------------------
# Cache module
# --------------------------------------------------------------------------

def test_cache_key_stable_across_param_order():
    a = cache_key("GET", "https://x.com/y", {"foo": 1, "bar": 2})
    b = cache_key("GET", "https://x.com/y", {"bar": 2, "foo": 1})
    assert a == b


def test_cache_key_differs_on_url_change():
    a = cache_key("GET", "https://x.com/y", {})
    b = cache_key("GET", "https://x.com/z", {})
    assert a != b


def test_cache_roundtrip(tmp_path):
    key = "abc123"
    write(key, {"method": "GET", "url": "x"}, {"hello": "world"},
          cache_dir=tmp_path)
    assert read(key, cache_dir=tmp_path) == {"hello": "world"}


def test_cache_read_missing_returns_none(tmp_path):
    assert read("nope", cache_dir=tmp_path) is None


def test_cached_get_returns_cached_without_network(tmp_path, monkeypatch):
    """Cache hit → never touches the transport."""
    monkeypatch.delenv(LIVE_ENV_FLAG, raising=False)
    key = cache_key("GET", "https://x.com/foo", None)
    write(key, {}, {"cached": True}, cache_dir=tmp_path)

    def boom(req):
        raise AssertionError("network should not be called on cache hit")
    client = httpx.Client(transport=httpx.MockTransport(boom))
    out = cached_get(client, "https://x.com/foo", cache_dir=tmp_path)
    assert out == {"cached": True}


def test_cached_get_miss_without_live_flag_raises(tmp_path, monkeypatch):
    monkeypatch.delenv(LIVE_ENV_FLAG, raising=False)
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={})))
    with pytest.raises(IngestionUnavailable, match=LIVE_ENV_FLAG):
        cached_get(client, "https://x.com/foo", cache_dir=tmp_path)


def test_cached_get_miss_with_live_flag_fetches_and_writes(tmp_path,
                                                          monkeypatch):
    monkeypatch.setenv(LIVE_ENV_FLAG, "1")
    payload = {"fresh": True}
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json=payload)))
    out = cached_get(client, "https://x.com/foo", cache_dir=tmp_path)
    assert out == payload
    # The follow-up call must come from the cache, not the network.
    client2 = httpx.Client(transport=httpx.MockTransport(
        lambda r: (_ for _ in ()).throw(AssertionError("should be cached"))))
    assert cached_get(client2, "https://x.com/foo",
                      cache_dir=tmp_path) == payload


# --------------------------------------------------------------------------
# End-to-end fetch_market against fixtures
# --------------------------------------------------------------------------

def test_fetch_market_e2e_offline(tmp_path, monkeypatch):
    """Seed both Gamma and CLOB caches → fetch_market should produce a
    RawMarket with B1 addresses populated and B3 unique_traders derived
    from real addresses (not 0)."""
    monkeypatch.delenv(LIVE_ENV_FLAG, raising=False)
    monkeypatch.setattr("app.ingestion.cache.CACHE_DIR", tmp_path)

    from app.ingestion.cache import cache_key as _ck, write as _w
    url = "https://polymarket.com/event/will-the-fed-cut-rates-in-2025"
    slug = "will-the-fed-cut-rates-in-2025"

    # Gamma /events?slug=
    _w(_ck("GET", "https://gamma-api.polymarket.com/events", {"slug": slug}),
       {}, GAMMA_FIXTURE, cache_dir=tmp_path)
    # Data API /trades?market=<conditionId>&limit=500
    _w(_ck("GET", "https://data-api.polymarket.com/trades",
           {"market": "0xabc123def456", "limit": 500}),
       {}, CLOB_FIXTURE, cache_dir=tmp_path)
    # CLOB /spread?token_id=...
    _w(_ck("GET", "https://clob.polymarket.com/spread",
           {"token_id": "yes-token-0xdead"}),
       {}, {"spread": "0.015"}, cache_dir=tmp_path)

    market = fetch_market(url)
    assert isinstance(market, RawMarket)
    assert market.condition_id == "0xabc123def456"
    assert market.question == "Will the Fed cut rates in 2025?"
    # 10 fixture entries minus: 1 malformed (no timestamp) + 1 NO-side
    # (filtered by YES-token client filter) = 8 trades.
    assert len(market.trades) == 8
    # proxyWallet → maker_address on every trade; taker_address always
    # empty (Data API doesn't expose the counterparty).
    assert all(t.maker_address for t in market.trades)
    assert all(t.taker_address == "" for t in market.trades)
    # unique_traders is derived from the wallet set, not Gamma's bogus 0.
    assert market.unique_traders > 0
    # spread came from the CLOB endpoint.
    assert market.spread == pytest.approx(0.015)


# --------------------------------------------------------------------------
# Live route smoke (uses cached fixtures; no live HTTP)
# --------------------------------------------------------------------------

def test_live_route_returns_market_score_against_cache(tmp_path, monkeypatch):
    """End-to-end: seed cache + hit POST /api/live/score through the
    FastAPI TestClient. Verifies wiring of fetch_market -> from_trades
    -> IsoForestDetector -> MarketScore."""
    from fastapi.testclient import TestClient

    monkeypatch.delenv(LIVE_ENV_FLAG, raising=False)
    monkeypatch.setattr("app.ingestion.cache.CACHE_DIR", tmp_path)

    from app.ingestion.cache import cache_key as _ck, write as _w
    url = "https://polymarket.com/event/will-the-fed-cut-rates-in-2025"
    slug = "will-the-fed-cut-rates-in-2025"
    _w(_ck("GET", "https://gamma-api.polymarket.com/events", {"slug": slug}),
       {}, GAMMA_FIXTURE, cache_dir=tmp_path)
    _w(_ck("GET", "https://data-api.polymarket.com/trades",
           {"market": "0xabc123def456", "limit": 500}),
       {}, CLOB_FIXTURE, cache_dir=tmp_path)
    _w(_ck("GET", "https://clob.polymarket.com/spread",
           {"token_id": "yes-token-0xdead"}),
       {}, {"spread": "0.015"}, cache_dir=tmp_path)

    from app.main import app
    with TestClient(app) as client:
        r = client.post("/api/live/score", json={"url": url})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["market_url"] == url
    assert body["band"] in {"HIGH", "MEDIUM", "LOW"}
    assert 0 <= body["reliability_score"] <= 100
    # B9: >=4 windows required for relative-feature baseline
    assert len(body["anomaly_series"]) >= 4
    # B8: source field reports the live path
    assert body["source"] == "live"


def test_live_route_503_on_cache_miss_without_live_flag(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.delenv(LIVE_ENV_FLAG, raising=False)
    monkeypatch.setattr("app.ingestion.cache.CACHE_DIR", tmp_path)

    from app.main import app
    with TestClient(app) as client:
        r = client.post("/api/live/score",
                        json={"url": "https://polymarket.com/event/nope"})
    assert r.status_code == 503
    assert "MARKETLENS_POLYMARKET_LIVE" in r.text

