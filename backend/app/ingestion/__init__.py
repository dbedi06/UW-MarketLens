"""S1 — Polymarket ingestion package."""
from .polymarket import fetch_market, fetch_library_markets, RawMarket, RawTrade

__all__ = ["fetch_market", "fetch_library_markets", "RawMarket", "RawTrade"]
