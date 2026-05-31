"""Test the live route end-to-end.

The route is now a thin wrapper around `composite.make_market_score`,
so the test exercises the full S1→S3→S4→S5→S6→S7 chain with the
external dependencies (Polymarket fetch, LLM calls) mocked out at the
composite level.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.ingestion.polymarket import RawMarket, RawTrade
from app.resolution import ResolutionAssessment
from app.tagger import TagResult


def _market_with_trades(n_windows: int = 6) -> RawMarket:
    """Build a RawMarket with enough trade tape to clear composite's
    `>=4 windows` threshold."""
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    trades = []
    for i in range(n_windows * 3):  # ~3 trades per window
        trades.append(RawTrade(
            trade_id=f"t{i}", token_id="yes-token",
            price=0.5 + (i % 5) * 0.01, size=100.0 + i,
            side="BUY",
            timestamp=t0.replace(minute=(i * 5) % 60,
                                 hour=12 + (i * 5) // 60),
            maker_address=f"0xWallet{i % 4}",
            taker_address=f"0xWallet{(i + 1) % 4}",
        ))
    return RawMarket(
        market_url="https://polymarket.com/event/will-the-fed-cut-rates-in-2025",
        condition_id="cond-1",
        question_id="q-1",
        question="Will the Fed cut rates in 2025?",
        token_ids=["yes-token", "no-token"],
        volume_usd=10000.0, liquidity_usd=2500.0,
        unique_traders=34,
        yes_price=0.55, spread=0.01,
        end_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
        resolved=False, resolution=None,
        trades=trades,
        fetched_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
    )


def test_live_score_uses_s4_s5_s6_s7_end_to_end(monkeypatch):
    """The route now calls composite, which calls S4 (resolution),
    S5 (tagger), S6 (citation), and applies S7's 35/40/25 weights.
    Mock the external dependencies; assert the wiring."""
    market = _market_with_trades()

    # composite.py does `from .X import Y` *inside* make_market_score,
    # so we patch the source modules — each call re-binds the local name.
    monkeypatch.setattr("app.ingestion.fetch_market", lambda url: market)
    monkeypatch.setattr(
        "app.resolution.resolve_market",
        lambda question, resolved=False: ResolutionAssessment(
            verdict="HIGH",
            reasoning="Independent reporting corroborates the outcome.",
            supporting_sources=["https://example.com/article"],
            confidence=0.8,
            resolution_quality=80,
            used_fallback=False,
        ),
    )
    monkeypatch.setattr(
        "app.tagger.tag_market",
        lambda question: TagResult(
            departments=["ECON", "EVANS"], course_applicability=85,
            used_fallback=False,
        ),
    )

    with TestClient(app) as client:
        r = client.post(
            "/api/live/score",
            json={"url": market.market_url, "as_of": "2026-05-26"},
        )
    assert r.status_code == 200, r.text
    body = r.json()

    # S4 output flows through verbatim
    assert body["resolution"]["verdict"] == "HIGH"
    assert body["resolution"]["supporting_sources"] == ["https://example.com/article"]
    assert body["subscores"]["resolution_quality"] == 80

    # S5 output replaces the old hardcoded ["ECON"]
    assert body["tags"]["departments"] == ["ECON", "EVANS"]
    assert body["tags"]["course_applicability"] == 85

    # S6 produces real BibTeX, not the mock placeholder
    assert body["citation"]["bibtex"].startswith("@misc{marketlens_")
    assert "Polymarket" in body["citation"]["apa"]

    # S7 composite uses 35/40/25 weights
    sub = body["subscores"]
    expected = round(
        0.35 * sub["liquidity_health"]
        + 0.40 * sub["anomaly"]
        + 0.25 * sub["resolution_quality"]
    )
    assert body["reliability_score"] == expected

    # source field set to "live"
    assert body["source"] == "live"

    # S6 RIS export now flows through citation
    assert "TY  - " in body["citation"]["ris"]
    assert "ER  - " in body["citation"]["ris"]

    # Track 4: SHAP per-window attributions populated by composite
    # (5 features per the top_k=5 cap; may be fewer if the model has
    # fewer features, but should be a non-empty list here).
    assert isinstance(body["anomaly"]["top_contributions"], list)
    assert len(body["anomaly"]["top_contributions"]) > 0
    sample = body["anomaly"]["top_contributions"][0]
    assert {"feature", "value", "shap"}.issubset(sample.keys())
