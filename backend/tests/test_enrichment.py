"""Tests for app.anomaly.network.enrichment — backfill takers.

The enricher reaches into the PolygonClient cache; tests pre-seed the
cache with synthetic eth_getLogs responses keyed by request shape, so
nothing live happens.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.anomaly.network.enrichment import (
    _estimate_block_for_timestamp, enrich_with_takers,
)
from app.anomaly.network.exchange import (
    EXCHANGE_ADDRESSES, ORDER_FILLED_TOPIC,
)
from app.anomaly.network.polygon_client import (
    PolygonClient, RpcUnavailable, _cache_key,
)
from app.ingestion.polymarket import RawTrade


PROXY_WALLET = "0x" + "a" * 40
COUNTERPARTY = "0x" + "b" * 40


def _rt(tx_hash: str, ts: int = 1762020000) -> RawTrade:
    """Build a RawTrade like the Data API would."""
    return RawTrade(
        trade_id=tx_hash,
        token_id="yes-token-x",
        price=0.5, size=10.0, side="BUY",
        timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
        maker_address=PROXY_WALLET,
        taker_address="",
    )


def _build_order_filled_log(
    *, tx_hash: str, maker: str, taker: str,
) -> dict:
    """A minimal eth_getLogs entry — same shape as `_build_log` in
    the decoder tests."""
    def w(v: str | int) -> str:
        if isinstance(v, int):
            return f"{v:064x}"
        return (v[2:] if v.startswith("0x") else v).rjust(64, "0")

    data = "0x" + (
        ("11" * 32)  # orderHash
        + w(maker) + w(taker)
        + w(12345) + w(67890) + w(1000) + w(990) + w(1)
    )
    return {
        "address": EXCHANGE_ADDRESSES[0],
        "topics": [ORDER_FILLED_TOPIC],
        "data": data,
        "transactionHash": tx_hash,
    }


def _seed_cache(cache_dir: Path, *, logs: list[dict],
                latest_block: int = 100_000,
                latest_ts: int = 1762100000) -> None:
    """Pre-populate the PolygonClient cache so the enricher runs offline.
    We need three cached responses: latest block number, latest block
    timestamp, and the eth_getLogs result (twice — one per Exchange
    address)."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    # eth_blockNumber → hex string
    bn_payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber",
                  "params": []}
    bn_key = _cache_key(bn_payload)
    (cache_dir / f"{bn_key}.json").write_text(json.dumps({
        "request": bn_payload, "result": hex(latest_block),
    }))

    # eth_getBlockByNumber latest → has timestamp
    lb_payload = {"jsonrpc": "2.0", "id": 1,
                  "method": "eth_getBlockByNumber",
                  "params": ["latest", False]}
    lb_key = _cache_key(lb_payload)
    (cache_dir / f"{lb_key}.json").write_text(json.dumps({
        "request": lb_payload,
        "result": {"timestamp": hex(latest_ts)},
    }))

    # eth_getLogs — same response for both Exchange addresses
    block_pad = 1000
    # Match what the enricher computes:
    # from_block = estimate(min_ts) - pad
    # to_block   = estimate(max_ts) + pad
    # All trades share ts=1762020000 in the happy path; latest_ts=1762100000
    # delta = 80000s → 40000 blocks; from/to_block = 100000 - 40000 = 60000
    # padded: from = 59000, to = 61000
    from_block = 59000
    to_block = 61000
    for addr in EXCHANGE_ADDRESSES:
        gl_payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs",
                      "params": [{
                          "fromBlock": hex(from_block),
                          "toBlock": hex(to_block),
                          "address": addr,
                          "topics": [ORDER_FILLED_TOPIC],
                      }]}
        gl_key = _cache_key(gl_payload)
        # Only the first exchange address gets matching logs; the second
        # returns empty (NegRisk doesn't see these binary-market trades).
        result = logs if addr == EXCHANGE_ADDRESSES[0] else []
        (cache_dir / f"{gl_key}.json").write_text(json.dumps({
            "request": gl_payload, "result": result,
        }))


def test_estimate_block_for_timestamp_linear():
    # 100 seconds ago → 50 blocks ago at 2s/block
    out = _estimate_block_for_timestamp(
        target_ts=900, latest_block=1000, latest_ts=1000,
    )
    assert out == 1000 - 50  # 950


def test_enrich_happy_path_backfills_taker(tmp_path, monkeypatch):
    monkeypatch.delenv("MARKETLENS_POLYGON_LIVE", raising=False)
    trades = [_rt("0xtx1"), _rt("0xtx2"), _rt("0xtx3")]
    logs = [
        _build_order_filled_log(tx_hash="0xtx1", maker=PROXY_WALLET,
                                taker=COUNTERPARTY),
        _build_order_filled_log(tx_hash="0xtx2", maker=PROXY_WALLET,
                                taker=COUNTERPARTY),
        _build_order_filled_log(tx_hash="0xtx3", maker=PROXY_WALLET,
                                taker=COUNTERPARTY),
    ]
    _seed_cache(tmp_path, logs=logs)
    client = PolygonClient(cache_dir=tmp_path)

    out = enrich_with_takers(client, trades, "yes-token-x")
    assert len(out) == 3
    assert all(t.taker_address == COUNTERPARTY for t in out)
    # Original list unchanged
    assert all(t.taker_address == "" for t in trades)


def test_enrich_partial_match(tmp_path, monkeypatch):
    """Only trades whose tx_hash appears in the logs get takers."""
    monkeypatch.delenv("MARKETLENS_POLYGON_LIVE", raising=False)
    trades = [_rt("0xtx1"), _rt("0xtx2"), _rt("0xtxNOMATCH")]
    logs = [
        _build_order_filled_log(tx_hash="0xtx1", maker=PROXY_WALLET,
                                taker=COUNTERPARTY),
        _build_order_filled_log(tx_hash="0xtx2", maker=PROXY_WALLET,
                                taker=COUNTERPARTY),
    ]
    _seed_cache(tmp_path, logs=logs)
    client = PolygonClient(cache_dir=tmp_path)

    out = enrich_with_takers(client, trades, "yes-token-x")
    by_id = {t.trade_id: t for t in out}
    assert by_id["0xtx1"].taker_address == COUNTERPARTY
    assert by_id["0xtx2"].taker_address == COUNTERPARTY
    assert by_id["0xtxNOMATCH"].taker_address == ""


def test_enrich_self_fill_keeps_taker_empty(tmp_path, monkeypatch):
    """A trade where the only on-chain wallet is the proxyWallet itself
    (self-fill) leaves taker empty — there's no real counterparty."""
    monkeypatch.delenv("MARKETLENS_POLYGON_LIVE", raising=False)
    trades = [_rt("0xtx1")]
    logs = [
        # Both maker AND taker are the proxyWallet — self-fill
        _build_order_filled_log(tx_hash="0xtx1", maker=PROXY_WALLET,
                                taker=PROXY_WALLET),
    ]
    _seed_cache(tmp_path, logs=logs)
    client = PolygonClient(cache_dir=tmp_path)

    out = enrich_with_takers(client, trades, "yes-token-x")
    assert out[0].taker_address == ""


def test_enrich_no_cache_no_live_passes_through(tmp_path, monkeypatch,
                                                 caplog):
    """No cached responses and no LIVE flag → trades unchanged, warning."""
    monkeypatch.delenv("MARKETLENS_POLYGON_LIVE", raising=False)
    trades = [_rt("0xtx1"), _rt("0xtx2")]
    client = PolygonClient(cache_dir=tmp_path)

    import logging
    with caplog.at_level(logging.WARNING,
                          logger="app.anomaly.network.enrichment"):
        out = enrich_with_takers(client, trades, "yes-token-x")
    assert out == trades  # unchanged (same list, never wrapped)
    assert all(t.taker_address == "" for t in out)
    # Warning logged
    assert any("unavailable" in r.message for r in caplog.records)


def test_enrich_empty_input_returns_empty(tmp_path):
    # Use pytest's tmp_path instead of a hardcoded "/nonexistent". On
    # Windows the latter resolved to D:\nonexistent (writable) and
    # passed locally; on Linux CI it's a root-fs path the runner can't
    # mkdir, so PolygonClient.__post_init__ raised PermissionError
    # before the test body ever ran. Tmp dir gives a guaranteed-
    # writable, test-scoped path.
    client = PolygonClient(cache_dir=tmp_path / "polygon-cache")
    assert enrich_with_takers(client, [], "yes-token-x") == []
