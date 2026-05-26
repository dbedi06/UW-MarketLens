"""Per-market-window network feature vectors.

Given a list of `Trade` records (from the Polygon client or, post-S1,
from real ingestion), bucket them into windows that match the
existing per-window feature contract and emit one feature row per
window. The features are designed to be **additive** to the existing
streams pipeline: you can `np.column_stack([feature_matrix_streams(...),
network_features_for_market(...)])` and the model trains on the union.

Honest scope: when the trade data is missing (RPC unavailable, no
cache, S1 not landed) the builder returns NaN rows. The model can be
trained either with these dropped (the common case today) or with
imputation (a Phase B decision once we have real data flow). We do not
silently fabricate.
"""

from __future__ import annotations
from typing import Iterable

import numpy as np

from .trader_graph import (
    Trade, TraderGraph, build_trader_graph,
    largest_component_size, repeat_counterparty_ratio,
    top_trader_hhi, unique_wallets,
)


NETWORK_FEATURE_NAMES = (
    "net_unique_wallets",       # raw count
    "net_top_trader_hhi",       # 0..1; 1 = one wallet
    "net_repeat_counterparty",  # 0..1; high = wash-trade smell
    "net_largest_component",    # raw count
)


def _slice_window(trades: list[Trade], start: int, end: int) -> list[Trade]:
    """Inclusive-start, exclusive-end window slice by timestamp."""
    return [t for t in trades if start <= t.timestamp < end]


def _row_from_graph(g: TraderGraph) -> np.ndarray:
    return np.array([
        float(unique_wallets(g)),
        float(top_trader_hhi(g)),
        float(repeat_counterparty_ratio(g)),
        float(largest_component_size(g)),
    ], dtype=float)


def network_features_for_market(
    trades: Iterable[Trade],
    window_starts: list[int],
    window_size_s: int,
) -> np.ndarray:
    """Compute one feature row per window. `window_starts` is a list of
    UNIX timestamps marking window boundaries (typically per-market
    `window_index` * `window_size_s`). The function returns an array of
    shape (len(window_starts), len(NETWORK_FEATURE_NAMES))."""
    trades_list = list(trades)
    n = len(window_starts)
    out = np.zeros((n, len(NETWORK_FEATURE_NAMES)), dtype=float)
    for i, start in enumerate(window_starts):
        window = _slice_window(trades_list, start, start + window_size_s)
        if not window:
            # No trades in this window -> empty graph -> all-zero row,
            # which is honest (no signal) rather than NaN (drops the row
            # downstream). The model can learn that empty windows aren't
            # anomalous.
            continue
        g = build_trader_graph(window)
        out[i] = _row_from_graph(g)
    return out


def nan_network_features(n_rows: int) -> np.ndarray:
    """Used when on-chain data is unavailable; produces an explicit
    NaN-filled matrix the caller can drop or impute. Never fabricates."""
    return np.full((n_rows, len(NETWORK_FEATURE_NAMES)), np.nan, dtype=float)
