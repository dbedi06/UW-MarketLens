"""Tests for the snapshot namespace dispatch (B2).

Before the fix, /api/live/score wrote into the same _SNAPSHOTS dict as
/api/score and the snapshot route always re-rendered via mock — so a
live permalink, when reopened, served mock data. These tests verify the
dispatch goes to the right path based on the registered source.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from fastapi.testclient import TestClient

from app import mock
from app.ingestion.cache import LIVE_ENV_FLAG


FIX = Path(__file__).parent / "fixtures" / "polymarket"
GAMMA_FIXTURE = json.loads((FIX / "gamma_event_fed_rates.json").read_text())
CLOB_FIXTURE = json.loads((FIX / "clob_trades_fed_rates.json").read_text())


def _seed_cache(tmp_path: Path, monkeypatch) -> str:
    """Warm the ingestion cache with the fed-rates fixture and return the URL."""
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
    return url


def test_mock_snapshot_returns_mock_data():
    """Sanity baseline: a snapshot registered by the mock route resolves
    via mock.make_market_score."""
    from app.main import app
    with TestClient(app) as client:
        # Score via mock → registers snapshot as "mock"
        r = client.post("/api/score", json={"url": "https://polymarket.com/event/foo"})
        assert r.status_code == 200, r.text
        sid = r.json()["snapshot_id"]
        assert r.json()["source"] == "mock"

        # Resolve permalink → still mock
        r2 = client.get(f"/api/snapshot/{sid}")
        assert r2.status_code == 200, r2.text
        assert r2.json()["source"] == "mock"
        # Mock is deterministic, so the snapshot view equals the original.
        assert r2.json()["reliability_score"] == r.json()["reliability_score"]


def test_live_snapshot_returns_live_data_not_mock(tmp_path, monkeypatch):
    """B2: a snapshot produced by the live route must resolve back to
    live data, not silently substitute mock."""
    url = _seed_cache(tmp_path, monkeypatch)
    from app.main import app
    with TestClient(app) as client:
        r = client.post("/api/live/score", json={"url": url})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] == "live"
        sid = body["snapshot_id"]
        live_score = body["reliability_score"]
        live_anomaly = body["subscores"]["anomaly"]

        # Reopen via permalink → should still be live, with matching values
        r2 = client.get(f"/api/snapshot/{sid}")
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        assert body2["source"] == "live", (
            "B2 regression: live permalink fell back to mock"
        )
        assert body2["reliability_score"] == live_score
        assert body2["subscores"]["anomaly"] == live_anomaly


def test_og_card_dispatches_to_live_for_live_snapshots(tmp_path, monkeypatch):
    """Bug 2: /api/og/{sid} was always rendering via mock, even when the
    snapshot was registered as live. The OG card therefore showed a
    different score than the report it pointed at. Fixed by dispatching
    on source like /api/snapshot does."""
    url = _seed_cache(tmp_path, monkeypatch)
    from app.main import app
    with TestClient(app) as client:
        r = client.post("/api/live/score", json={"url": url})
        assert r.status_code == 200, r.text
        live_body = r.json()
        sid = live_body["snapshot_id"]
        live_score = live_body["reliability_score"]

        og = client.get(f"/api/og/{sid}")
    assert og.status_code == 200
    # SVG embeds the score as text; mock would produce a deterministic-
    # but-different number, so equality is the right discriminator.
    assert str(live_score) in og.text, (
        f"OG card body did not contain live score {live_score}; "
        f"first 400 chars: {og.text[:400]}"
    )


def test_live_snapshot_cold_cache_returns_503_not_500(tmp_path, monkeypatch):
    """If the live snapshot's cache has been wiped (e.g., after a Render
    dyno wake), /api/snapshot should produce a friendly 503 — not crash."""
    url = _seed_cache(tmp_path, monkeypatch)
    from app.main import app
    with TestClient(app) as client:
        r = client.post("/api/live/score", json={"url": url})
        sid = r.json()["snapshot_id"]

    # Simulate a fresh, empty cache for the snapshot fetch (the registry
    # entry still exists from the prior process; the cache files don't).
    monkeypatch.setattr("app.ingestion.cache.CACHE_DIR", tmp_path / "empty")
    (tmp_path / "empty").mkdir(parents=True, exist_ok=True)

    # Composite's in-process MarketScore cache also survives a dyno wake
    # within the same process, so the snapshot-restart simulation must
    # clear it explicitly to model a true cold start.
    from app import composite
    composite._LIVE_SCORE_CACHE.clear()

    with TestClient(app) as client:
        r2 = client.get(f"/api/snapshot/{sid}")
    assert r2.status_code == 503, r2.text
    # Don't leak a 500 traceback to the user
    assert "cold" in r2.text.lower() or "cache" in r2.text.lower()
