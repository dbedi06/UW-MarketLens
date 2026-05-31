"""
S1 — Polymarket Ingestion
=========================
Fetches real market data from Polymarket's public APIs (no auth required
on the paths we use).

Three APIs in play
------------------
  - Gamma API     https://gamma-api.polymarket.com   — market metadata,
                                                       volume, liquidity,
                                                       end date, resolution.
  - Data API      https://data-api.polymarket.com    — public trade history
                                                       (no auth). Polymarket's
                                                       public alternative to
                                                       CLOB /trades, which is
                                                       L2-auth-gated.
  - CLOB API      https://clob.polymarket.com        — used only for /spread
                                                       (point-in-time spread
                                                       snapshot, best-effort).

Why three hosts and not the obvious two
---------------------------------------
The original implementation used CLOB /trades. Polymarket's own docs
(`llms.txt`) and the official `py-clob-client` SDK both state that
`/trades` requires Level 2 (EIP-712-signed) authentication. Production
was returning 401 for every real market URL because we were hitting an
auth-gated endpoint without credentials. The Data API (described in
`llms.txt` as the public surface for "trades, activity, and holder
information") is the supported public path. Probing confirmed it
returns trade JSON with no auth headers.

Public entry points
-------------------
  fetch_market(url)  -> RawMarket
      Parse a polymarket.com URL, pull metadata + trade history for that
      market, return a RawMarket dataclass.

  fetch_library_markets(limit)  -> list[RawMarket]
      Pull the N most-active active markets — used to seed the library.

Internal flow
-------------
  URL slug  -->  Gamma /events?slug=         -->  condition_id + token_ids
                                              -->  Data API /trades?market=<condition_id>
                                                   (filtered client-side to YES token)
                                              -->  CLOB /spread?token_id=
                                              -->  RawMarket

RawMarket is the S1 output contract that S2 (feature engineering) and
mock.py's swap-out point both read. Do not change field names without
updating schemas.py and mock.py simultaneously.
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, urlencode

import httpx

from .cache import IngestionUnavailable, cached_get

logger = logging.getLogger(__name__)

# ── API base URLs ────────────────────────────────────────────────────────────
GAMMA_BASE    = "https://gamma-api.polymarket.com"
CLOB_BASE     = "https://clob.polymarket.com"
# Data API — Polymarket's public, no-auth endpoint for trade history. The
# CLOB `/trades` endpoint requires Level 2 (EIP-712-signed) authentication
# per Polymarket's docs + py-clob-client SDK; the Data API is the public
# alternative described in their llms.txt index.
DATA_API_BASE = "https://data-api.polymarket.com"

# ── Rate-limit guard: stay well inside Cloudflare's burst allowance ──────────
_REQUEST_DELAY_S = 0.15   # 150 ms between requests → ~6 req/s

# ── Retry config ─────────────────────────────────────────────────────────────
_MAX_RETRIES = 3
_RETRY_BACKOFF_S = 1.5


# ── Output dataclasses (the S1 "contract") ───────────────────────────────────

@dataclass
class RawTrade:
    """One matched trade from the CLOB.

    `maker_address` / `taker_address` are 0x... Polygon wallet addresses
    when CLOB provides them, "" otherwise. Downstream consumers
    (A3 network features, S2 unique_traders derivation) need these —
    Lewi's first cut didn't extract them. Field-name tolerance: we try
    `maker_address` first, then `maker`, then `""`.
    """
    trade_id:        str
    token_id:        str
    price:           float          # 0–1 implied probability
    size:            float          # USDC notional
    side:            str            # "BUY" or "SELL"
    timestamp:       datetime       # UTC
    maker_address:   str = ""
    taker_address:   str = ""


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

def _get(client: httpx.Client, url: str,
         params: dict | None = None) -> dict | list:
    """GET via the on-disk cache (B4). Cache hit → no network. Cache
    miss → live fetch only if MARKETLENS_POLYMARKET_LIVE=1 is set,
    otherwise raises IngestionUnavailable. Wraps `cached_get` with the
    retry-on-429 logic since CDN rate-limits can still hit on live
    misses."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            if attempt > 0 or os.environ.get("MARKETLENS_POLYMARKET_LIVE") == "1":
                # Throttle only when an actual network call may happen
                # (cache hits don't need to sleep).
                time.sleep(_REQUEST_DELAY_S)
            return cached_get(client, url, params=params)
        except IngestionUnavailable:
            raise
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                wait = _RETRY_BACKOFF_S * (attempt + 1)
                logger.warning("Rate-limited; waiting %.1fs before retry %d",
                               wait, attempt + 1)
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


def _extract_token_ids(primary: dict) -> list[str]:
    """Pull YES/NO token ids from a Gamma market record.

    Polymarket's Gamma API has been through a few shapes; we tolerate
    three of them in this order of preference:

      1. `tokens: [{token_id, outcome}, ...]` — older shape; our
         committed fixtures use this.
      2. `clobTokenIds: '["0x...", "0x..."]'` — modern shape: a
         JSON-encoded *string* containing the array. Naively assigning
         this to a list variable gives back the string, and `[0]`
         returns the first character (a literal `[`). That was the
         smoking-gun bug behind the production 401 — CLOB returned
         `?market=[` and quite rightly refused.
      3. `clobTokenIds: ["0x...", "0x..."]` — the same field, but
         already a proper list. Belt and braces.
    """
    import json as _json

    raw_tokens = primary.get("tokens") or []
    if isinstance(raw_tokens, list):
        ids = [t["token_id"] for t in raw_tokens
               if isinstance(t, dict) and "token_id" in t]
        if ids:
            return ids

    raw_clob = primary.get("clobTokenIds")
    if isinstance(raw_clob, str):
        try:
            parsed = _json.loads(raw_clob)
        except _json.JSONDecodeError:
            parsed = []
        if isinstance(parsed, list):
            return [str(x) for x in parsed if x]
    if isinstance(raw_clob, list):
        return [str(x) for x in raw_clob if x]

    return []


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
    token_ids = _extract_token_ids(primary)

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
        # Gamma doesn't carry a live spread on event objects. Real spread
        # comes from CLOB /spread inside fetch_market; default to 0.0
        # here so fetch_library_markets has a sane default until the
        # caller does the per-token fetch.
        "spread":         0.0,
        "end_date":       end_date,
        "resolved":       resolved,
        "resolution":     resolution,
    }


# ── Data API calls (public trades) ───────────────────────────────────────────

def _fetch_market_trades(
    client: httpx.Client,
    condition_id: str,
    yes_token_id: str,
    limit: int = 500,
) -> list[RawTrade]:
    """
    GET data-api.polymarket.com/trades?market=<condition_id>&limit=<n>

    Returns up to `limit` most recent trades for the YES side of the market
    (filtered client-side by `asset == yes_token_id`).

    Why this exists
    ---------------
    CLOB `/trades` (the previous implementation) requires Level 2
    EIP-712-signed authentication per Polymarket's own docs and the
    `py-clob-client` SDK (which calls `assert_level_2_auth()` before any
    /trades request). Our existing production 401s were caused by hitting
    that auth-gated endpoint without credentials. The Data API is the
    public-no-auth alternative explicitly described in Polymarket's
    `llms.txt` docs index.

    Honest loss of signal
    ---------------------
    The Data API response includes only `proxyWallet` (the trade
    initiator) — not the counterparty. Our trader-graph features
    therefore see only one side of each edge. We map `proxyWallet` to
    `maker_address` and leave `taker_address` empty so downstream code
    (`_derive_unique_traders`, network features) continues to function
    on a reduced graph. The alternative is auth-required CLOB access,
    which is out of scope for this fix.
    """
    if not isinstance(condition_id, str) or len(condition_id) < 4:
        raise ValueError(
            f"Refusing to query Data API with malformed condition_id "
            f"{condition_id!r} (likely a Gamma parse bug)."
        )
    data = _get(
        client,
        f"{DATA_API_BASE}/trades",
        params={"market": condition_id, "limit": limit},
    )
    trades: list[RawTrade] = []
    raw_list = data if isinstance(data, list) else data.get("data", [])
    for t in raw_list:
        try:
            # Filter to the YES token if provided; the market endpoint
            # returns both YES and NO outcome trades by default.
            asset = str(t.get("asset", ""))
            if yes_token_id and asset and asset != yes_token_id:
                continue

            ts_raw = t.get("timestamp")
            # Data API returns Unix seconds (int). Fall back to ISO parse
            # for robustness in case the shape ever changes.
            if isinstance(ts_raw, (int, float)):
                ts = datetime.fromtimestamp(float(ts_raw), tz=timezone.utc)
            elif ts_raw:
                ts = datetime.fromisoformat(
                    str(ts_raw).replace("Z", "+00:00")
                )
            else:
                continue  # skip malformed (no timestamp)

            wallet = str(t.get("proxyWallet", "") or "")
            tx_hash = str(t.get("transactionHash", "") or "")
            trades.append(
                RawTrade(
                    trade_id=tx_hash or str(t.get("id", "")),
                    token_id=asset or (yes_token_id or ""),
                    price=float(t.get("price", 0)),
                    size=float(t.get("size", 0)),
                    side=str(t.get("side", "BUY")).upper(),
                    timestamp=ts,
                    maker_address=wallet,
                    taker_address="",  # Data API doesn't expose counterparty
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed trade record: %s — %s", t, exc)
    # newest first
    trades.sort(key=lambda x: x.timestamp, reverse=True)
    return trades




def _derive_unique_traders(trades: list[RawTrade]) -> int:
    """B3: count distinct wallet addresses across maker + taker fields.
    Empty strings (missing addresses) are excluded. Returns 0 if no
    addresses are present anywhere — caller can then fall back to
    Gamma's reported value (even if known-flaky)."""
    addrs: set[str] = set()
    for t in trades:
        if t.maker_address:
            addrs.add(t.maker_address)
        if t.taker_address:
            addrs.add(t.taker_address)
    return len(addrs)


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
    2. Gamma /events?slug=  → metadata + condition_id + token_ids
    3. Data API /trades?market=<condition_id> → trade history (filtered
       client-side to the YES token)
    4. CLOB /spread?token_id= → current spread (best-effort; falls back
       to 0.0 if CLOB tightens auth on this endpoint too)
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
        # the price series and feature vectors. The Data API takes the
        # condition_id; we filter client-side to the YES token.
        trades: list[RawTrade] = []
        spread = parsed["spread"]
        condition_id = parsed["condition_id"]
        if parsed["token_ids"] and condition_id:
            yes_token = parsed["token_ids"][0]
            trades = _fetch_market_trades(
                client, condition_id, yes_token, limit=trade_limit,
            )
            spread = _fetch_clob_spread(client, yes_token) or spread

    # B3: derive unique_traders from the trade tape (real). Fall back to
    # Gamma's reported count only if no addresses surfaced — which
    # should never happen for an actively traded market.
    derived = _derive_unique_traders(trades)
    unique_traders = derived if derived > 0 else parsed["unique_traders"]

    return RawMarket(
        market_url=url,
        condition_id=parsed["condition_id"],
        question_id=parsed["question_id"],
        question=parsed["question"],
        token_ids=parsed["token_ids"],
        volume_usd=parsed["volume_usd"],
        liquidity_usd=parsed["liquidity_usd"],
        unique_traders=unique_traders,
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
