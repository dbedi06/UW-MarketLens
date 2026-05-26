"""End-to-end synthetic eval — v3, stream-aware.

The v2 path (IID `run`, `run_multi`) is kept for backward-compatibility and
fast tests. The primary path is now `run_streams` / `run_streams_multi`,
which:

- generates *heterogeneous market streams* (M markets x W windows each),
- splits markets disjointly into train / val / test (no leakage),
- builds per-market relative features (real-system analog),
- adds a `coordinated_manip` pattern that lives across consecutive
  windows of one market (the pattern simple z-scores cannot win on),
- reports recall at an **operating-point grid** of FPRs
  ({0.5%, 1%, 5%, 20%}),
- reports **Precision @ K** (analyst-queue metric),
- reports ROC-AUC + PR-AUC per pattern,
- compares against both **global** and **per-market-relative** baselines.

Honesty per Section D: still synthetic. Stream features get us closer to
how real surveillance systems work but cannot replace labeled real data.
"""

from __future__ import annotations
import math
from typing import Any, Dict, Iterable, List
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from . import FEATURE_NAMES, FULL_FEATURE_NAMES
from .features import (
    clean_windows,
    feature_matrix,
    feature_matrix_streams,
)
from .streams import clean_streams
from .injector import (
    INJECTORS,
    SEVERITIES,
    inject_coordinated_manip,
)
from .model import IsoForestDetector
from .baselines import all_baselines, all_stream_baselines


# --------------------------------------------------------------------------
# Confidence intervals
# --------------------------------------------------------------------------

def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    lo = 0.0 if k == 0 else max(0.0, center - half)
    hi = 1.0 if k == n else min(1.0, center + half)
    return p, lo, hi


def bootstrap_ci(values: list[float], *, n_boot: int = 2000,
                 seed: int = 0) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    means = rng.choice(arr, size=(n_boot, arr.size), replace=True).mean(axis=1)
    return float(arr.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


# --------------------------------------------------------------------------
# v2 path (IID) — kept for back-compat, tests, fast iteration
# --------------------------------------------------------------------------

def _per_pattern_recall_iid(detector, *, threshold: float, use_engineered: bool,
                            n_inj: int, seed_stream: np.random.Generator
                            ) -> Dict[str, Dict[str, Dict[str, Any]]]:
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for pat, fn in INJECTORS.items():
        out[pat] = {}
        for sev in SEVERITIES:
            clean_base = clean_windows(
                n_inj, seed=int(seed_stream.integers(0, 2**31 - 1)))
            rng_inj = np.random.default_rng(int(seed_stream.integers(0, 2**31 - 1)))
            X_inj_base = fn(clean_base, rng_inj, sev)
            X_inj = feature_matrix(X_inj_base) if use_engineered else X_inj_base
            s = detector.score(X_inj)
            tp = int((s >= threshold).sum())
            p, lo, hi = wilson_ci(tp, n_inj)
            out[pat][sev] = {"n": n_inj, "true_positives": tp,
                             "recall": p, "ci_low": lo, "ci_high": hi}
    return out


def _auc_per_pattern_iid(detector, *, X_clean_test: np.ndarray,
                         use_engineered: bool, n_inj: int,
                         seed_stream: np.random.Generator
                         ) -> Dict[str, Dict[str, float]]:
    aucs: Dict[str, Dict[str, float]] = {}
    clean_scores = detector.score(X_clean_test)
    for pat, fn in INJECTORS.items():
        clean_base = clean_windows(n_inj, seed=int(seed_stream.integers(0, 2**31 - 1)))
        rng_inj = np.random.default_rng(int(seed_stream.integers(0, 2**31 - 1)))
        X_inj_base = fn(clean_base, rng_inj, "typical")
        X_inj = feature_matrix(X_inj_base) if use_engineered else X_inj_base
        inj_scores = detector.score(X_inj)
        y_true = np.concatenate([np.zeros(len(clean_scores)), np.ones(len(inj_scores))])
        y_score = np.concatenate([clean_scores, inj_scores])
        aucs[pat] = {"roc_auc": float(roc_auc_score(y_true, y_score)),
                     "pr_auc": float(average_precision_score(y_true, y_score))}
    return aucs


def run(
    *, seed: int = 0,
    n_train_clean: int = 2000, n_val_clean: int = 1000, n_test_clean: int = 1000,
    n_inj_per_cell: int = 333, fpr_target: float = 0.20,
) -> Dict[str, Any]:
    rng_master = np.random.default_rng(seed)
    def _sub() -> int: return int(rng_master.integers(0, 2**31 - 1))

    X_train_base = clean_windows(n_train_clean, seed=_sub())
    X_val_base = clean_windows(n_val_clean, seed=_sub())
    X_test_base = clean_windows(n_test_clean, seed=_sub())
    X_train_eng = feature_matrix(X_train_base)
    X_val_eng = feature_matrix(X_val_base)
    X_test_eng = feature_matrix(X_test_base)

    model = IsoForestDetector(seed=seed).fit(X_train_eng)
    thr_m = model.pick_threshold(X_val_eng, fpr_target=fpr_target)
    fp_m = int((model.score(X_test_eng) >= thr_m).sum())
    fpr_m = wilson_ci(fp_m, n_test_clean)
    per_pat = _per_pattern_recall_iid(
        model, threshold=thr_m, use_engineered=True, n_inj=n_inj_per_cell,
        seed_stream=np.random.default_rng(_sub()))
    auc_m = _auc_per_pattern_iid(
        model, X_clean_test=X_test_eng, use_engineered=True,
        n_inj=n_inj_per_cell, seed_stream=np.random.default_rng(_sub()))

    baselines_out: Dict[str, Dict[str, Any]] = {}
    for det in all_baselines():
        det.fit(X_train_base)
        thr_b = det.pick_threshold(X_val_base, fpr_target=fpr_target)
        fp_b = int((det.score(X_test_base) >= thr_b).sum())
        per_pat_b = _per_pattern_recall_iid(
            det, threshold=thr_b, use_engineered=False, n_inj=n_inj_per_cell,
            seed_stream=np.random.default_rng(_sub()))
        auc_b = _auc_per_pattern_iid(
            det, X_clean_test=X_test_base, use_engineered=False,
            n_inj=n_inj_per_cell, seed_stream=np.random.default_rng(_sub()))
        fpr_b = wilson_ci(fp_b, n_test_clean)
        baselines_out[det.name] = {
            "threshold": thr_b,
            "realized_fpr": {"false_positives": fp_b, "n": n_test_clean,
                             "rate": fpr_b[0], "ci_low": fpr_b[1], "ci_high": fpr_b[2]},
            "per_pattern_by_severity": per_pat_b,
            "auc": auc_b,
        }

    return {
        "schema_version": 2, "seed": seed,
        "feature_names": list(FEATURE_NAMES),
        "model": {
            "name": "IsolationForest(n_estimators=200,contamination=0.05) + RobustScaler",
            "threshold": thr_m,
            "realized_fpr": {"false_positives": fp_m, "n": n_test_clean,
                             "rate": fpr_m[0], "ci_low": fpr_m[1], "ci_high": fpr_m[2]},
            "per_pattern_by_severity": per_pat,
            "auc": auc_m,
        },
        "baselines": baselines_out,
        "dataset": {
            "n_train_clean": n_train_clean, "n_val_clean": n_val_clean,
            "n_test_clean": n_test_clean, "n_inj_per_cell": n_inj_per_cell,
            "severities": list(SEVERITIES),
        },
        "fpr_target": fpr_target,
        "framing": ("Synthetic-only evaluation. Reported as a lower-bound "
                    "capability check, not a real-world manipulation-detection benchmark."),
    }


# --------------------------------------------------------------------------
# v3 path (streams) — primary
# --------------------------------------------------------------------------

DEFAULT_FPR_TARGETS = (0.005, 0.01, 0.05, 0.20)
DEFAULT_K_VALUES = (10, 50, 100)


def _sample_curve(xs: np.ndarray, ys: np.ndarray, n_points: int = 50
                  ) -> list[dict]:
    """Subsample a curve to <= n_points (uniform along x) for JSON size."""
    if xs.size <= n_points:
        idx = np.arange(xs.size)
    else:
        idx = np.linspace(0, xs.size - 1, n_points).astype(int)
    return [{"x": float(xs[i]), "y": float(ys[i])} for i in idx]


def _split_streams(streams: tuple[np.ndarray, np.ndarray, np.ndarray],
                   markets: np.ndarray):
    X, mid, widx = streams
    mask = np.isin(mid, markets)
    return X[mask], mid[mask], widx[mask]


def _operating_points(scores_clean: np.ndarray, scores_pos: np.ndarray,
                      fpr_targets: Iterable[float]
                      ) -> Dict[str, Dict[str, Any]]:
    """For each FPR target, pick threshold on `scores_clean` (assumes those
    rows ARE the clean reference) and compute recall on `scores_pos`."""
    out: Dict[str, Dict[str, Any]] = {}
    n_c = scores_clean.size
    n_p = scores_pos.size
    for f in fpr_targets:
        thr = float(np.quantile(scores_clean, 1.0 - f))
        fp = int((scores_clean >= thr).sum())
        tp = int((scores_pos >= thr).sum())
        f_p, f_lo, f_hi = wilson_ci(fp, n_c)
        r_p, r_lo, r_hi = wilson_ci(tp, n_p)
        out[f"fpr={f:.3f}"] = {
            "threshold": thr,
            "realized_fpr": {"rate": f_p, "ci_low": f_lo, "ci_high": f_hi, "n": n_c},
            "recall": {"rate": r_p, "ci_low": r_lo, "ci_high": r_hi, "n": n_p},
        }
    return out


def _precision_at_k(scores_clean: np.ndarray, scores_pos: np.ndarray,
                    ks: Iterable[int]) -> Dict[str, float | None]:
    y_true = np.concatenate([np.zeros(scores_clean.size), np.ones(scores_pos.size)])
    y_score = np.concatenate([scores_clean, scores_pos])
    order = np.argsort(-y_score)
    out: Dict[str, float | None] = {}
    n = y_score.size
    for k in ks:
        out[f"k={k}"] = float(y_true[order[:k]].mean()) if k <= n else None
    return out


def _curves(scores_clean: np.ndarray, scores_pos: np.ndarray
            ) -> Dict[str, list[dict]]:
    y_true = np.concatenate([np.zeros(scores_clean.size), np.ones(scores_pos.size)])
    y_score = np.concatenate([scores_clean, scores_pos])
    fpr, tpr, _ = roc_curve(y_true, y_score)
    prec, rec, _ = precision_recall_curve(y_true, y_score)
    return {
        "roc": _sample_curve(fpr, tpr),
        "pr": _sample_curve(rec, prec),
    }


def _row_inject(test_streams, pat: str, sev: str,
                rng: np.random.Generator
                ) -> tuple[np.ndarray, np.ndarray]:
    """Apply a row-level INJECTOR pattern to every test row, return
    (perturbed base, labels-all-True). We perturb every row so the labeled
    pool is large; clean reference is the unperturbed copy."""
    X, _, _ = test_streams
    X_inj = INJECTORS[pat](X, rng, sev)
    return X_inj, np.ones(X_inj.shape[0], dtype=bool)


def _coord_inject(test_streams, sev: str, rng: np.random.Generator,
                  n_episodes: int) -> tuple[np.ndarray, np.ndarray]:
    return inject_coordinated_manip(*test_streams, rng,
                                    n_episodes=n_episodes, severity=sev)


def _generate_injection_pools(
    test_clean, *, seed: int, n_coord_episodes: int
) -> Dict[tuple[str, str], tuple[np.ndarray, np.ndarray]]:
    """Pre-generate the full {(pattern, severity) -> (X_inj_base, labels)}
    dictionary so every detector evaluates on the SAME injected data
    (paired comparison, no order dependence). Each (pat, sev) gets its own
    deterministic sub-seed so adding a new pattern later doesn't shift the
    randomness of existing ones (fairness bug B1 + order-dependence O1)."""
    pools: Dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
    seed_rng = np.random.default_rng(seed ^ 0xC0FFEE)
    for pat in list(INJECTORS) + ["coordinated_manip"]:
        for sev in SEVERITIES:
            sub_seed = int(seed_rng.integers(0, 2**31 - 1))
            sub_rng = np.random.default_rng(sub_seed)
            if pat == "coordinated_manip":
                pools[(pat, sev)] = _coord_inject(
                    test_clean, sev, sub_rng, n_episodes=n_coord_episodes)
            else:
                pools[(pat, sev)] = _row_inject(test_clean, pat, sev, sub_rng)
    return pools


DetectorMode = str  # one of "eng_streams" | "base_global" | "relative_streams"


def _detector_branch(detector, *, train, val, test_clean, pools,
                     mode: DetectorMode, fpr_targets, k_values,
                     ) -> Dict[str, Any]:
    """Run one detector through the full operating-point + Precision@K +
    AUC pipeline using the *pre-generated* `pools` dict (fairness B1).
    `mode` chooses the feature space the detector consumes."""
    if mode == "eng_streams":
        detector.fit(feature_matrix_streams(*train))
        sc_clean = detector.score(feature_matrix_streams(*test_clean))
    elif mode == "base_global":
        detector.fit(train[0])
        sc_clean = detector.score(test_clean[0])
    elif mode == "relative_streams":
        detector.fit(test_clean)
        sc_clean = detector.score(test_clean)
    else:
        raise ValueError(f"unknown mode {mode!r}")

    per_pat: Dict[str, Dict[str, Any]] = {}
    for pat in list(INJECTORS) + ["coordinated_manip"]:
        per_pat[pat] = {}
        for sev in SEVERITIES:
            X_inj_base, labels = pools[(pat, sev)]
            if mode == "eng_streams":
                sc_inj_all = detector.score(
                    feature_matrix_streams(X_inj_base, test_clean[1], test_clean[2]))
            elif mode == "base_global":
                sc_inj_all = detector.score(X_inj_base)
            else:
                sc_inj_all = detector.score(
                    (X_inj_base, test_clean[1], test_clean[2]))
            sc_pos = sc_inj_all[labels]
            if sc_pos.size == 0:
                per_pat[pat][sev] = {"n_positive": 0, "operating_points": {},
                                     "precision_at_k": {}, "auc": None,
                                     "curves": None}
                continue
            y_true = np.concatenate([np.zeros(sc_clean.size), np.ones(sc_pos.size)])
            y_score = np.concatenate([sc_clean, sc_pos])
            per_pat[pat][sev] = {
                "n_positive": int(sc_pos.size),
                "operating_points": _operating_points(sc_clean, sc_pos, fpr_targets),
                "precision_at_k": _precision_at_k(sc_clean, sc_pos, k_values),
                "auc": {
                    "roc_auc": float(roc_auc_score(y_true, y_score)),
                    "pr_auc": float(average_precision_score(y_true, y_score)),
                },
                # O3: only store curves for typical severity (the rest were
                # already None; explicit None keeps the JSON small).
                "curves": _curves(sc_clean, sc_pos) if sev == "typical" else None,
            }
    return {"name": detector.name, "per_pattern_by_severity": per_pat}


def run_streams(
    *, seed: int = 0,
    n_markets: int = 120, w_per_market: int = 40,
    train_market_frac: float = 0.5, val_market_frac: float = 0.2,
    fpr_targets: Iterable[float] = DEFAULT_FPR_TARGETS,
    k_values: Iterable[int] = DEFAULT_K_VALUES,
    n_coord_episodes: int | None = None,
) -> Dict[str, Any]:
    fpr_targets = tuple(fpr_targets)
    k_values = tuple(k_values)
    rng = np.random.default_rng(seed)

    X_all, mid_all, widx_all = clean_streams(
        n_markets, w_per_market, seed=int(rng.integers(0, 2**31 - 1)))
    markets = np.unique(mid_all)
    rng.shuffle(markets)
    n_train_m = max(1, int(round(train_market_frac * n_markets)))
    n_val_m = max(1, int(round(val_market_frac * n_markets)))
    train_ms = markets[:n_train_m]
    val_ms = markets[n_train_m:n_train_m + n_val_m]
    test_ms = markets[n_train_m + n_val_m:]

    train = _split_streams((X_all, mid_all, widx_all), train_ms)
    val = _split_streams((X_all, mid_all, widx_all), val_ms)
    test_clean = _split_streams((X_all, mid_all, widx_all), test_ms)

    if n_coord_episodes is None:
        n_coord_episodes = max(8, test_clean[0].shape[0] // 40)

    # B1: pre-generate the SAME injection pools for every detector to make
    # the comparison paired. Each (pat, sev) gets its own deterministic
    # sub-seed (O1) so adding a pattern later doesn't shift the others.
    pools = _generate_injection_pools(
        test_clean, seed=seed, n_coord_episodes=n_coord_episodes)

    model = IsoForestDetector(seed=seed)
    model_branch = _detector_branch(
        model, train=train, val=val, test_clean=test_clean, pools=pools,
        mode="eng_streams", fpr_targets=fpr_targets, k_values=k_values,
    )

    baselines_out: Dict[str, Any] = {}
    for det in all_baselines():
        baselines_out[det.name] = _detector_branch(
            det, train=train, val=val, test_clean=test_clean, pools=pools,
            mode="base_global", fpr_targets=fpr_targets, k_values=k_values,
        )
    for det in all_stream_baselines():
        baselines_out[det.name] = _detector_branch(
            det, train=train, val=val, test_clean=test_clean, pools=pools,
            mode="relative_streams", fpr_targets=fpr_targets, k_values=k_values,
        )

    return {
        "schema_version": 3,
        "seed": seed,
        "feature_names": list(FULL_FEATURE_NAMES),
        "model_name": "IsolationForest(n=200,contamination=0.05) + RobustScaler on stream-engineered features",
        "split": {
            "n_train_markets": int(n_train_m),
            "n_val_markets": int(n_val_m),
            "n_test_markets": int(test_ms.size),
            "w_per_market": int(w_per_market),
            "n_test_rows": int(test_clean[0].shape[0]),
        },
        "fpr_targets": list(fpr_targets),
        "k_values": list(k_values),
        "patterns": list(INJECTORS) + ["coordinated_manip"],
        "severities": list(SEVERITIES),
        "model": model_branch,
        "baselines": baselines_out,
        "framing": ("Synthetic stream evaluation with disjoint train/val/test "
                    "markets, per-market relative features, and a stream-level "
                    "coordinated_manip pattern. Still synthetic: no real "
                    "labeled cases, no order-book features, no network/wallet "
                    "features. Reviewer-grade interpretation per Section D."),
    }


def run_streams_multi(
    *, seeds: Iterable[int] = range(5),
    **kw,
) -> Dict[str, Any]:
    seeds_list = list(seeds)
    per_seed = [run_streams(seed=s, **kw) for s in seeds_list]

    # Aggregate AUC per pattern across seeds (typical severity) for model
    # and each baseline; aggregate recall at each FPR target similarly.
    def _agg(branch_key: str, sub: str | None = None) -> Dict[str, Any]:
        agg: Dict[str, Any] = {}
        for pat in per_seed[0]["model"]["per_pattern_by_severity"]:
            agg[pat] = {}
            for sev in per_seed[0]["severities"]:
                rocs: list[float] = []
                ops: Dict[str, list[float]] = {}
                paks: Dict[str, list[float]] = {}
                for r in per_seed:
                    node = r["model"] if branch_key == "model" else r["baselines"][sub]
                    cell = node["per_pattern_by_severity"][pat][sev]
                    if cell.get("auc") is not None:
                        rocs.append(cell["auc"]["roc_auc"])
                    for k, v in cell["operating_points"].items():
                        ops.setdefault(k, []).append(v["recall"]["rate"])
                    for k, v in cell["precision_at_k"].items():
                        if v is not None:
                            paks.setdefault(k, []).append(float(v))
                agg[pat][sev] = {
                    "roc_auc": _stat(rocs),
                    "recall_at_fpr": {k: _stat(vs) for k, vs in ops.items()},
                    "precision_at_k": {k: _stat(vs) for k, vs in paks.items()},
                    "n_seeds": len(per_seed),
                }
        return agg

    baseline_names = list(per_seed[0]["baselines"].keys())
    return {
        "schema_version": 3,
        "seeds": seeds_list,
        "feature_names": per_seed[0]["feature_names"],
        "patterns": per_seed[0]["patterns"],
        "severities": per_seed[0]["severities"],
        "fpr_targets": per_seed[0]["fpr_targets"],
        "k_values": per_seed[0]["k_values"],
        "per_seed": per_seed,
        "aggregate": {
            "model": _agg("model"),
            "baselines": {n: _agg("baselines", n) for n in baseline_names},
        },
        "framing": per_seed[0]["framing"],
    }


def drift_smoke_test(*, seed: int = 0, n_markets: int = 80,
                     w_per_market: int = 30,
                     volume_shift_mult: float = 1.30,
                     vol_sigma_mult: float = 1.50) -> Dict[str, Any]:
    """Train on a baseline market distribution; eval recall/AUC on a
    *shifted* distribution (more volume, fatter volatility tails).
    Reports the AUC delta — a smoke check for concept-drift sensitivity.
    Does not claim to *fix* drift; demonstrates we measure it."""
    rng = np.random.default_rng(seed)
    X_base, mid, widx = clean_streams(
        n_markets, w_per_market, seed=int(rng.integers(0, 2**31 - 1)))
    X_train = feature_matrix_streams(X_base, mid, widx)
    detector = IsoForestDetector(seed=seed).fit(X_train)

    # Score baseline test pool + injected
    X_base_test, mid_t, widx_t = clean_streams(
        n_markets, w_per_market, seed=int(rng.integers(0, 2**31 - 1)))
    inj_rng = np.random.default_rng(int(rng.integers(0, 2**31 - 1)))
    X_inj = INJECTORS["volume_spike"](X_base_test, inj_rng, "typical")

    def _auc_for(X_clean_base, X_inj_base):
        Xc = feature_matrix_streams(X_clean_base, mid_t, widx_t)
        Xi = feature_matrix_streams(X_inj_base, mid_t, widx_t)
        sc = np.concatenate([detector.score(Xc), detector.score(Xi)])
        y = np.concatenate([np.zeros(Xc.shape[0]), np.ones(Xi.shape[0])])
        return float(roc_auc_score(y, sc))

    auc_baseline = _auc_for(X_base_test, X_inj)

    # Shifted distribution: multiply volume + fatten volatility.
    X_shifted = X_base_test.copy()
    X_shifted[:, 0] *= volume_shift_mult
    X_shifted[:, 3] *= vol_sigma_mult
    X_inj_shifted = INJECTORS["volume_spike"](X_shifted, inj_rng, "typical")
    auc_shifted = _auc_for(X_shifted, X_inj_shifted)

    return {
        "seed": seed,
        "shift": {"volume_mult": volume_shift_mult,
                  "vol_sigma_mult": vol_sigma_mult},
        "auc_baseline": auc_baseline,
        "auc_shifted": auc_shifted,
        "delta_auc": auc_shifted - auc_baseline,
        "note": (
            "Synthetic drift smoke check. Demonstrates we measure "
            "concept-drift sensitivity; we do not claim to correct it. "
            "Real systems retrain on rolling windows + monitor "
            "PSI/KS divergence per feature."
        ),
    }


def _stat(values: list[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
    mean, lo, hi = bootstrap_ci(values)
    return {
        "mean": mean,
        "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "ci_low": lo, "ci_high": hi, "n": len(values),
    }


# --------------------------------------------------------------------------
# v2 multi-seed aggregator (kept)
# --------------------------------------------------------------------------

def _collect_recalls(per_seed: List[Dict[str, Any]], *, branch: str,
                     sub: str | None = None
                     ) -> Dict[str, Dict[str, List[float]]]:
    out: Dict[str, Dict[str, List[float]]] = {}
    for r in per_seed:
        node = r["model"] if branch == "model" else r["baselines"][sub]
        for pat, by_sev in node["per_pattern_by_severity"].items():
            out.setdefault(pat, {})
            for sev, m in by_sev.items():
                out[pat].setdefault(sev, []).append(float(m["recall"]))
    return out


def _aggregate(per_seed: List[Dict[str, Any]], *, branch: str,
               sub: str | None = None) -> Dict[str, Any]:
    raw = _collect_recalls(per_seed, branch=branch, sub=sub)
    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for pat, sev_map in raw.items():
        out[pat] = {}
        for sev, vals in sev_map.items():
            mean, lo, hi = bootstrap_ci(vals)
            out[pat][sev] = {
                "mean": mean,
                "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
                "ci_low": lo, "ci_high": hi, "n_seeds": len(vals),
            }
    fprs = [float((r["model"] if branch == "model"
                   else r["baselines"][sub])["realized_fpr"]["rate"])
            for r in per_seed]
    f_mean, f_lo, f_hi = bootstrap_ci(fprs)
    return {
        "per_pattern_by_severity": out,
        "realized_fpr_across_seeds": {
            "mean": f_mean, "ci_low": f_lo, "ci_high": f_hi,
            "n_seeds": len(fprs)},
    }


def run_multi(
    *, seeds: Iterable[int] = range(10),
    n_train_clean: int = 2000, n_val_clean: int = 1000,
    n_test_clean: int = 1000, n_inj_per_cell: int = 333,
    fpr_target: float = 0.20,
) -> Dict[str, Any]:
    seeds_list = list(seeds)
    per_seed = [run(seed=s, n_train_clean=n_train_clean, n_val_clean=n_val_clean,
                    n_test_clean=n_test_clean, n_inj_per_cell=n_inj_per_cell,
                    fpr_target=fpr_target) for s in seeds_list]
    baseline_names = list(per_seed[0]["baselines"].keys())
    return {
        "schema_version": 2,
        "feature_names": per_seed[0]["feature_names"],
        "fpr_target": fpr_target,
        "dataset": per_seed[0]["dataset"],
        "seeds": seeds_list,
        "per_seed": per_seed,
        "aggregate": {
            "model": _aggregate(per_seed, branch="model"),
            "baselines": {name: _aggregate(per_seed, branch="baselines", sub=name)
                          for name in baseline_names},
        },
        "framing": per_seed[0]["framing"],
    }
