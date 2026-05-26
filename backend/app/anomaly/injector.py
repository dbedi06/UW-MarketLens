"""Synthetic anomaly injection — the three patterns named in proposal §5.

Each injector takes a copy of clean *base* feature rows (5 columns) and
perturbs them in the shape its named anomaly would leave on pre-aggregated
window features. Pure: given a seeded `rng`, output is deterministic.

Severity parameter (`mild` / `typical` / `extreme`) scales the perturbation,
so the eval shows a meaningful gradient rather than just "extreme = obvious."
Multipliers per pattern:

  volume_spike       mild: 1.5–2.0×   typical: 2.5–4.0×   extreme: 4.0–6.0×
  coordinated_swing  mild: 2–3×       typical: 4–6×       extreme: 6–10×    (volatility)
  wash_trade_pair    mild: 1.4–1.8×   typical: 2.0–3.0×   extreme: 3.0–4.5× (volume)

Honesty: synthetic injections are by construction more detectable than
real-world manipulation. Section D frames these as a lower-bound capability
check, not a real-world benchmark.
"""

from __future__ import annotations
from typing import Callable, Dict, Literal
import numpy as np

Severity = Literal["mild", "typical", "extreme"]
SEVERITIES: tuple[Severity, ...] = ("mild", "typical", "extreme")

_V, _S, _T, _PV, _TR = 0, 1, 2, 3, 4


def _check_severity(s: str) -> None:
    if s not in SEVERITIES:
        raise ValueError(f"severity must be one of {SEVERITIES}, got {s!r}")


def volume_spike(X: np.ndarray, rng: np.random.Generator,
                 severity: Severity = "typical") -> np.ndarray:
    _check_severity(severity)
    lo, hi = {"mild": (1.5, 2.0), "typical": (2.5, 4.0),
              "extreme": (4.0, 6.0)}[severity]
    out = X.copy()
    n = out.shape[0]
    out[:, _V] *= rng.uniform(lo, hi, size=n)
    out[:, _S] *= rng.uniform(0.7, 1.0, size=n)
    # B3: drop dead np.maximum (multiplier was already >= 1.2). Allow
    # trader-count to occasionally *drop* slightly, modeling a spike
    # dominated by a few existing whales rather than fresh participation.
    out[:, _T] *= rng.uniform(0.9, 1.6, size=n)
    return out


def coordinated_swing(X: np.ndarray, rng: np.random.Generator,
                      severity: Severity = "typical") -> np.ndarray:
    _check_severity(severity)
    pv_mult = {"mild": (2.0, 3.0), "typical": (4.0, 6.0),
               "extreme": (6.0, 10.0)}[severity]
    pv_add = {"mild": (0.01, 0.03), "typical": (0.03, 0.06),
              "extreme": (0.06, 0.12)}[severity]
    sp_mult = {"mild": (1.2, 1.6), "typical": (1.8, 2.6),
               "extreme": (2.6, 3.5)}[severity]
    out = X.copy()
    n = out.shape[0]
    # B4: cap volatility at 0.5 (physical ceiling for an implied-probability
    # tick std-dev). Without this the injector can produce nonsensical
    # values that the model trivially separates.
    out[:, _PV] = np.clip(
        out[:, _PV] * rng.uniform(*pv_mult, size=n)
        + rng.uniform(*pv_add, size=n),
        0.0, 0.5,
    )
    out[:, _S] *= rng.uniform(*sp_mult, size=n)
    return out


def wash_trade_pair(X: np.ndarray, rng: np.random.Generator,
                    severity: Severity = "typical") -> np.ndarray:
    _check_severity(severity)
    v_mult = {"mild": (1.4, 1.8), "typical": (2.0, 3.0),
              "extreme": (3.0, 4.5)}[severity]
    out = X.copy()
    n = out.shape[0]
    out[:, _V] *= rng.uniform(*v_mult, size=n)
    out[:, _T] *= rng.uniform(0.85, 1.0, size=n)  # traders flat or down
    out[:, _S] *= rng.uniform(0.5, 0.8, size=n)   # fake-liquidity look
    return out


InjectorFn = Callable[[np.ndarray, np.random.Generator, Severity], np.ndarray]

INJECTORS: Dict[str, InjectorFn] = {
    "volume_spike": volume_spike,
    "coordinated_swing": coordinated_swing,
    "wash_trade_pair": wash_trade_pair,
}


# ---------- Stream-level injector: coordinated_manip ---------------------
# Lives across multiple consecutive same-market windows; perturbs
# (volatility, spread, volume/traders) jointly with realistic correlations.
# This is the pattern where a single-feature z-score cannot win, because
# any one feature shift is modest — the *combination* is the signature.

def inject_coordinated_manip(
    X_base: np.ndarray,
    market_id: np.ndarray,
    window_index: np.ndarray,
    rng: np.random.Generator,
    *,
    n_episodes: int,
    severity: Severity = "typical",
    episode_len_range: tuple[int, int] = (3, 5),
) -> tuple[np.ndarray, np.ndarray]:
    """Inject `n_episodes` coordinated bursts. Each burst spans
    episode_len consecutive windows of one randomly chosen market.
    Returns (X_perturbed_copy, labels_bool of shape (N,))."""
    _check_severity(severity)
    pv_mult = {"mild": (2.0, 3.0), "typical": (3.0, 4.5),
               "extreme": (4.5, 6.5)}[severity]
    sp_mult = {"mild": (1.3, 1.7), "typical": (1.6, 2.2),
               "extreme": (2.2, 3.0)}[severity]
    v_mult = {"mild": (1.3, 1.6), "typical": (1.5, 2.0),
              "extreme": (2.0, 2.8)}[severity]
    tr_mult = {"mild": (0.9, 1.0), "typical": (0.85, 0.95),
               "extreme": (0.75, 0.9)}[severity]

    out = X_base.copy()
    labels = np.zeros(out.shape[0], dtype=bool)

    markets = np.unique(market_id)
    # Build per-market row arrays sorted by window_index.
    per_market: dict[int, np.ndarray] = {}
    for m in markets:
        rows = np.where(market_id == m)[0]
        per_market[int(m)] = rows[np.argsort(window_index[rows])]

    placed = 0
    attempts = 0
    while placed < n_episodes and attempts < n_episodes * 20:
        attempts += 1
        m = int(rng.choice(markets))
        rows_sorted = per_market[m]
        L = int(rng.integers(episode_len_range[0], episode_len_range[1] + 1))
        if rows_sorted.size < L:
            continue
        start = int(rng.integers(0, rows_sorted.size - L + 1))
        idx = rows_sorted[start:start + L]
        if labels[idx].any():
            continue  # don't overlap existing episodes
        out[idx, 3] *= rng.uniform(*pv_mult, size=L)             # volatility
        out[idx, 1] *= rng.uniform(*sp_mult, size=L)             # spread
        out[idx, 0] *= rng.uniform(*v_mult, size=L)              # volume up
        out[idx, 2] = np.maximum(
            out[idx, 2] * rng.uniform(*tr_mult, size=L), 1.0)    # traders flat/down
        labels[idx] = True
        placed += 1
    return out, labels


STREAM_INJECTORS: Dict[str, Callable] = {
    "coordinated_manip": inject_coordinated_manip,
}


# ---------- Network-feature injector: sybil_ring -------------------------
# Perturbs ONLY the network columns; base features stay near-clean. This
# is the lift case for network-aware detectors — base-only models should
# miss it.

_NU, _NHHI, _NRCP, _NLCC = 0, 1, 2, 3  # column order in NETWORK_FEATURE_NAMES


def inject_sybil_ring(
    X_net: np.ndarray,
    market_id: np.ndarray,
    window_index: np.ndarray,
    rng: np.random.Generator,
    *,
    n_episodes: int,
    severity: Severity = "typical",
    episode_len_range: tuple[int, int] = (3, 5),
) -> tuple[np.ndarray, np.ndarray]:
    """Inject `n_episodes` sybil-ring bursts across consecutive windows of
    one market. Operates on the (N, 4) network matrix. Returns
    (X_net_perturbed, labels_bool of shape (N,)).

    Pattern signature:
      * top_trader_hhi spikes (one or two wallets dominate)
      * repeat_counterparty ratio jumps (ring trades within itself)
      * unique_wallets shrinks (small closed pool)
      * largest_component tracks unique_wallets (the ring is fully connected)
    """
    _check_severity(severity)
    hhi_target = {"mild": (0.55, 0.70), "typical": (0.70, 0.85),
                  "extreme": (0.85, 0.95)}[severity]
    rcp_target = {"mild": (0.30, 0.45), "typical": (0.45, 0.65),
                  "extreme": (0.65, 0.85)}[severity]
    uw_target = {"mild": (8, 15), "typical": (4, 9),
                 "extreme": (3, 6)}[severity]

    out = X_net.copy()
    labels = np.zeros(out.shape[0], dtype=bool)

    markets = np.unique(market_id)
    per_market: dict[int, np.ndarray] = {}
    for m in markets:
        rows = np.where(market_id == m)[0]
        per_market[int(m)] = rows[np.argsort(window_index[rows])]

    placed = 0
    attempts = 0
    while placed < n_episodes and attempts < n_episodes * 20:
        attempts += 1
        m = int(rng.choice(markets))
        rows_sorted = per_market[m]
        L = int(rng.integers(episode_len_range[0], episode_len_range[1] + 1))
        if rows_sorted.size < L:
            continue
        start = int(rng.integers(0, rows_sorted.size - L + 1))
        idx = rows_sorted[start:start + L]
        if labels[idx].any():
            continue
        # Replace (not multiply) so the burst is a clean signature
        # independent of the per-market baseline level.
        out[idx, _NHHI] = rng.uniform(*hhi_target, size=L)
        out[idx, _NRCP] = rng.uniform(*rcp_target, size=L)
        out[idx, _NU] = rng.integers(uw_target[0], uw_target[1] + 1, size=L)
        # The ring is fully connected within itself.
        out[idx, _NLCC] = out[idx, _NU]
        labels[idx] = True
        placed += 1
    return out, labels


STREAM_INJECTORS["sybil_ring"] = inject_sybil_ring
