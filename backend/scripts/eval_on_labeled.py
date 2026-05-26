"""Evaluate the S3 detector against the pre-registered labeled cases.

Today (pre-S1) the script is in scaffold mode: there is no real
detector that can score a Polymarket market URL, so we report the
shape — number of cases, class balance, pairwise Cohen's κ — without
faking model scores. Once S1 lands and a scorer is plugged in via
`--scorer <module:fn>`, the script will produce real per-case scores,
AUC, and recall at the operating-point grid.

Usage:
    python -m scripts.eval_on_labeled                 # shape report
    python -m scripts.eval_on_labeled --dry-run       # alias
    python -m scripts.eval_on_labeled --scorer pkg.mod:score_market_url
"""

from __future__ import annotations
import argparse
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.anomaly.labeled import (  # noqa: E402
    DEFAULT_CASES_PATH, class_balance, load_cases, pairwise_kappa,
)


def _resolve_scorer(spec: str | None):
    """Return a callable taking a market_url and returning a float score
    (higher = more anomalous), or None if no scorer requested."""
    if not spec:
        return None
    mod_name, fn_name = spec.split(":", 1)
    mod = importlib.import_module(mod_name)
    return getattr(mod, fn_name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    ap.add_argument("--scorer", default=None,
                    help="dotted spec 'pkg.module:fn' returning a float "
                         "anomaly score given a market_url (post-S1).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Equivalent to omitting --scorer.")
    args = ap.parse_args()

    cases = load_cases(args.cases)
    print(f"UW MarketLens -- S3 labeled-cases evaluation")
    print("=" * 64)
    print(f"  cases file       : {args.cases}")
    print(f"  total cases      : {len(cases)}")
    balance = class_balance(cases)
    print(f"  class balance    : controversial={balance['controversial']}  "
          f"mundane={balance['mundane']}")

    pair_stats = pairwise_kappa(cases)
    if not pair_stats:
        print(f"  inter-rater      : no labeler pair shares >= 2 cases")
    else:
        print(f"  inter-rater (Cohen's kappa, percentile bootstrap 95% CI):")
        for s in pair_stats:
            print(f"    {s['labeler_a']:>8s} vs {s['labeler_b']:<8s}"
                  f"  n={s['n_shared']:3d}  kappa={s['kappa']:+.3f}  "
                  f"CI[{s['ci_low']:+.3f}, {s['ci_high']:+.3f}]")

    scorer = _resolve_scorer(args.scorer) if not args.dry_run else None
    if scorer is None:
        if len(cases) == 0:
            print("\n  No cases yet -- add rows to labeled_cases.yaml per the "
                  "rubric, then re-run.")
        print("\n  No --scorer provided: skipping per-case scoring. Plug a "
              "scorer in once S1 / S7 wiring lands; this script's contract "
              "stays the same.")
        out_path = ROOT / "app" / "anomaly" / "last_labeled_eval.json"
        out_path.write_text(json.dumps({
            "schema_version": 1,
            "n_cases": len(cases),
            "class_balance": balance,
            "pairwise_kappa": pair_stats,
            "framing": (
                "Scaffold mode (no scorer). The real per-case AUC/recall "
                "report becomes possible once a Polymarket-URL -> score "
                "function is provided via --scorer."
            ),
        }, indent=2), encoding="utf-8")
        print(f"  wrote {out_path.relative_to(ROOT.parent)}")
        return 0

    # Real scoring path (post-S1)
    rows = []
    for c in cases:
        try:
            score = float(scorer(c.market_url))
        except Exception as e:
            print(f"  ! scorer failed for {c.market_url}: {e}")
            continue
        rows.append({"market_url": c.market_url, "label": c.label,
                     "score": score})
    print(f"\n  scored {len(rows)}/{len(cases)} cases via {args.scorer}")
    # Mean-score-by-label diagnostic; AUC computed only if both classes
    # represented (sklearn would crash otherwise).
    by_label: dict[str, list[float]] = {"controversial": [], "mundane": []}
    for r in rows:
        by_label[r["label"]].append(r["score"])
    for lab, vals in by_label.items():
        if vals:
            import statistics as _s
            print(f"    {lab:>14s}: n={len(vals)}  mean_score="
                  f"{_s.mean(vals):.3f}  median={_s.median(vals):.3f}")
    auc_payload: dict = {}
    low_n = len(rows) < 20
    if by_label["controversial"] and by_label["mundane"]:
        import numpy as np
        from sklearn.metrics import roc_auc_score
        y_true = np.array([1] * len(by_label["controversial"])
                          + [0] * len(by_label["mundane"]))
        y_score = np.array(by_label["controversial"]
                           + by_label["mundane"])
        auc = float(roc_auc_score(y_true, y_score))
        # Percentile bootstrap CI — honest small-N reporting.
        rng = np.random.default_rng(0)
        n = y_true.shape[0]
        boots = np.empty(1000)
        idx = np.arange(n)
        for i in range(1000):
            sel = rng.choice(idx, size=n, replace=True)
            try:
                boots[i] = roc_auc_score(y_true[sel], y_score[sel])
            except ValueError:
                boots[i] = np.nan
        boots = boots[~np.isnan(boots)]
        if boots.size:
            ci_low = float(np.quantile(boots, 0.025))
            ci_high = float(np.quantile(boots, 0.975))
        else:
            ci_low = ci_high = float("nan")
        print(f"    ROC-AUC          : {auc:.3f}"
              f"  CI[{ci_low:.3f}, {ci_high:.3f}]  (n={n})")
        if low_n:
            print("    !! low-N warning: n<20 means the CI is wide and the "
                  "point estimate is volatile. Treat as directional.")
        auc_payload = {
            "auc": auc, "auc_ci_low": ci_low, "auc_ci_high": ci_high,
        }

    out_path = ROOT / "app" / "anomaly" / "last_labeled_eval.json"
    out_path.write_text(json.dumps({
        "schema_version": 1,
        "scorer": args.scorer,
        "n_cases": len(cases),
        "n_scored": len(rows),
        "low_n_warning": low_n,
        "class_balance": balance,
        "pairwise_kappa": pair_stats,
        **auc_payload,
        "rows": rows,
    }, indent=2), encoding="utf-8")
    print(f"\n  wrote {out_path.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
