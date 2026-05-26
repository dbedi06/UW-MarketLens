"""Tests for the Polygon on-chain trader-network subpackage (A3).

These run entirely against committed fixtures + in-memory Trade lists
(no live RPC, no env flags). A separate optional smoke test that hits
the real chain is documented in the module docstrings but not part of
the default suite.
"""

from __future__ import annotations
import os
from pathlib import Path

import numpy as np
import pytest

from app.anomaly.network import (
    NETWORK_FEATURE_NAMES,
    PolygonClient,
    RpcUnavailable,
    TraderGraph,
    build_trader_graph,
    network_features_for_market,
)
from app.anomaly.network.trader_graph import (
    Trade,
    largest_component_size,
    repeat_counterparty_ratio,
    top_trader_hhi,
    unique_wallets,
)


# ---- trader graph: pure-function math ------------------------------------

def _t(ts, mkt, mk, tk, size=1.0) -> Trade:
    return Trade(timestamp=ts, market_id=mkt, maker=mk, taker=tk, size=size)


def test_build_trader_graph_collects_wallets_and_weights():
    trades = [
        _t(100, "m1", "A", "B"),
        _t(110, "m1", "A", "B"),  # repeat pair -> weight 2
        _t(120, "m1", "A", "C"),
        _t(130, "m1", "D", "E"),
    ]
    g = build_trader_graph(trades)
    assert g.wallets == {"A", "B", "C", "D", "E"}
    assert g.edge_weights[("A", "B")] == 2
    assert g.edge_weights[("A", "C")] == 1
    assert g.edge_weights[("D", "E")] == 1


def test_self_trade_counted_in_trades_per_wallet_no_edge():
    trades = [_t(100, "m1", "A", "A"), _t(110, "m1", "A", "B")]
    g = build_trader_graph(trades)
    assert ("A", "A") not in g.edge_weights
    assert g.trades_per_wallet["A"] == 3  # self counted twice + B once


def test_unique_wallets_count():
    g = build_trader_graph([_t(1, "m", "X", "Y"), _t(2, "m", "Y", "Z")])
    assert unique_wallets(g) == 3


def test_top_trader_hhi_extremes():
    """All trade by one wallet (with itself) -> HHI=1.0. Perfectly
    balanced two wallets -> HHI=0.5."""
    g_solo = build_trader_graph([_t(1, "m", "A", "A")])
    assert top_trader_hhi(g_solo) == pytest.approx(1.0)
    g_balanced = build_trader_graph([_t(1, "m", "A", "B")])
    # A and B each traded once -> 2 entries of 1/2 -> HHI = 0.5
    assert top_trader_hhi(g_balanced) == pytest.approx(0.5)


def test_repeat_counterparty_ratio_wash_signature():
    """3 unique pairs, 2 of which repeat -> ratio 2/3."""
    trades = [
        _t(1, "m", "A", "B"), _t(2, "m", "A", "B"),  # repeat
        _t(3, "m", "C", "D"), _t(4, "m", "C", "D"),  # repeat
        _t(5, "m", "E", "F"),                         # single
    ]
    g = build_trader_graph(trades)
    assert repeat_counterparty_ratio(g) == pytest.approx(2 / 3)


def test_largest_component_size_components():
    """Two disconnected components: {A,B,C} (size 3) and {D,E} (size 2)."""
    trades = [
        _t(1, "m", "A", "B"),
        _t(2, "m", "B", "C"),
        _t(3, "m", "D", "E"),
    ]
    g = build_trader_graph(trades)
    assert largest_component_size(g) == 3


def test_empty_graph_stats_are_zero():
    g = build_trader_graph([])
    assert unique_wallets(g) == 0
    assert top_trader_hhi(g) == 0.0
    assert repeat_counterparty_ratio(g) == 0.0
    assert largest_component_size(g) == 0


# ---- per-window network features ----------------------------------------

def test_network_features_per_window_shape_and_zero_when_empty():
    trades = [_t(100, "m", "A", "B"), _t(140, "m", "A", "B")]
    feats = network_features_for_market(
        trades, window_starts=[0, 100, 200, 300], window_size_s=100,
    )
    assert feats.shape == (4, len(NETWORK_FEATURE_NAMES))
    # window starting at 0 covers ts 0-99 -> empty
    assert (feats[0] == 0.0).all()
    # window starting at 100 covers ts 100-199 -> both trades
    assert feats[1, NETWORK_FEATURE_NAMES.index("net_unique_wallets")] == 2.0
    assert (feats[2] == 0.0).all() and (feats[3] == 0.0).all()


def test_network_features_repeat_pair_detected():
    """Within one window the same pair traded 5x -> repeat_counterparty
    ratio should equal 1.0 (single edge with weight > 1)."""
    trades = [_t(100 + i, "m", "A", "B") for i in range(5)]
    feats = network_features_for_market(
        trades, window_starts=[100], window_size_s=100,
    )
    rc_col = NETWORK_FEATURE_NAMES.index("net_repeat_counterparty")
    assert feats[0, rc_col] == pytest.approx(1.0)


# ---- PolygonClient: cache-only, no live RPC ------------------------------

def test_polygon_client_raises_rpc_unavailable_without_cache(tmp_path,
                                                            monkeypatch):
    """No cache, no live flag -> explicit error (we never fabricate)."""
    monkeypatch.delenv("MARKETLENS_POLYGON_LIVE", raising=False)
    cli = PolygonClient(cache_dir=tmp_path)
    with pytest.raises(RpcUnavailable):
        cli.block_number()


def test_polygon_client_returns_cached(tmp_path, monkeypatch):
    """A cached fixture is loaded without touching the network."""
    monkeypatch.delenv("MARKETLENS_POLYGON_LIVE", raising=False)
    cli = PolygonClient(cache_dir=tmp_path)
    # Build the cache file the client would write — request shape mirrors
    # what `block_number` sends.
    from app.anomaly.network.polygon_client import _cache_key
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber",
               "params": []}
    key = _cache_key(payload)
    (tmp_path / f"{key}.json").write_text(
        '{"request": {}, "result": "0x10000"}', encoding="utf-8")
    assert cli.block_number() == 0x10000


def test_polygon_client_get_logs_returns_empty_when_cache_empty(tmp_path,
                                                                monkeypatch):
    monkeypatch.delenv("MARKETLENS_POLYGON_LIVE", raising=False)
    cli = PolygonClient(cache_dir=tmp_path)
    # Pre-create the cache entry the client will look for.
    from app.anomaly.network.polygon_client import _cache_key
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs",
               "params": [{"fromBlock": "earliest", "toBlock": "latest"}]}
    key = _cache_key(payload)
    (tmp_path / f"{key}.json").write_text(
        '{"request": {}, "result": []}', encoding="utf-8")
    assert cli.get_logs() == []
