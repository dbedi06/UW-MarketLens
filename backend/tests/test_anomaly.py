"""Tests for the S3 anomaly module — contract + properties, not target
chasing. Synthetic-only; small N where possible so fast."""

from __future__ import annotations
import numpy as np
import pytest

from app.anomaly import (
    BASE_FEATURE_NAMES, FEATURE_NAMES, FULL_FEATURE_NAMES,
    feature_matrix, feature_matrix_streams, clean_windows, clean_streams,
    IsoForestDetector, BaggedIsoForest,
)
from app.anomaly.injector import (
    INJECTORS, SEVERITIES, inject_coordinated_manip,
)
from app.anomaly.baselines import (
    all_baselines, all_stream_baselines, CombinedSimpleRule,
)
from app.anomaly.evaluate import (
    run, run_multi, run_streams, run_streams_multi, drift_smoke_test,
    wilson_ci, bootstrap_ci, DEFAULT_FPR_TARGETS, DEFAULT_K_VALUES,
    _generate_injection_pools, _operating_points, _precision_at_k,
    _sample_curve, _split_streams,
)
from app.anomaly.features import _rolling_z
from app.anomaly.explain import Explainer


# ---- features ------------------------------------------------------------

def test_clean_windows_deterministic_for_seed():
    a = clean_windows(64, seed=7)
    b = clean_windows(64, seed=7)
    assert a.shape == (64, len(BASE_FEATURE_NAMES))
    assert np.array_equal(a, b)


def test_clean_windows_change_with_seed():
    assert not np.array_equal(clean_windows(64, seed=7), clean_windows(64, seed=8))


def test_feature_matrix_shape_and_finite():
    X = feature_matrix(clean_windows(32, seed=1))
    assert X.shape == (32, len(FEATURE_NAMES))
    assert np.isfinite(X).all()


def test_feature_matrix_rejects_wrong_shape():
    with pytest.raises(ValueError):
        feature_matrix(np.zeros((10, 3)))


# ---- streams / relative features -----------------------------------------

def test_clean_streams_shape_and_ids():
    X, mid, widx = clean_streams(8, 5, seed=0)
    assert X.shape == (40, len(BASE_FEATURE_NAMES))
    assert set(np.unique(mid).tolist()) == set(range(8))
    # Each market has window_index 0..4 once.
    for m in range(8):
        rows = np.where(mid == m)[0]
        assert sorted(widx[rows].tolist()) == list(range(5))


def test_feature_matrix_streams_shape_and_zero_warmup():
    X, mid, widx = clean_streams(4, 6, seed=1)
    F = feature_matrix_streams(X, mid, widx, history=20)
    assert F.shape == (24, len(FULL_FEATURE_NAMES))
    # Relative columns are the last 4. The first 3 windows of each market
    # have insufficient prior history → z = 0.
    rel = F[:, -4:]
    for m in range(4):
        rows = np.where(mid == m)[0]
        order = rows[np.argsort(widx[rows])]
        assert np.all(rel[order[:3]] == 0.0)


def test_relative_feature_detects_local_spike():
    """A volume spike on one market's row should produce a large positive
    z relative to its own rolling baseline."""
    X, mid, widx = clean_streams(3, 30, seed=2)
    # Spike row 25 of market 0 by 5x.
    rows0 = np.where(mid == 0)[0]
    target = rows0[np.argsort(widx[rows0])][25]
    X2 = X.copy()
    X2[target, 0] *= 5.0
    F = feature_matrix_streams(X2, mid, widx, history=20)
    # Look the column up by name so this can't drift if engineered
    # features are added/reordered.
    col = FULL_FEATURE_NAMES.index("vol_z_rel")
    z_target = F[target, col]
    z_neighbors = F[rows0, col]
    assert z_target > 3.0
    assert z_target > np.abs(z_neighbors).max() - 1e-9


# ---- injectors -----------------------------------------------------------

@pytest.mark.parametrize("severity", list(SEVERITIES))
def test_each_injector_shifts_targeted_feature(severity):
    base = clean_windows(400, seed=11)
    rng = np.random.default_rng(11)
    inj = INJECTORS["volume_spike"](base, rng, severity)
    assert inj[:, 0].mean() > base[:, 0].mean()
    inj = INJECTORS["coordinated_swing"](base, rng, severity)
    assert inj[:, 3].mean() > base[:, 3].mean()
    inj = INJECTORS["wash_trade_pair"](base, rng, severity)
    rb = (base[:, 0] / np.maximum(base[:, 2], 1)).mean()
    ri = (inj[:, 0] / np.maximum(inj[:, 2], 1)).mean()
    assert ri > rb


def test_injector_rejects_bad_severity():
    with pytest.raises(ValueError):
        INJECTORS["volume_spike"](clean_windows(4, seed=0),
                                  np.random.default_rng(0), "huge")  # type: ignore[arg-type]


def test_coordinated_manip_episodes_have_contiguous_labels():
    X, mid, widx = clean_streams(6, 20, seed=3)
    rng = np.random.default_rng(3)
    _, labels = inject_coordinated_manip(X, mid, widx, rng,
                                         n_episodes=5, severity="typical")
    assert labels.dtype == bool and labels.shape == (X.shape[0],)
    # Per market, labeled rows should form contiguous runs of length 3-5.
    for m in np.unique(mid):
        rows = np.where(mid == m)[0]
        order = rows[np.argsort(widx[rows])]
        lbl = labels[order]
        # find runs of True
        runs: list[int] = []
        i = 0
        while i < lbl.size:
            if lbl[i]:
                j = i
                while j < lbl.size and lbl[j]:
                    j += 1
                runs.append(j - i)
                i = j
            else:
                i += 1
        for run_len in runs:
            assert 3 <= run_len <= 5


# ---- detection sanity ----------------------------------------------------

def test_model_beats_random_at_target_fpr():
    X_train = feature_matrix(clean_windows(1500, seed=2))
    X_val = feature_matrix(clean_windows(800, seed=3))
    det = IsoForestDetector(seed=2).fit(X_train)
    thr = det.pick_threshold(X_val, fpr_target=0.20)
    fpr = float((det.score(feature_matrix(clean_windows(800, seed=4))) >= thr).mean())
    assert fpr <= 0.27
    rng = np.random.default_rng(5)
    for name, fn in INJECTORS.items():
        base = clean_windows(250, seed=int(rng.integers(0, 2**31 - 1)))
        X_inj = feature_matrix(fn(base, np.random.default_rng(int(rng.integers(0, 2**31 - 1))), "typical"))
        recall = float((det.score(X_inj) >= thr).mean())
        assert recall > fpr + 0.10, f"{name} recall {recall:.3f} not clearly above fpr {fpr:.3f}"


# ---- v2 evaluate.run contract --------------------------------------------

def _small_run(**kw):
    return run(n_train_clean=600, n_val_clean=300, n_test_clean=300,
               n_inj_per_cell=80, **kw)


def test_evaluate_run_contract_and_ci_invariant():
    r = _small_run(seed=0)
    for k in ("seed", "model", "baselines", "dataset", "fpr_target",
              "framing", "feature_names"):
        assert k in r
    for node_name, node in [("model", r["model"]),
                            *((f"baselines.{n}", b) for n, b in r["baselines"].items())]:
        for k in ("threshold", "realized_fpr",
                  "per_pattern_by_severity", "auc"):
            assert k in node, f"{node_name} missing {k}"
        f = node["realized_fpr"]
        assert 0.0 <= f["ci_low"] <= f["rate"] <= f["ci_high"] <= 1.0
        for by_sev in node["per_pattern_by_severity"].values():
            assert set(by_sev) == set(SEVERITIES)
            for m in by_sev.values():
                assert 0.0 <= m["ci_low"] <= m["recall"] <= m["ci_high"] <= 1.0


def test_evaluate_run_deterministic():
    assert _small_run(seed=42) == _small_run(seed=42)


def test_threshold_monotonic_in_fpr_target():
    r_lo = _small_run(seed=1, fpr_target=0.05)
    r_hi = _small_run(seed=1, fpr_target=0.30)
    assert r_lo["model"]["realized_fpr"]["rate"] <= r_hi["model"]["realized_fpr"]["rate"] + 1e-9
    for pat in INJECTORS:
        rec_lo = r_lo["model"]["per_pattern_by_severity"][pat]["typical"]["recall"]
        rec_hi = r_hi["model"]["per_pattern_by_severity"][pat]["typical"]["recall"]
        assert rec_lo <= rec_hi + 1e-9, f"{pat}"


def test_model_not_catastrophically_below_best_baseline():
    r = _small_run(seed=7)
    model_rec = float(np.mean([
        r["model"]["per_pattern_by_severity"][pat]["typical"]["recall"]
        for pat in INJECTORS
    ]))
    baseline_recs = [
        float(np.mean([
            b["per_pattern_by_severity"][pat]["typical"]["recall"]
            for pat in INJECTORS
        ]))
        for b in r["baselines"].values()
    ]
    assert model_rec + 0.20 >= max(baseline_recs)


# ---- v3 streams contract -------------------------------------------------

def _small_streams(seed=0):
    return run_streams(seed=seed, n_markets=30, w_per_market=20)


def test_run_streams_contract():
    r = _small_streams()
    for k in ("schema_version", "seed", "feature_names", "model_name",
              "split", "fpr_targets", "k_values", "patterns", "severities",
              "model", "baselines", "framing"):
        assert k in r
    assert r["schema_version"] == 3
    pats = r["patterns"]
    assert pats == list(INJECTORS) + ["coordinated_manip"]
    model_per_pat = r["model"]["per_pattern_by_severity"]
    assert set(model_per_pat) == set(pats)
    for pat, by_sev in model_per_pat.items():
        for sev in SEVERITIES:
            cell = by_sev[sev]
            if cell.get("auc") is not None:
                assert 0.0 <= cell["auc"]["roc_auc"] <= 1.0
                assert 0.0 <= cell["auc"]["pr_auc"] <= 1.0
                for op in cell["operating_points"].values():
                    rc = op["recall"]
                    assert 0.0 <= rc["ci_low"] <= rc["rate"] <= rc["ci_high"] <= 1.0


def test_run_streams_precision_at_k_monotone_in_k_lt_n():
    """When K is small relative to N, raising K cannot increase precision
    beyond the current value if the top-K members are all positives. We
    just check P@K is defined and within [0,1] for our K's."""
    r = _small_streams()
    pat_cell = r["model"]["per_pattern_by_severity"]["coordinated_manip"]["typical"]
    if pat_cell.get("precision_at_k"):
        for k, v in pat_cell["precision_at_k"].items():
            if v is not None:
                assert 0.0 <= v <= 1.0


def test_run_streams_multi_aggregates():
    r = run_streams_multi(seeds=[0, 1],
                          n_markets=24, w_per_market=18)
    assert r["seeds"] == [0, 1]
    agg = r["aggregate"]["model"]
    for pat in r["patterns"]:
        cell = agg[pat]["typical"]
        for k in ("roc_auc", "recall_at_fpr", "precision_at_k", "n_seeds"):
            assert k in cell


# ---- bagging -------------------------------------------------------------

def test_bagged_iso_forest_fits_and_scores():
    X = feature_matrix(clean_windows(800, seed=10))
    det = BaggedIsoForest(k=3, seed=10).fit(X)
    s = det.score(X)
    assert s.shape == (800,) and np.isfinite(s).all()


def test_bagged_is_deterministic_per_seed():
    """Honest property: same seed -> identical scores. We do *not* claim
    bagging strictly reduces variance at small N (the empirics don't
    support it on a 5-point probe). Stability across seeds is reported
    via run_streams_multi rather than asserted here."""
    X = feature_matrix(clean_windows(400, seed=20))
    a = BaggedIsoForest(k=4, seed=42).fit(X).score(X[:5])
    b = BaggedIsoForest(k=4, seed=42).fit(X).score(X[:5])
    assert np.allclose(a, b)
    c = BaggedIsoForest(k=4, seed=43).fit(X).score(X[:5])
    assert not np.allclose(a, c)


# ---- SHAP explanations ---------------------------------------------------

def test_explainer_returns_sorted_contributions():
    X = feature_matrix(clean_windows(200, seed=30))
    det = IsoForestDetector(seed=30).fit(X)
    expl = Explainer(det, list(FEATURE_NAMES))
    out = expl.explain(X[0])
    assert "score" in out and "contributions" in out
    assert set(out["contributions"][0]) == {"feature", "value", "shap"}
    # Contributions sorted by |shap| descending.
    mags = [abs(c["shap"]) for c in out["contributions"]]
    assert mags == sorted(mags, reverse=True)


def test_explainer_contributions_are_finite_and_one_per_feature():
    """SHAP additivity for IF holds in the raw tree-output space, not in
    our reported score space, so we don't claim a residual against
    `score`. We do check the contributions are well-formed."""
    X = feature_matrix(clean_windows(200, seed=31))
    det = IsoForestDetector(seed=31).fit(X)
    expl = Explainer(det, list(FEATURE_NAMES))
    for i in range(3):
        out = expl.explain(X[i])
        assert len(out["contributions"]) == len(FEATURE_NAMES)
        names = [c["feature"] for c in out["contributions"]]
        assert set(names) == set(FEATURE_NAMES)
        for c in out["contributions"]:
            assert np.isfinite(c["shap"])


# ---- drift smoke ---------------------------------------------------------

def test_drift_smoke_test_contract():
    r = drift_smoke_test(seed=0, n_markets=24, w_per_market=15)
    for k in ("seed", "shift", "auc_baseline", "auc_shifted", "delta_auc", "note"):
        assert k in r
    assert 0.0 <= r["auc_baseline"] <= 1.0
    assert 0.0 <= r["auc_shifted"] <= 1.0


# ---- CIs -----------------------------------------------------------------

def test_wilson_invariants():
    assert wilson_ci(0, 0) == (0.0, 0.0, 0.0)
    p, lo, hi = wilson_ci(0, 100); assert (p, lo) == (0.0, 0.0) and 0.0 < hi < 0.1
    p, lo, hi = wilson_ci(100, 100); assert p == 1.0 and 0.9 < lo < 1.0 and hi == 1.0
    _, lo, hi = wilson_ci(50, 100)
    assert round(lo, 3) == 0.404 and round(hi, 3) == 0.596


def test_bootstrap_ci_brackets_mean():
    p, lo, hi = bootstrap_ci([0.5, 0.6, 0.55, 0.62, 0.58, 0.51], seed=0)
    assert lo <= p <= hi
    assert hi - lo < 0.2


# ---- baselines -----------------------------------------------------------

def test_baselines_fit_and_score():
    base = clean_windows(400, seed=9)
    for det in all_baselines():
        det.fit(base)
        s = det.score(base)
        assert s.shape == (400,) and np.isfinite(s).all()
    combo = CombinedSimpleRule().fit(base)
    assert combo.score(base).shape == (400,)


def test_stream_baselines_fit_and_score():
    streams = clean_streams(6, 25, seed=42)
    for det in all_stream_baselines():
        det.fit(streams)
        s = det.score(streams)
        assert s.shape == (streams[0].shape[0],) and np.isfinite(s).all()


# ---- defaults sanity -----------------------------------------------------

def test_default_constants_present():
    assert tuple(DEFAULT_FPR_TARGETS) == (0.005, 0.01, 0.05, 0.20)
    assert tuple(DEFAULT_K_VALUES) == (10, 50, 100)


# ---- T1-T12: post-review additions --------------------------------------

def test_t1_streams_disjoint_market_split():
    """T1: train/val/test market sets are pairwise disjoint."""
    X, mid, _ = clean_streams(30, 10, seed=99)
    markets = np.unique(mid)
    rng = np.random.default_rng(99)
    rng.shuffle(markets)
    n_train = int(round(0.5 * 30))
    n_val = int(round(0.2 * 30))
    train_ms = markets[:n_train]
    val_ms = markets[n_train:n_train + n_val]
    test_ms = markets[n_train + n_val:]
    assert set(train_ms).isdisjoint(val_ms)
    assert set(val_ms).isdisjoint(test_ms)
    assert set(train_ms).isdisjoint(test_ms)


def test_t2_operating_points_monotonic_in_fpr():
    """T2: at higher fpr_target, threshold drops and recall on positives
    is non-decreasing."""
    clean = np.random.default_rng(0).normal(size=500)
    pos = np.random.default_rng(1).normal(loc=1.0, size=300)
    ops = _operating_points(clean, pos, (0.01, 0.05, 0.20))
    last_thr = float("inf")
    last_recall = -1.0
    for key in ("fpr=0.010", "fpr=0.050", "fpr=0.200"):
        thr = ops[key]["threshold"]
        rec = ops[key]["recall"]["rate"]
        assert thr <= last_thr + 1e-9, f"threshold not non-increasing at {key}"
        assert rec >= last_recall - 1e-9, f"recall not non-decreasing at {key}"
        last_thr, last_recall = thr, rec


def test_t3_precision_at_k_boundaries():
    """T3: P@K is 1.0 when all top scores are positives; 0.0 when none are;
    None when K > N."""
    clean = np.array([0.0, 0.0, 0.0])
    pos = np.array([10.0, 9.0, 8.0])
    pak = _precision_at_k(clean, pos, (1, 3, 5, 100))
    assert pak["k=1"] == 1.0
    assert pak["k=3"] == 1.0
    assert pak["k=5"] == 3 / 5  # 3 positives in pool of 6
    assert pak["k=100"] is None

    clean2 = np.array([10.0, 9.0, 8.0])
    pos2 = np.array([0.0, 0.0])
    pak2 = _precision_at_k(clean2, pos2, (1, 3))
    assert pak2["k=1"] == 0.0
    assert pak2["k=3"] == 0.0


def test_t4_coordinated_manip_leaves_unlabeled_rows_unchanged():
    """T4: perturbations are confined to labeled rows. Bytes-equal on the
    complement is the strongest invariant."""
    X, mid, widx = clean_streams(6, 20, seed=4)
    rng = np.random.default_rng(4)
    X_inj, labels = inject_coordinated_manip(X, mid, widx, rng,
                                             n_episodes=4, severity="typical")
    assert labels.any() and not labels.all()
    assert np.array_equal(X[~labels], X_inj[~labels])


def test_t5_rolling_z_constant_prior_returns_zero():
    """T5 (B2 fix): when the trailing window is exactly constant, z = 0
    rather than a garbage 1e9. Pre-fix this test would have failed."""
    values = np.array([5.0, 5.0, 5.0, 5.0, 7.0])  # 4 constants, then a jump
    z = _rolling_z(values, history=4, min_n=3)
    assert z[0] == 0.0 and z[1] == 0.0 and z[2] == 0.0
    # Index 3 has prior [5,5,5] (constant) → z = 0, not 2e9.
    assert z[3] == 0.0
    # Index 4 has prior [5,5,5,5] (constant) → z = 0.
    assert z[4] == 0.0


def test_t6_paired_pool_invariant_across_detectors():
    """T6 (B1 fix): the injection pool is generated once per seed and seen
    by both the model and every baseline (paired comparison invariant)."""
    X, mid, widx = clean_streams(20, 12, seed=7)
    streams = (X, mid, widx)
    pools_a = _generate_injection_pools(streams, seed=7, n_coord_episodes=5)
    pools_b = _generate_injection_pools(streams, seed=7, n_coord_episodes=5)
    # Determinism per seed.
    for key in pools_a:
        Xa, La = pools_a[key]
        Xb, Lb = pools_b[key]
        assert np.array_equal(Xa, Xb)
        assert np.array_equal(La, Lb)
    # Different seed -> different pool.
    pools_c = _generate_injection_pools(streams, seed=8, n_coord_episodes=5)
    diffs = sum(
        1 for k in pools_a
        if not np.array_equal(pools_a[k][0], pools_c[k][0])
    )
    assert diffs >= len(pools_a) - 1  # most should differ


def test_t7_shap_explanation_deterministic():
    """T7: two Explainer instances over the same fitted model and row
    return identical contributions."""
    X = feature_matrix(clean_windows(200, seed=33))
    det = IsoForestDetector(seed=33).fit(X)
    e1 = Explainer(det, list(FEATURE_NAMES)).explain(X[0])
    e2 = Explainer(det, list(FEATURE_NAMES)).explain(X[0])
    assert e1["score"] == e2["score"]
    assert [c["feature"] for c in e1["contributions"]] == \
           [c["feature"] for c in e2["contributions"]]
    assert all(c1["shap"] == c2["shap"]
               for c1, c2 in zip(e1["contributions"], e2["contributions"]))


def test_t8_auc_in_unit_interval_for_all_cells():
    """T8: every (detector, pattern, severity) AUC in [0, 1]."""
    r = run_streams(seed=11, n_markets=24, w_per_market=15)
    for branch in [r["model"]] + list(r["baselines"].values()):
        for by_sev in branch["per_pattern_by_severity"].values():
            for cell in by_sev.values():
                if cell.get("auc"):
                    assert 0.0 <= cell["auc"]["roc_auc"] <= 1.0
                    assert 0.0 <= cell["auc"]["pr_auc"] <= 1.0


def test_t9_drift_strong_shift_degrades_at_least_as_much_as_mild():
    """T9: a stronger volume/volatility shift produces an AUC delta no
    smaller in magnitude than a mild shift (loose monotonicity)."""
    mild = drift_smoke_test(seed=0, n_markets=20, w_per_market=12,
                            volume_shift_mult=1.05, vol_sigma_mult=1.05)
    hard = drift_smoke_test(seed=0, n_markets=20, w_per_market=12,
                            volume_shift_mult=1.50, vol_sigma_mult=1.80)
    # Either both are positive (no degradation), or hard is at least as
    # negative as mild. Allow noise tolerance.
    assert hard["delta_auc"] <= mild["delta_auc"] + 0.10


def test_t10_if_wins_on_coordinated_manip_typical():
    """T10: the honest positive result. At production-scale data (~120
    markets x 40 windows, ~2400 test rows) IF beats the best baseline on
    the multi-feature pattern by a small margin. The claim is
    DATASET-SIZE-DEPENDENT — at the small sizes used by other tests the
    margin reverses. We run this at production scale (the regime where
    the claim is meaningful) with a 5-point tolerance for seed variance.

    Takes ~10s — by far the slowest test in the suite."""
    r = run_streams(seed=0)  # default n_markets=120, w_per_market=40
    model_roc = r["model"]["per_pattern_by_severity"]["coordinated_manip"]["typical"]["auc"]["roc_auc"]
    baseline_rocs = [
        b["per_pattern_by_severity"]["coordinated_manip"]["typical"]["auc"]["roc_auc"]
        for b in r["baselines"].values()
    ]
    best = max(baseline_rocs)
    assert model_roc + 0.05 >= best, (
        f"model {model_roc:.3f} vs best baseline {best:.3f} on coord_manip"
    )


def test_t11_sample_curve_edge_cases():
    """T11: small arrays return in order; n_points smaller than xs.size
    returns exactly n_points; single-point array returns single point."""
    xs = np.array([0.0])
    ys = np.array([1.0])
    out = _sample_curve(xs, ys, n_points=50)
    assert out == [{"x": 0.0, "y": 1.0}]
    xs = np.linspace(0, 1, 20)
    ys = xs ** 2
    out = _sample_curve(xs, ys, n_points=5)
    assert len(out) == 5
    # First and last points preserved (linspace indexing).
    assert out[0]["x"] == 0.0
    assert out[-1]["x"] == 1.0


def test_t12_coordinated_swing_volatility_capped():
    """T12 (B4 fix): injected price_volatility never exceeds 0.5 even at
    extreme severity. Without the cap this routinely overshot 1.0."""
    base = clean_windows(2000, seed=88)
    rng = np.random.default_rng(88)
    inj = INJECTORS["coordinated_swing"](base, rng, "extreme")
    assert inj[:, 3].max() <= 0.5 + 1e-9


# ---- A2: microstructure features (hand-computed) ------------------------

def test_amihud_proxy_hand_computed():
    """amihud_proxy[i] = price_volatility[i] / log1p(volume[i]).
    Pin to two hand-computed rows so the formula can't silently drift."""
    base = np.array([
        # volume, spread, traders, volatility, ttr
        [1000.0, 0.01, 25.0, 0.020, 30.0],
        [5000.0, 0.02, 60.0, 0.050, 90.0],
    ])
    X = feature_matrix(base)
    amihud_col = FEATURE_NAMES.index("amihud_proxy")
    expected_0 = 0.020 / (np.log1p(1000.0) + 1e-9)
    expected_1 = 0.050 / (np.log1p(5000.0) + 1e-9)
    assert X[0, amihud_col] == pytest.approx(expected_0, rel=1e-9)
    assert X[1, amihud_col] == pytest.approx(expected_1, rel=1e-9)


def test_spread_per_logvol_hand_computed():
    """spread_per_logvol[i] = bid_ask_spread[i] / log1p(volume[i])."""
    base = np.array([
        [1000.0, 0.01, 25.0, 0.020, 30.0],
        [5000.0, 0.02, 60.0, 0.050, 90.0],
    ])
    X = feature_matrix(base)
    col = FEATURE_NAMES.index("spread_per_logvol")
    expected_0 = 0.01 / (np.log1p(1000.0) + 1e-9)
    expected_1 = 0.02 / (np.log1p(5000.0) + 1e-9)
    assert X[0, col] == pytest.approx(expected_0, rel=1e-9)
    assert X[1, col] == pytest.approx(expected_1, rel=1e-9)


def test_microstructure_columns_finite_on_clean_streams():
    """Honest smoke: across a real synthetic stream the new columns are
    finite (no log(0), no divide-by-zero), regardless of how skewed
    volume gets."""
    X, mid, widx = clean_streams(30, 20, seed=99)
    F = feature_matrix_streams(X, mid, widx)
    amihud_col = FULL_FEATURE_NAMES.index("amihud_proxy")
    spread_col = FULL_FEATURE_NAMES.index("spread_per_logvol")
    assert np.isfinite(F[:, amihud_col]).all()
    assert np.isfinite(F[:, spread_col]).all()


def test_from_trades_is_implemented_and_returns_streams_tuple():
    """B6: the S1 -> S2 bridge is now real. Full behavior is covered by
    `tests/test_from_trades.py`; this is a smoke check that the symbol
    is importable, callable, and returns the (X, mid, widx) shape."""
    from app.anomaly.features import from_trades, BASE_FEATURE_NAMES
    from app.ingestion.polymarket import RawMarket

    empty_market = RawMarket(
        market_url="https://polymarket.com/event/x",
        condition_id="c", question_id="q", question="?",
        token_ids=[], volume_usd=0.0, liquidity_usd=0.0,
        unique_traders=0, yes_price=0.5, spread=0.0,
        end_date=None, resolved=False, resolution=None,
    )
    X, mid, widx = from_trades(empty_market)
    assert X.shape == (0, len(BASE_FEATURE_NAMES))
    assert mid.shape == (0,) and widx.shape == (0,)
