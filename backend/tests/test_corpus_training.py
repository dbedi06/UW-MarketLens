"""Tests for the real-corpus training path (Phase 2 of the v0.9 push).

These exercise the JSON loader + the corpus trainer + the pickle
round-trip + the get_detector resolution order. No live HTTP — uses
a tiny on-disk corpus fixture built in `tmp_path`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from app.anomaly import scoring as anomaly_scoring
from app.anomaly.scoring import (
    _load_corpus_market, get_detector, reset_detector, save_detector,
    train_from_corpus,
)
from app.ingestion.polymarket import RawMarket, RawTrade


UTC = timezone.utc


def _market_json(market: RawMarket) -> dict:
    """Serialize a RawMarket the way build_real_corpus.py does."""
    from dataclasses import asdict
    payload = asdict(market)
    def _convert(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_convert(x) for x in obj]
        return obj
    return _convert(payload)


def _build_market(condition_id: str, n_windows: int = 6) -> RawMarket:
    """Build a RawMarket with enough trades to clear the >=3 windows
    threshold the trainer uses."""
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    trades = []
    for i in range(n_windows * 4):  # ~4 trades per window
        trades.append(RawTrade(
            trade_id=f"0x{condition_id[:8]}{i:04d}",
            token_id="yes-token",
            price=0.45 + 0.01 * (i % 11),
            size=100.0 + i * 5,
            side="BUY" if i % 2 else "SELL",
            timestamp=t0 + timedelta(minutes=i * 4),
            maker_address=f"0xWallet{i % 7}",
            taker_address=f"0xWallet{(i + 3) % 7}",
        ))
    return RawMarket(
        market_url=f"https://polymarket.com/event/test-{condition_id[:8]}",
        condition_id=condition_id,
        question_id=f"q-{condition_id[:8]}",
        question=f"Test market {condition_id[:8]}?",
        token_ids=["yes-token", "no-token"],
        volume_usd=10000.0, liquidity_usd=2500.0,
        unique_traders=7,
        yes_price=0.5, spread=0.01,
        end_date=datetime(2026, 6, 1, tzinfo=UTC),
        resolved=True, resolution="YES",
        trades=trades,
    )


@pytest.fixture
def tiny_corpus(tmp_path):
    """Two minimal RawMarket JSONs on disk."""
    for i, cid in enumerate(["0xaa" + "1" * 62, "0xbb" + "2" * 62]):
        market = _build_market(cid)
        (tmp_path / f"{cid}.json").write_text(
            json.dumps(_market_json(market), indent=2),
            encoding="utf-8",
        )
    return tmp_path


def test_load_corpus_market_round_trips_dataclasses(tiny_corpus):
    """RawMarket → JSON → _load_corpus_market should reconstruct the
    dataclass with datetime fields parsed correctly."""
    paths = sorted(tiny_corpus.glob("*.json"))
    assert len(paths) == 2
    market = _load_corpus_market(paths[0])
    assert isinstance(market, RawMarket)
    assert market.condition_id.startswith("0xaa")
    assert isinstance(market.end_date, datetime)
    assert market.end_date.tzinfo is not None
    assert len(market.trades) > 0
    assert isinstance(market.trades[0], RawTrade)
    assert isinstance(market.trades[0].timestamp, datetime)


def test_train_from_corpus_produces_calibrated_detector(tiny_corpus):
    det = train_from_corpus(tiny_corpus)
    assert hasattr(det, "_reference_scores")
    assert det._reference_scores.size > 0
    assert hasattr(det, "_network_medians")
    assert det._network_medians.shape == (4,)
    assert det._trained_on == "real-corpus"
    assert det._corpus_n_markets == 2
    assert det._corpus_n_windows > 0


def test_train_from_corpus_raises_on_empty_dir(tmp_path):
    with pytest.raises(ValueError, match="No corpus JSONs"):
        train_from_corpus(tmp_path)


def test_pickle_round_trip_preserves_scoring(tiny_corpus, tmp_path):
    """Save → load → score on the same input must match within numerical
    tolerance. Confirms the pickle is fully serializable."""
    det = train_from_corpus(tiny_corpus)
    pkl = tmp_path / "model.pkl"
    save_detector(det, pkl)

    # Score a constructed feature vector with both detectors.
    from app.anomaly.scoring import _load_detector
    loaded = _load_detector(pkl)
    assert loaded is not None
    assert loaded._trained_on == "real-corpus"
    assert loaded._corpus_n_markets == det._corpus_n_markets

    # Reference scores must match exactly
    np.testing.assert_array_equal(
        det._reference_scores, loaded._reference_scores,
    )
    np.testing.assert_array_equal(
        det._network_medians, loaded._network_medians,
    )


def test_get_detector_prefers_pickle_over_synthetic(tiny_corpus, tmp_path,
                                                     monkeypatch):
    """When a pickle is present at MODEL_PATH, get_detector loads it
    instead of running the synthetic fallback."""
    det = train_from_corpus(tiny_corpus)
    pkl = tmp_path / "trained_model.pkl"
    save_detector(det, pkl)
    monkeypatch.setattr("app.anomaly.scoring.MODEL_PATH", pkl)
    reset_detector()
    loaded = get_detector()
    assert loaded._trained_on == "real-corpus"


def test_get_detector_falls_back_to_synthetic_when_pickle_missing(
    tmp_path, monkeypatch,
):
    """No pickle on disk → synthetic fit runs and the marker says so."""
    monkeypatch.setattr(
        "app.anomaly.scoring.MODEL_PATH", tmp_path / "nonexistent.pkl",
    )
    reset_detector()
    det = get_detector()
    assert det._trained_on == "synthetic"
