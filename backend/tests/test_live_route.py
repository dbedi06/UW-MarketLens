from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.ingestion.polymarket import RawMarket
from app.resolution import ResolutionAssessment


class _FakeDetector:
    def score(self, features):
        return np.array([0.2, 0.3, 0.4])


def _market() -> RawMarket:
    return RawMarket(
        market_url="https://polymarket.com/event/will-the-fed-cut-rates-in-2025",
        condition_id="cond-1",
        question_id="q-1",
        question="Will the Fed cut rates in 2025?",
        token_ids=["yes-token", "no-token"],
        volume_usd=10000.0,
        liquidity_usd=2500.0,
        unique_traders=34,
        yes_price=0.55,
        spread=0.01,
        end_date=None,
        resolved=False,
        resolution=None,
        trades=[],
        fetched_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
    )


def test_live_score_uses_s4_resolution_output(monkeypatch):
    market = _market()

    def fake_fetch_market(url):
        assert url == market.market_url
        return market

    def fake_from_trades_with_network(market_obj):
        assert market_obj is market
        X_base = np.array([[0.10, 0.01], [0.12, 0.02], [0.11, 0.015]])
        X_net = np.array([[0.0], [0.0], [0.0]])
        mid = np.array([0.5, 0.5, 0.5])
        widx = np.array([0, 1, 2])
        return X_base, X_net, mid, widx

    def fake_feature_matrix_streams_with_network(X_base, X_net, mid, widx):
        assert X_base.shape == (3, 2)
        assert X_net.shape == (3, 1)
        assert mid.shape == (3,)
        assert widx.tolist() == [0, 1, 2]
        return np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]])

    def fake_resolve_market(question, resolved=False):
        assert question == market.question
        assert resolved is False
        return ResolutionAssessment(
            verdict="HIGH",
            reasoning="Independent reporting corroborates the outcome.",
            supporting_sources=["https://example.com/article-one"],
            confidence=0.8,
            resolution_quality=80,
            used_fallback=False,
        )

    monkeypatch.setattr("app.routes.live.fetch_market", fake_fetch_market)
    monkeypatch.setattr("app.routes.live.from_trades_with_network", fake_from_trades_with_network)
    monkeypatch.setattr("app.routes.live.feature_matrix_streams_with_network", fake_feature_matrix_streams_with_network)
    monkeypatch.setattr("app.routes.live.anomaly_scoring.get_detector", lambda: _FakeDetector())
    monkeypatch.setattr("app.routes.live.resolve_market", fake_resolve_market)

    client = TestClient(app)
    response = client.post(
        "/api/live/score",
        json={"url": market.market_url, "as_of": "2026-05-26"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resolution"]["verdict"] == "HIGH"
    assert payload["resolution"]["reasoning"] == "Independent reporting corroborates the outcome."
    assert payload["resolution"]["supporting_sources"] == ["https://example.com/article-one"]
    assert payload["subscores"]["resolution_quality"] == 80
    assert payload["reliability_score"] == 54
    assert "NewsAPI and Claude" in payload["reasons"][2]["detail"]
