"""Tests for `features.from_trades` — the S1 -> S2 bridge.

Builds RawMarket fixtures in-process (no JSON files needed) so the
windowing/aggregation contract is hand-checkable.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.anomaly.features import (
    BASE_FEATURE_NAMES,
    from_trades,
    from_trades_with_network,
    _market_id_hash,
)
from app.anomaly.network import NETWORK_FEATURE_NAMES
from app.ingestion.polymarket import RawMarket, RawTrade


UTC = timezone.utc


def _trade(ts: datetime, *, price: float, size: float,
           maker: str = "0xA", taker: str = "0xB",
           tid: str = "t") -> RawTrade:
    return RawTrade(
        trade_id=tid,
        token_id="tok-yes",
        price=price,
        size=size,
        side="BUY",
        timestamp=ts,
        maker_address=maker,
        taker_address=taker,
    )


def _market(trades: list[RawTrade], *,
            end_date: datetime | None = datetime(2025, 12, 31, tzinfo=UTC)
            ) -> RawMarket:
    return RawMarket(
        market_url="https://polymarket.com/event/test-market",
        condition_id="0xCOND",
        question_id="qid",
        question="Test?",
        token_ids=["tok-yes", "tok-no"],
        volume_usd=0.0,
        liquidity_usd=0.0,
        unique_traders=0,
        yes_price=0.5,
        spread=0.0,
        end_date=end_date,
        resolved=False,
        resolution=None,
        trades=trades,
    )


# ── shape contract ──────────────────────────────────────────────────────────

def test_from_trades_returns_correct_shape_tuples():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [_trade(t0 + timedelta(minutes=i * 5),
                     price=0.5 + 0.01 * i, size=100.0)
              for i in range(4)]
    X, mid, widx = from_trades(_market(trades), window_minutes=15)

    assert X.ndim == 2 and X.shape[1] == len(BASE_FEATURE_NAMES)
    assert mid.shape == (X.shape[0],)
    assert widx.shape == (X.shape[0],)
    assert mid.dtype == np.int64 and widx.dtype == np.int64
    # all rows from same market -> single id value
    assert len(np.unique(mid)) == 1


def test_from_trades_empty_trades_returns_empty():
    X, mid, widx = from_trades(_market([]))
    assert X.shape == (0, len(BASE_FEATURE_NAMES))
    assert mid.shape == (0,) and widx.shape == (0,)


# ── window bucketing ────────────────────────────────────────────────────────

def test_window_bucketing_15min():
    # Trades at +0, +10, +20, +30 min with 15-min windows ->
    # idx 0 (0,10), idx 1 (20), idx 2 (30). Three populated windows.
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [
        _trade(t0,                         price=0.50, size=100.0),
        _trade(t0 + timedelta(minutes=10), price=0.51, size=100.0),
        _trade(t0 + timedelta(minutes=20), price=0.52, size=100.0),
        _trade(t0 + timedelta(minutes=30), price=0.53, size=100.0),
    ]
    X, _, widx = from_trades(_market(trades), window_minutes=15)
    assert X.shape[0] == 3
    assert widx.tolist() == [0, 1, 2]


def test_empty_windows_skipped_sparse_indices():
    # Trades only in windows 0 and 5; middle windows must be absent
    # (sparse window_index is fine per the relative-feature contract).
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [
        _trade(t0,                          price=0.50, size=100.0),
        _trade(t0 + timedelta(minutes=80),  price=0.60, size=100.0),
    ]
    X, _, widx = from_trades(_market(trades), window_minutes=15)
    assert X.shape[0] == 2
    assert widx.tolist() == [0, 5]


# ── per-window features ─────────────────────────────────────────────────────

def test_volume_is_sum_of_sizes_per_window():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [
        _trade(t0,                          price=0.50, size=100.0),
        _trade(t0 + timedelta(minutes=5),   price=0.51, size=250.0),
        _trade(t0 + timedelta(minutes=20),  price=0.52, size=75.0),
    ]
    X, _, _ = from_trades(_market(trades), window_minutes=15)
    # window 0: 100+250=350; window 1: 75
    assert X[0, 0] == pytest.approx(350.0)
    assert X[1, 0] == pytest.approx(75.0)


def test_unique_traders_per_window_distinct_addresses():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [
        _trade(t0,                        price=0.5, size=10, maker="0xA", taker="0xB"),
        _trade(t0 + timedelta(minutes=5), price=0.5, size=10, maker="0xA", taker="0xC"),
        _trade(t0 + timedelta(minutes=8), price=0.5, size=10, maker="0xA", taker="0xB"),
    ]
    X, _, _ = from_trades(_market(trades), window_minutes=15)
    # distinct addresses in window 0: {0xA, 0xB, 0xC} -> 3
    assert X[0, 2] == pytest.approx(3.0)


def test_price_volatility_is_stddev_of_prices():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    prices = [0.50, 0.52, 0.54, 0.56]
    trades = [_trade(t0 + timedelta(minutes=i), price=p, size=100.0)
              for i, p in enumerate(prices)]
    X, _, _ = from_trades(_market(trades), window_minutes=15)
    assert X[0, 3] == pytest.approx(np.std(prices, ddof=0))


def test_bid_ask_spread_proxy_is_price_range():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [
        _trade(t0,                        price=0.40, size=10),
        _trade(t0 + timedelta(minutes=5), price=0.65, size=10),
    ]
    X, _, _ = from_trades(_market(trades), window_minutes=15)
    assert X[0, 1] == pytest.approx(0.25)


def test_single_trade_window_volatility_is_zero_not_nan():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [_trade(t0, price=0.5, size=100.0)]
    X, _, _ = from_trades(_market(trades), window_minutes=15)
    assert X.shape[0] == 1
    assert X[0, 3] == 0.0  # stddev of single value
    assert X[0, 1] == 0.0  # spread proxy of single value
    assert not np.isnan(X).any()


# ── time_to_resolution ──────────────────────────────────────────────────────

def test_time_to_resolution_derived_from_end_date():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    end = datetime(2025, 11, 11, 12, 0, tzinfo=UTC)  # ~10 days out
    trades = [_trade(t0, price=0.5, size=100.0)]
    X, _, _ = from_trades(_market(trades, end_date=end), window_minutes=15)
    # window midpoint = t0 + 7.5min; ttr ~ 10 days - 7.5min ≈ 9.9948 days
    assert X[0, 4] == pytest.approx(9.9948, abs=0.01)


def test_none_end_date_falls_back_to_30_days_with_warning(caplog):
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [_trade(t0, price=0.5, size=100.0)]
    with caplog.at_level(logging.WARNING, logger="app.anomaly.features"):
        X, _, _ = from_trades(_market(trades, end_date=None), window_minutes=15)
    assert X[0, 4] == 30.0
    assert any("end_date" in rec.message for rec in caplog.records)


# ── market id stability ────────────────────────────────────────────────────

# ── from_trades_with_network ─────────────────────────────────────────────────

def test_from_trades_with_network_returns_four_tuple_and_widths_align():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [_trade(t0 + timedelta(minutes=i * 4),
                     price=0.5 + 0.01 * i, size=100.0,
                     maker=f"0xA{i % 3}", taker=f"0xB{i % 4}")
              for i in range(8)]
    Xb, Xn, mid, widx = from_trades_with_network(_market(trades),
                                                  window_minutes=15)
    assert Xb.shape[1] == len(BASE_FEATURE_NAMES)
    assert Xn.shape == (Xb.shape[0], len(NETWORK_FEATURE_NAMES))
    assert mid.shape == widx.shape == (Xb.shape[0],)


def test_from_trades_with_network_window_boundaries_match_from_trades():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [_trade(t0,                          price=0.5, size=10,
                     maker="0xA", taker="0xB"),
              _trade(t0 + timedelta(minutes=20),  price=0.5, size=10,
                     maker="0xA", taker="0xC")]
    Xb_a, mid_a, widx_a = from_trades(_market(trades))
    Xb_b, Xn, mid_b, widx_b = from_trades_with_network(_market(trades))
    assert np.array_equal(Xb_a, Xb_b)
    assert np.array_equal(widx_a, widx_b)


def test_from_trades_with_network_nan_when_addresses_absent():
    t0 = datetime(2025, 11, 1, 12, 0, tzinfo=UTC)
    trades = [_trade(t0 + timedelta(minutes=i * 4),
                     price=0.5, size=10.0, maker="", taker="")
              for i in range(5)]
    Xb, Xn, mid, widx = from_trades_with_network(_market(trades))
    assert np.isnan(Xn).all()
    assert Xb.shape[0] >= 1  # base path still produced rows


def test_from_trades_with_network_empty_market_returns_empty_blocks():
    Xb, Xn, mid, widx = from_trades_with_network(_market([]))
    assert Xb.shape == (0, len(BASE_FEATURE_NAMES))
    assert Xn.shape == (0, len(NETWORK_FEATURE_NAMES))
    assert mid.shape == (0,) and widx.shape == (0,)


def test_market_id_hash_is_deterministic_and_positive():
    a = _market_id_hash("https://polymarket.com/event/foo")
    b = _market_id_hash("https://polymarket.com/event/foo")
    c = _market_id_hash("https://polymarket.com/event/bar")
    assert a == b
    assert a != c
    assert a > 0 and c > 0
