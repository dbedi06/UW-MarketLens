"""Tests for `clean_streams_with_network` — Phase A network synth."""
from __future__ import annotations

import numpy as np
import pytest

from app.anomaly.features import (
    BASE_FEATURE_NAMES, FULL_FEATURE_NAMES_WITH_NETWORK,
    feature_matrix_streams_with_network,
)
from app.anomaly.network import NETWORK_FEATURE_NAMES
from app.anomaly.streams import clean_streams_with_network
from app.anomaly.injector import inject_sybil_ring


def test_clean_streams_with_network_shape_contract():
    Xb, Xn, mid, widx = clean_streams_with_network(8, 20, seed=1)
    assert Xb.shape == (8 * 20, len(BASE_FEATURE_NAMES))
    assert Xn.shape == (8 * 20, len(NETWORK_FEATURE_NAMES))
    assert mid.shape == (8 * 20,) and widx.shape == (8 * 20,)


def test_clean_streams_with_network_is_deterministic():
    a = clean_streams_with_network(5, 12, seed=42)
    b = clean_streams_with_network(5, 12, seed=42)
    for x, y in zip(a, b):
        assert np.array_equal(x, y)


def test_clean_streams_with_network_values_in_plausible_range():
    _, Xn, _, _ = clean_streams_with_network(20, 30, seed=3)
    # HHI in [0, 1]
    assert (Xn[:, 1] >= 0).all() and (Xn[:, 1] <= 1).all()
    # repeat-counterparty in [0, 1]
    assert (Xn[:, 2] >= 0).all() and (Xn[:, 2] <= 1).all()
    # unique wallets >= 2
    assert (Xn[:, 0] >= 2).all()
    # LCC >= 1 and <= unique wallets
    assert (Xn[:, 3] >= 1).all()
    assert (Xn[:, 3] <= Xn[:, 0] + 1e-9).all()


def test_clean_streams_with_network_heterogeneous_across_markets():
    """Per-market params draws must produce non-constant cross-market means."""
    _, Xn, mid, _ = clean_streams_with_network(30, 30, seed=11)
    per_mkt_hhi = np.array([Xn[mid == m, 1].mean() for m in np.unique(mid)])
    # If markets were identical, std would be tiny — require meaningful spread
    assert per_mkt_hhi.std() > 0.02


def test_feature_matrix_streams_with_network_column_count():
    Xb, Xn, mid, widx = clean_streams_with_network(6, 18, seed=2)
    F = feature_matrix_streams_with_network(Xb, Xn, mid, widx)
    assert F.shape == (6 * 18, len(FULL_FEATURE_NAMES_WITH_NETWORK))


def test_feature_matrix_streams_with_network_shape_mismatch_raises():
    Xb, _, mid, widx = clean_streams_with_network(4, 10, seed=2)
    bad_net = np.zeros((Xb.shape[0], 3))  # wrong width
    with pytest.raises(ValueError, match="X_net shape"):
        feature_matrix_streams_with_network(Xb, bad_net, mid, widx)


def test_sybil_ring_injection_perturbs_only_network_columns():
    Xb, Xn, mid, widx = clean_streams_with_network(20, 30, seed=4)
    rng = np.random.default_rng(0)
    Xn_perturbed, labels = inject_sybil_ring(
        Xn, mid, widx, rng, n_episodes=10, severity="typical",
    )
    assert labels.sum() >= 10  # at least 10 windows flagged (≥ 1 per episode)
    # Flagged rows should show elevated HHI
    flagged_hhi = Xn_perturbed[labels, 1]
    clean_hhi = Xn[labels, 1]
    assert flagged_hhi.mean() > clean_hhi.mean() + 0.2
    # Unflagged rows are identical to input
    assert np.array_equal(Xn_perturbed[~labels], Xn[~labels])


def test_sybil_ring_severity_ladder_orders_correctly():
    Xb, Xn, mid, widx = clean_streams_with_network(40, 30, seed=5)
    means = {}
    for sev in ("mild", "typical", "extreme"):
        rng = np.random.default_rng(0)
        Xp, lab = inject_sybil_ring(Xn, mid, widx, rng,
                                     n_episodes=20, severity=sev)
        means[sev] = Xp[lab, 1].mean()
    assert means["mild"] < means["typical"] < means["extreme"]
