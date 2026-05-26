"""Synthetic per-window feature vectors + the engineered features the model
actually sees.

The 5 base features mirror proposal §2.1; the 3 engineered features below
exist because vanilla IsolationForest partitions on raw axes and cannot
natively form ratios. The wash-trade pattern is precisely a ratio anomaly
(volume up, unique-traders flat) so we expose `vol_per_trader` etc. as
first-class columns. This is what the real S2 feature engineering would
build anyway — we're materializing S2's contract, not cheating.

`feature_matrix(rows)` is the single construction path used by training,
scoring, and tests so the model and the tests never drift apart.

Column order:
    0 volume                  USD volume in the window
    1 bid_ask_spread          average spread, probability units
    2 unique_traders          distinct trader count
    3 price_volatility        std-dev of implied probability ticks
    4 time_to_resolution      days remaining until resolve
    5 log_volume              log1p of volume (heavy-tail flattener)
    6 vol_per_trader          log1p(volume / max(traders, 1))
    7 spread_x_vol            bid_ask_spread * sqrt(volume)
    8 traders_per_logvol      unique_traders / log1p(volume)
"""

from __future__ import annotations
import numpy as np


BASE_FEATURE_NAMES = (
    "volume",
    "bid_ask_spread",
    "unique_traders",
    "price_volatility",
    "time_to_resolution",
)

ENGINEERED_FEATURE_NAMES = (
    "log_volume",
    "vol_per_trader",
    "spread_x_vol",
    "traders_per_logvol",
    # Microstructure additions (A2). Pre-S1 these use price_volatility as
    # a |return| proxy and spread/volume as the illiquidity input; once
    # S1 lands and we have real trade-tape data, swap the inputs to true
    # per-window |return| and bid-ask spread via `features.from_trades`.
    "amihud_proxy",        # |return-proxy| / log1p(volume) — illiquidity
    "spread_per_logvol",   # bid_ask_spread / log1p(volume) — tightness
)

# Per-market rolling z-scores (against this market's own trailing windows).
# Real surveillance systems compare each window to *its own market's*
# baseline; these features are the synthetic analog.
RELATIVE_FEATURE_NAMES = (
    "vol_z_rel",
    "volatility_z_rel",
    "vol_per_trader_z_rel",
    "spread_z_rel",
)

FEATURE_NAMES = BASE_FEATURE_NAMES + ENGINEERED_FEATURE_NAMES
FULL_FEATURE_NAMES = FEATURE_NAMES + RELATIVE_FEATURE_NAMES

# Network columns from app.anomaly.network — appended after the relative
# features to give a single source-of-truth column order for the wider
# matrix used by the live route + labeled scorer.
from .network import NETWORK_FEATURE_NAMES  # noqa: E402

FULL_FEATURE_NAMES_WITH_NETWORK = FULL_FEATURE_NAMES + NETWORK_FEATURE_NAMES


def clean_windows(n: int, *, seed: int) -> np.ndarray:
    """Generate `n` clean *base* feature rows. Deterministic for a given
    seed; pure (no I/O, no globals). Engineering happens in
    `feature_matrix`."""
    rng = np.random.default_rng(seed)

    volume = rng.lognormal(mean=np.log(2500.0), sigma=0.85, size=n)

    bid_ask_spread = rng.lognormal(mean=np.log(0.012), sigma=0.45, size=n)
    bid_ask_spread = np.clip(bid_ask_spread, 1e-4, 0.25)

    base = 6.0 + 2.0 * (np.log(volume) - np.log(2500.0))
    unique_traders = rng.poisson(np.clip(base, 1.0, None)).astype(float)

    price_volatility = np.abs(rng.normal(loc=0.0, scale=0.022, size=n))

    time_to_resolution = rng.uniform(low=1.0, high=180.0, size=n)

    return np.column_stack([
        volume, bid_ask_spread, unique_traders,
        price_volatility, time_to_resolution,
    ])


def feature_matrix(X_base: np.ndarray) -> np.ndarray:
    """Add the engineered columns. Pure; same shape policy every caller
    uses, so model and tests can't drift."""
    if X_base.ndim != 2 or X_base.shape[1] != len(BASE_FEATURE_NAMES):
        raise ValueError(
            f"expected (N, {len(BASE_FEATURE_NAMES)}) base matrix, "
            f"got {X_base.shape}"
        )
    vol = X_base[:, 0]
    spread = X_base[:, 1]
    traders = np.maximum(X_base[:, 2], 1.0)

    log_volume = np.log1p(vol)
    vol_per_trader = np.log1p(vol / traders)
    spread_x_vol = spread * np.sqrt(vol)
    traders_per_logvol = traders / np.log1p(vol)

    # Microstructure features (A2). Defined to be scale-stable: divide
    # by log1p(volume) rather than volume directly so heavy-tailed
    # volume doesn't pin the feature to ~0.
    amihud_proxy = X_base[:, 3] / (log_volume + 1e-9)            # |ret|/lnV
    spread_per_logvol = X_base[:, 1] / (log_volume + 1e-9)       # spread/lnV

    return np.column_stack([
        X_base,
        log_volume, vol_per_trader, spread_x_vol, traders_per_logvol,
        amihud_proxy, spread_per_logvol,
    ])


def _rolling_z(values: np.ndarray, history: int, min_n: int = 3,
               sd_floor: float = 1e-6) -> np.ndarray:
    """Trailing-window z-score for a 1D series (per-market, called per block).
    Position i uses values[max(0, i-history) : i] (exclusive of i).

    Returns 0 in two cases:
      * fewer than `min_n` prior values (insufficient baseline), and
      * the prior is effectively constant (sd < sd_floor). The previous
        version divided by eps and produced garbage z ≈ 1e9 (bug B2)."""
    n = values.shape[0]
    out = np.zeros(n, dtype=float)
    for i in range(n):
        lo = max(0, i - history)
        prior = values[lo:i]
        if prior.size < min_n:
            continue
        mu = float(prior.mean())
        sd = float(prior.std(ddof=0))
        if sd < sd_floor:
            continue  # constant baseline -> "no signal"
        out[i] = (values[i] - mu) / sd
    return out


# --------------------------------------------------------------------------
# S1 integration point (Phase B). Today this is a documented placeholder —
# `from_trades(...)` will accept the trade-tape rows Dilshan's S1 produces
# and emit the same (N, 5) base feature matrix our model already expects.
# Defined here (not built) so callers can see the contract.
# --------------------------------------------------------------------------

def _market_id_hash(market_url: str) -> int:
    """Stable 31-bit int market id derived from a Polymarket URL. Used
    so synthetic and real markets share the same int-id space in the
    streams pipeline. Hash is deterministic across runs (unlike Python's
    built-in `hash()` for strings under PYTHONHASHSEED)."""
    import hashlib
    h = hashlib.sha256(market_url.encode("utf-8")).hexdigest()
    return int(h[:8], 16)  # 32-bit, positive


def from_trades(market, *, window_minutes: int = 15
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build per-window base features from a real Polymarket `RawMarket`
    (S1's output) — the S1 → S2 bridge.

    Parameters
    ----------
    market : ingestion.RawMarket
        Full market record from `fetch_market(url)` including the trade
        history and metadata (end_date, etc.).
    window_minutes : int
        Width of each aggregation window. Defaults to 15 minutes
        matching the synthetic stream cadence.

    Returns
    -------
    (X_base, market_id, window_index) matching the contract of
    `clean_streams` so the existing model + relative-feature pipeline
    consumes it unchanged. Empty windows are skipped (the relative-
    feature code already handles arbitrary `window_index` sequences).

    Per-window features (mirroring BASE_FEATURE_NAMES order):
      0 volume               sum of trade sizes
      1 bid_ask_spread       (max_price - min_price) — *proxy* for
                             spread (we don't have order-book history)
      2 unique_traders       distinct addresses among maker + taker
      3 price_volatility     stddev of trade prices in the window
      4 time_to_resolution   days from window midpoint to market end
                             (falls back to 30 if end_date is None)

    Honest caveats (documented in the plan and Section E):
      - bid_ask_spread proxy: real spread needs the order book.
      - price_volatility: stddev of few trades is high-variance.
      - unique_traders misses participants with only unfilled orders.
    """
    from datetime import datetime, timedelta, timezone

    trades = list(getattr(market, "trades", []))
    if not trades:
        empty = np.zeros((0, len(BASE_FEATURE_NAMES)), dtype=float)
        return empty, np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)

    # Sort ascending by timestamp; bucket into fixed-width windows
    # aligned to the earliest trade.
    trades.sort(key=lambda t: t.timestamp)
    t0 = trades[0].timestamp
    width = timedelta(minutes=window_minutes)
    end_date = getattr(market, "end_date", None)

    buckets: dict[int, list] = {}
    for t in trades:
        idx = int((t.timestamp - t0) // width)
        buckets.setdefault(idx, []).append(t)

    rows = []
    window_indices = []
    for idx in sorted(buckets):
        window_trades = buckets[idx]
        prices = np.fromiter((t.price for t in window_trades),
                             dtype=float, count=len(window_trades))
        volume = float(sum(t.size for t in window_trades))
        bid_ask_spread = float(prices.max() - prices.min()) if prices.size > 1 \
            else 0.0
        # stddev: 0 for a single-trade window (not NaN)
        price_volatility = float(prices.std(ddof=0))
        addrs: set[str] = set()
        for t in window_trades:
            if t.maker_address:
                addrs.add(t.maker_address)
            if t.taker_address:
                addrs.add(t.taker_address)
        unique_traders = float(len(addrs)) if addrs else float(len(window_trades))

        midpoint = t0 + width * idx + width / 2
        if end_date is not None:
            # Make sure both sides are TZ-aware for the subtraction.
            try:
                ttr_days = max(0.0,
                               (end_date - midpoint).total_seconds() / 86400.0)
            except TypeError:
                # naive vs aware mismatch; coerce midpoint to UTC
                midpoint_aware = midpoint.replace(tzinfo=timezone.utc) \
                    if midpoint.tzinfo is None else midpoint
                ttr_days = max(0.0,
                               (end_date - midpoint_aware).total_seconds() / 86400.0)
        else:
            ttr_days = 30.0  # honest default; documented in plan
            import logging
            logging.getLogger(__name__).warning(
                "from_trades: market has no end_date, defaulting "
                "time_to_resolution to 30 days for %s",
                getattr(market, "market_url", "<unknown>"))

        rows.append([volume, bid_ask_spread, unique_traders,
                     price_volatility, ttr_days])
        window_indices.append(idx)

    X_base = np.array(rows, dtype=float)
    n = X_base.shape[0]
    mid = np.full(n, _market_id_hash(getattr(market, "market_url", "live")),
                  dtype=np.int64)
    widx = np.asarray(window_indices, dtype=np.int64)
    return X_base, mid, widx


def feature_matrix_streams(
    X_base: np.ndarray,
    market_id: np.ndarray,
    window_index: np.ndarray,
    *,
    history: int = 20,
) -> np.ndarray:
    """Full feature matrix for *stream* data: base + engineered +
    per-market rolling z-scores. Rows MAY arrive unsorted; we reorder
    internally and put results back in the original row order."""
    if X_base.shape[0] != market_id.shape[0] or X_base.shape[0] != window_index.shape[0]:
        raise ValueError("X_base, market_id, window_index must have matching N")

    eng = feature_matrix(X_base)  # (N, 9)
    vol = X_base[:, 0]
    spread = X_base[:, 1]
    traders = np.maximum(X_base[:, 2], 1.0)
    volatility = X_base[:, 3]
    vol_per_trader_raw = np.log1p(vol / traders)

    n = X_base.shape[0]
    rel = np.zeros((n, len(RELATIVE_FEATURE_NAMES)), dtype=float)

    # Iterate per market: gather indices, sort by window_index, compute
    # rolling z, scatter back. O(sum(W_m^2)) which is fine for our sizes.
    for m in np.unique(market_id):
        rows = np.where(market_id == m)[0]
        order = rows[np.argsort(window_index[rows])]
        block_vol = vol[order]
        block_pv = volatility[order]
        block_vpt = vol_per_trader_raw[order]
        block_sp = spread[order]

        z_vol = _rolling_z(block_vol, history)
        z_pv = _rolling_z(block_pv, history)
        z_vpt = _rolling_z(block_vpt, history)
        z_sp = _rolling_z(block_sp, history)

        rel[order, 0] = z_vol
        rel[order, 1] = z_pv
        rel[order, 2] = z_vpt
        rel[order, 3] = z_sp

    return np.column_stack([eng, rel])


def feature_matrix_streams_with_network(
    X_base: np.ndarray,
    X_net: np.ndarray,
    market_id: np.ndarray,
    window_index: np.ndarray,
    *,
    history: int = 20,
) -> np.ndarray:
    """`feature_matrix_streams` extended with the 4 network columns.

    Column order matches `FULL_FEATURE_NAMES_WITH_NETWORK`. The function
    is the single shared source-of-truth: synthetic training (via
    `clean_streams_with_network`) and live scoring (via
    `from_trades_with_network`) both go through here so the matrix the
    detector trains on always matches the matrix it scores.
    """
    if X_net.shape != (X_base.shape[0], len(NETWORK_FEATURE_NAMES)):
        raise ValueError(
            f"X_net shape mismatch: expected "
            f"({X_base.shape[0]}, {len(NETWORK_FEATURE_NAMES)}), "
            f"got {X_net.shape}"
        )
    F = feature_matrix_streams(X_base, market_id, window_index, history=history)
    return np.column_stack([F, X_net])


def from_trades_with_network(
    market, *, window_minutes: int = 15,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """S1 → S2 bridge including network features.

    Returns `(X_base, X_net, market_id, window_index)`. The base block
    is computed by `from_trades`; the network block is computed by
    `network_features_for_market` over the same window boundaries.

    Honest fallback: if no trade has wallet addresses (e.g., the API
    response is anonymized), `X_net` is returned as NaN — the caller
    can drop the rows, impute, or fall back to the base-only detector.
    We do not fabricate.
    """
    from datetime import timedelta
    from .network import network_features_for_market, nan_network_features
    from .network.trader_graph import Trade as NetTrade

    X_base, mid, widx = from_trades(market, window_minutes=window_minutes)
    n = X_base.shape[0]

    trades = list(getattr(market, "trades", []))
    have_addrs = any((t.maker_address or t.taker_address) for t in trades)
    if n == 0 or not have_addrs:
        return X_base, nan_network_features(n), mid, widx

    # Align window boundaries with from_trades: t0 = earliest trade, fixed
    # width, indexed by widx (which is sparse — only populated windows).
    trades_sorted = sorted(trades, key=lambda t: t.timestamp)
    t0 = trades_sorted[0].timestamp
    width_s = window_minutes * 60
    t0_ts = int(t0.timestamp())

    net_trades = [
        NetTrade(
            timestamp=int(t.timestamp.timestamp()),
            market_id=str(getattr(market, "condition_id", "live")),
            maker=t.maker_address or "",
            taker=t.taker_address or "",
            size=float(t.size),
        )
        for t in trades_sorted
        if (t.maker_address or t.taker_address)
    ]
    window_starts = [t0_ts + int(wi) * width_s for wi in widx.tolist()]
    X_net = network_features_for_market(net_trades, window_starts, width_s)
    return X_base, X_net, mid, widx
