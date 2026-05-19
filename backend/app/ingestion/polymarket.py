"""
S1 — Polymarket Ingestion
=========================
Fetches real market data from Polymarket's public APIs (no auth required).

Two APIs in play:
  - Gamma API  https://gamma-api.polymarket.com  — market metadata, volume,
    liquidity, end date, resolution status.
  - CLOB API   https://clob.polymarket.com       — trade history per token.

Public entry points
-------------------
  fetch_market(url)  -> RawMarket
      Parse a polymarket.com URL, pull metadata + trade history for that
      market, return a RawMarket dataclass.

  fetch_library_markets(limit)  -> list[RawMarket]
      Pull the N most-active active markets — used to seed the library.

Internal flow
-------------
  URL slug  -->  Gamma /markets?slug=  -->  market + token IDs
                                        -->  CLOB /trades?token_id=  (per token)
                                        -->  RawMarket

RawMarket is the S1 output contract that S2 (feature engineering) and
mock.py's swap-out point both read. Do not change field names without
updating schemas.py and mock.py simultaneously.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, urlencode

import httpx

logger = logging.getLogger(__name__)

# ── API base URLs ────────────────────────────────────────────────────────────
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"

# ── Rate-limit guard: stay well inside Cloudflare's burst allowance ──────────
_REQUEST_DELAY_S = 0.15   # 150 ms between requests → ~6 req/s

# ── Retry config ─────────────────────────────────────────────────────────────
_MAX_RETRIES = 3
_RETRY_BACKOFF_S = 1.5


# ── Output dataclasses (the S1 "contract") ───────────────────────────────────

@dataclass
class RawTrade:
    """One matched trade from the CLOB."""
    trade_id:   str
    token_id:   str
    price:      float          # 0–1 implied probability
    size:       float          # USDC notional
    side:       str            # "BUY" or "SELL"
    timestamp:  datetime       # UTC


@dataclass
class RawMarket:
    """Everything S1 knows about one Polymarket market.

    S2 (feature engineering) consumes this directly.
    mock.py's make_market_score() is replaced by a call chain that starts here.
    """
    # Identifiers
    market_url:       str
    condition_id:     str
    question_id:      str

    # Question text (used by S4 LLM resolution checker and citation)
    question:         str

    # Tokens: Polymarket binary markets have a YES token and a NO token
    token_ids:        list[str]

    # Aggregate market stats (from Gamma)
    volume_usd:       float
    liquidity_usd:    float
    unique_traders:   int

    # Prices: last-traded YES probability (0–1)
    yes_price:        float
    spread:           float        # ask_price - bid_price at snapshot time

    # Lifecycle
    end_date:         Optional[datetime]
    resolved:         bool
    resolution:       Optional[str]   # "YES" / "NO" / None if unresolved

    # Raw trade history (YES token trades, newest-first)
    trades:           list[RawTrade] = field(default_factory=list)

    # When this snapshot was taken
    fetched_at:       datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ── HTTP helpers ─────────────────────────────────────────────────────────────

def _get(client: httpx.Client, url: str, params: dict | None = None) -> dict | list:
    """GET with retries and rate-limit delay."""
    time.sleep(_REQUEST_DELAY_S)
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            r = client.get(url, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                wait = _RETRY_BACKOFF_S * (attempt + 1)
                logger.warning("Rate-limited; waiting %.1fs before retry %d", wait, attempt + 1)
                time.sleep(wait)
                last_exc = exc
            else:
                raise
        except httpx.RequestError as exc:
            logger.warning("Request error on attempt %d: %s", attempt + 1, exc)
            time.sleep(_RETRY_BACKOFF_S)
            last_exc = exc
    raise RuntimeError(f"Failed after {_MAX_RETRIES} retries") from last_exc


# ── URL parsing ──────────────────────────────────────────────────────────────

def _slug_from_url(url: str) -> str:
    """
    Extract the event slug from a polymarket.com URL.

    Polymarket URLs look like:
      https://polymarket.com/event/will-the-fed-cut-rates-in-2025
      https://polymarket.com/event/will-the-fed-cut-rates-in-2025?tid=...

    The slug is the last path segment (everything after /event/).
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    # Path is e.g. /event/will-the-fed-cut-rates-in-2025
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2 or parts[0] != "event":
        raise ValueError(
            f"Expected a URL like polymarket.com/event/<slug>, got: {url!r}"
        )
    return parts[1]


# ── Gamma API calls ───────────────────────────────────────────────────────────

def _fetch_gamma_market(client: httpx.Client, slug: str) -> dict:
    """
    GET /events?slug=<slug> returns a list of event objects.
    Each event contains a list of markets (binary outcomes).
    We want the first event that matches.
    """
    data = _get(client, f"{GAMMA_BASE}/events", params={"slug": slug})
    if not data:
        raise ValueError(f"No Gamma event found for slug: {slug!r}")
    # data is a list; take the first match
    event = data[0] if isinstance(data, list) else data
    markets = event.get("markets", [])
    if not markets:
        raise ValueError(f"Event {slug!r} has no markets")
    return event


def _parse_gamma_market(event: dict, url: str) -> dict:
    """
    Pull the fields we need out of a Gamma event object.
    Gamma nests individual outcome markets under event["markets"].
    We aggregate volume/liquidity across all outcomes for the event.
    """
    markets = event.get("markets", [])

    # Sum volume and liquidity across all outcome markets in this event
    volume_usd    = sum(float(m.get("volumeNum", 0) or 0) for m in markets)
    liquidity_usd = sum(float(m.get("liquidityNum", 0) or 0) for m in markets)

    # Use the first (YES) market for token IDs, price, and metadata
    primary = markets[0]
    token_ids = [t["token_id"] for t in primary.get("tokens", []) if "token_id" in t]
    if not token_ids:
        # Fall back to clob_token_ids if tokens list is absent
        token_ids = primary.get("clobTokenIds", [])

    # Outcome prices: ["0.62", "0.38"] → YES price is index 0
    outcome_prices = primary.get("outcomePrices", ["0.5", "0.5"])
    try:
        yes_price = float(outcome_prices[0])
    except (IndexError, ValueError):
        yes_price = 0.5

    # Resolution
    resolved = bool(primary.get("closed", False))
    # Gamma uses "winner" field when resolved ("Yes" / "No")
    winner_raw = (primary.get("winner") or "").strip().upper()
    resolution = winner_raw if winner_raw in ("YES", "NO") else None

    # End date
    end_date_str = primary.get("endDate") or event.get("endDate")
    end_date: Optional[datetime] = None
    if end_date_str:
        try:
            # Gamma returns ISO strings; strip trailing Z if present
            end_date = datetime.fromisoformat(
                end_date_str.replace("Z", "+00:00")
            )
        except ValueError:
            pass

    return {
        "condition_id":   primary.get("conditionId", ""),
        "question_id":    primary.get("questionID", ""),
        "question":       event.get("title") or primary.get("question", ""),
        "token_ids":      token_ids,
        "volume_usd":     volume_usd,
        "liquidity_usd":  liquidity_usd,
        # Gamma doesn't expose unique_traders directly; 0 is the honest default
        # S2 can derive an approximation from trade history if needed
        "unique_traders": int(primary.get("uniqueTraderCount", 0)),
        "yes_price":      yes_price,
        "spread":         abs(1.0 - yes_price - (1.0 - yes_price)),  # best-effort
        "end_date":       end_date,
        "resolved":       resolved,
        "resolution":     resolution,
    }


# ── CLOB API calls ────────────────────────────────────────────────────────────

def _fetch_clob_trades(
    client: httpx.Client,
    token_id: str,
    limit: int = 500,
) -> list[RawTrade]:
    """
    GET /trades?token_id=<id>&limit=<n>

    Returns up to `limit` most recent trades for this token.
    The CLOB /trades endpoint is public (no auth).
    """
    data = _get(
        client,
        f"{CLOB_BASE}/trades",
        params={"market": token_id, "limit": limit},
    )
    trades: list[RawTrade] = []
    raw_list = data if isinstance(data, list) else data.get("data", [])
    for t in raw_list:
        try:
            ts_raw = t.get("timestamp") or t.get("matchTime", "")
            # Timestamps come as ISO strings or Unix seconds
            if isinstance(ts_raw, (int, float)):
                ts = datetime.fromtimestamp(float(ts_raw), tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(
                    str(ts_raw).replace("Z", "+00:00")
                )
            trades.append(
                RawTrade(
                    trade_id=str(t.get("id", t.get("tradeId", ""))),
                    token_id=token_id,
                    price=float(t.get("price", 0)),
                    size=float(t.get("size", t.get("usdcSize", 0))),
                    side=str(t.get("side", "BUY")).upper(),
                    timestamp=ts,
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed trade record: %s — %s", t, exc)
    # newest first
    trades.sort(key=lambda x: x.timestamp, reverse=True)
    return trades


def _fetch_clob_spread(client: httpx.Client, token_id: str) -> float:
    """
    GET /spread?token_id=<id>  returns {"spread": "0.02"} or similar.
    Falls back to 0.0 on any error — spread is a nice-to-have for S2,
    not a hard requirement.
    """
    try:
        data = _get(client, f"{CLOB_BASE}/spread", params={"token_id": token_id})
        return float(data.get("spread", 0))
    except Exception:
        return 0.0


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_market(url: str, trade_limit: int = 500) -> RawMarket:
    """
    Full S1 fetch for one Polymarket URL.

    Steps
    -----
    1. Parse URL → slug
    2. Gamma /events?slug=  → metadata
    3. CLOB /trades?market=  → trade history for YES token
    4. CLOB /spread?token_id= → current spread
    5. Assemble RawMarket

    Raises
    ------
    ValueError   – bad URL or market not found
    RuntimeError – network failure after retries
    """
    slug = _slug_from_url(url)

    with httpx.Client(
        headers={"User-Agent": "UW-MarketLens/0.1 (research project)"},
        follow_redirects=True,
    ) as client:
        event   = _fetch_gamma_market(client, slug)
        parsed  = _parse_gamma_market(event, url)

        # Fetch trades for the YES token (index 0) — that's what S2 uses for
        # the price series and feature vectors
        trades: list[RawTrade] = []
        spread = parsed["spread"]
        if parsed["token_ids"]:
            yes_token = parsed["token_ids"][0]
            trades = _fetch_clob_trades(client, yes_token, limit=trade_limit)
            spread = _fetch_clob_spread(client, yes_token) or spread

    return RawMarket(
        market_url=url,
        condition_id=parsed["condition_id"],
        question_id=parsed["question_id"],
        question=parsed["question"],
        token_ids=parsed["token_ids"],
        volume_usd=parsed["volume_usd"],
        liquidity_usd=parsed["liquidity_usd"],
        unique_traders=parsed["unique_traders"],
        yes_price=parsed["yes_price"],
        spread=spread,
        end_date=parsed["end_date"],
        resolved=parsed["resolved"],
        resolution=parsed["resolution"],
        trades=trades,
    )


def fetch_library_markets(limit: int = 20) -> list[RawMarket]:
    """
    Pull the `limit` most-active open markets from Gamma.

    Used by the library endpoint to seed the market list with real data
    instead of the hardcoded _SAMPLE_URLS in mock.py.

    Markets are sorted by 24h volume descending so the library shows
    the most relevant active markets first.
    """
    with httpx.Client(
        headers={"User-Agent": "UW-MarketLens/0.1 (research project)"},
        follow_redirects=True,
    ) as client:
        data = _get(
            client,
            f"{GAMMA_BASE}/markets",
            params={
                "active":       "true",
                "closed":       "false",
                "order":        "volume24hr",
                "ascending":    "false",
                "limit":        limit,
                "enableOrderBook": "true",
            },
        )

    markets_raw = data if isinstance(data, list) else data.get("data", [])
    results: list[RawMarket] = []
    for m in markets_raw[:limit]:
        slug = m.get("slug") or m.get("marketSlug", "")
        if not slug:
            continue
        url = f"https://polymarket.com/event/{slug}"
        try:
            rm = fetch_market(url, trade_limit=200)
            results.append(rm)
        except Exception as exc:
            logger.warning("Skipping market %s: %s", url, exc)

    return results
