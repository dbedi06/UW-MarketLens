"""Synthetic market *streams*: M markets, each with W consecutive windows.

The IID `clean_windows` generator in `features.py` samples from one global
distribution. Real surveillance systems compare each window to its own
market's recent history (a niche market and a blue chip have very different
baselines). To approximate that synthetically, we generate heterogeneous
markets — each with its own per-market volume / volatility / trader scale —
so a "z-score vs this market's trailing K windows" feature becomes
meaningful (something real systems lean on heavily).

`clean_streams(n_markets, w_per_market, seed)` returns a triple:
    X_base        (N, 5) base feature matrix, N = M*W
    market_id     (N,)   integer market index
    window_index  (N,)   position 0..W-1 inside that market's history
Rows are grouped by market then ordered by window_index ascending.
"""

from __future__ import annotations
import numpy as np

from .features import BASE_FEATURE_NAMES  # 5 base columns; order matters
from .network import NETWORK_FEATURE_NAMES  # 4 network columns


def _market_params(rng: np.random.Generator) -> dict:
    """Sample per-market baseline scales. Spread of these is what creates
    the cross-market heterogeneity that justifies per-market relativization."""
    return {
        "mean_log_volume": rng.normal(loc=np.log(2500.0), scale=0.7),
        "vol_sigma": rng.uniform(0.5, 1.0),
        "spread_loc": rng.lognormal(mean=np.log(0.012), sigma=0.35),
        "trader_scale": rng.uniform(0.6, 1.6),
        "volatility_scale": rng.uniform(0.012, 0.04),
        "end_date_days": rng.uniform(1.0, 180.0),
    }


def _market_windows(p: dict, w: int, rng: np.random.Generator) -> np.ndarray:
    """Generate `w` clean windows for a single market with params `p`.
    Same 5-column shape as `clean_windows`, but each market has its own
    centers and scales so the global pool is heterogeneous."""
    volume = np.exp(rng.normal(loc=p["mean_log_volume"], scale=p["vol_sigma"], size=w))

    spread = rng.lognormal(mean=np.log(p["spread_loc"]), sigma=0.35, size=w)
    spread = np.clip(spread, 1e-4, 0.25)

    # Trader count scaled by market size, with sub-linear coupling to volume.
    base_traders = (
        6.0
        + 2.0 * (np.log(volume) - p["mean_log_volume"])
    ) * p["trader_scale"]
    unique_traders = rng.poisson(np.clip(base_traders, 1.0, None)).astype(float)

    price_volatility = np.abs(rng.normal(loc=0.0, scale=p["volatility_scale"], size=w))

    # Time-to-resolution decreases monotonically within a market's window
    # sequence (chronological), then small jitter so it isn't perfectly
    # monotonic across simulated trading windows.
    ttr_start = p["end_date_days"]
    ttr = np.linspace(ttr_start, max(1.0, ttr_start - w * 0.25), w)
    ttr = np.clip(ttr + rng.normal(0.0, 0.5, size=w), 1.0, None)

    return np.column_stack([volume, spread, unique_traders, price_volatility, ttr])


def clean_streams(
    n_markets: int, w_per_market: int, *, seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate (X_base, market_id, window_index) for M markets x W windows.
    Deterministic in seed."""
    rng = np.random.default_rng(seed)
    blocks: list[np.ndarray] = []
    market_ids: list[np.ndarray] = []
    window_idxs: list[np.ndarray] = []
    for m in range(n_markets):
        p = _market_params(rng)
        mkt_rng = np.random.default_rng(int(rng.integers(0, 2**31 - 1)))
        X = _market_windows(p, w_per_market, mkt_rng)
        blocks.append(X)
        market_ids.append(np.full(w_per_market, m, dtype=np.int64))
        window_idxs.append(np.arange(w_per_market, dtype=np.int64))
    return (
        np.vstack(blocks),
        np.concatenate(market_ids),
        np.concatenate(window_idxs),
    )


assert len(BASE_FEATURE_NAMES) == 5, "feature contract drift"


# --------------------------------------------------------------------------
# Synthetic *network* features (Phase A — pushing toward honest 6/10).
# --------------------------------------------------------------------------
# Honest caveat: parameter ranges below are a MODELING CHOICE. We have no
# measurement of the true population of trader-graph statistics on
# Polymarket; the labeled eval is the cross-check. If real markets exhibit
# very different distributions (especially HHI), the model's relative
# z-features survive but absolute network columns may miscalibrate.

def _network_market_params(rng: np.random.Generator) -> dict:
    """Per-market plausible baselines for the four NETWORK_FEATURE_NAMES."""
    return {
        "wallet_pool": int(rng.integers(10, 200)),
        # Beta(2,8) ≈ mean 0.2, right-skewed — typical of permissionless markets
        # where a few wallets dominate volume.
        "hhi_alpha": 2.0, "hhi_beta": 8.0,
        # Beta(2,15) ≈ mean ~0.12 — repeat-counterparty is normally rare.
        "rcp_alpha": 2.0, "rcp_beta": 15.0,
        # LCC ratio relative to wallet pool, U(0.3, 0.9). Most active wallets
        # are connected via some chain of counterparties; this is the slack.
        "lcc_ratio_lo": 0.3, "lcc_ratio_hi": 0.9,
    }


def _network_market_windows(p: dict, w: int,
                            rng: np.random.Generator) -> np.ndarray:
    """Generate `w` clean network feature rows for one market with params
    `p`. Order matches `NETWORK_FEATURE_NAMES`:
        net_unique_wallets, net_top_trader_hhi,
        net_repeat_counterparty, net_largest_component.
    """
    pool = p["wallet_pool"]
    # Per-window active wallet count fluctuates around a per-market base.
    base_active = max(2.0, pool * 0.3)
    unique_w = np.clip(
        rng.poisson(lam=base_active, size=w).astype(float),
        2.0, float(pool),
    )
    hhi = rng.beta(p["hhi_alpha"], p["hhi_beta"], size=w)
    rcp = rng.beta(p["rcp_alpha"], p["rcp_beta"], size=w)
    lcc_ratio = rng.uniform(p["lcc_ratio_lo"], p["lcc_ratio_hi"], size=w)
    lcc = np.clip(unique_w * lcc_ratio, 1.0, None)
    return np.column_stack([unique_w, hhi, rcp, lcc])


def clean_streams_with_network(
    n_markets: int, w_per_market: int, *, seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Like `clean_streams`, but also emits per-window network features.

    Returns `(X_base, X_net, market_id, window_index)`. The same per-market
    rng draws both base and network blocks so re-running with the same
    seed produces identical output. Heterogeneous per market: each
    market gets its own wallet-pool size and HHI/RCP/LCC scales.
    """
    rng = np.random.default_rng(seed)
    base_blocks: list[np.ndarray] = []
    net_blocks: list[np.ndarray] = []
    market_ids: list[np.ndarray] = []
    window_idxs: list[np.ndarray] = []
    for m in range(n_markets):
        bp = _market_params(rng)
        np_p = _network_market_params(rng)
        mkt_seed = int(rng.integers(0, 2**31 - 1))
        mkt_rng = np.random.default_rng(mkt_seed)
        net_rng = np.random.default_rng(mkt_seed ^ 0xA5A5A5)
        Xb = _market_windows(bp, w_per_market, mkt_rng)
        Xn = _network_market_windows(np_p, w_per_market, net_rng)
        base_blocks.append(Xb)
        net_blocks.append(Xn)
        market_ids.append(np.full(w_per_market, m, dtype=np.int64))
        window_idxs.append(np.arange(w_per_market, dtype=np.int64))
    return (
        np.vstack(base_blocks),
        np.vstack(net_blocks),
        np.concatenate(market_ids),
        np.concatenate(window_idxs),
    )


assert len(NETWORK_FEATURE_NAMES) == 4, "network contract drift"
