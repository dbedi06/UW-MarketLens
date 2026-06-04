"""Shared pytest fixtures.

composite._LIVE_SCORE_CACHE is module-level state — without clearing
it between tests, a result from one test can satisfy a snapshot-fetch
in another and mask regressions.
"""
import pytest


@pytest.fixture(autouse=True)
def _clear_composite_cache():
    from app import composite, snapshot_store
    composite._LIVE_SCORE_CACHE.clear()
    snapshot_store.clear()
    yield
    composite._LIVE_SCORE_CACHE.clear()
    snapshot_store.clear()
