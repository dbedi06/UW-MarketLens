"""Run the S3 synthetic evaluation, print a readable report, write the
artifact. ASCII-only so it survives Windows cp1252 consoles.

The streams pipeline (v3) is the default. The legacy IID pipeline (v2) is
still available via --legacy.

Usage (from backend/ with the venv active):
    python -m scripts.eval_anomaly                    # streams, 5 seeds
    python -m scripts.eval_anomaly --seeds 0          # single seed, fast
    python -m scripts.eval_anomaly --legacy           # v2 IID path
    python -m scripts.eval_anomaly --drift            # just the drift smoke test

Writes:
    backend/app/anomaly/last_eval.json
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.anomaly.evaluate import (  # noqa: E402
    run, run_multi, run_streams, run_streams_multi, drift_smoke_test,
    DEFAULT_FPR_TARGETS, DEFAULT_K_VALUES,
)
from app.anomaly.injector import SEVERITIES, INJECTORS  # noqa: E402


def _pct(x: float) -> str: return f"{x * 100:5.1f}%"


def _print_streams_single(r: dict) -> None:
    print(f"\n  MODEL  {r['model_name']}")
    _print_pattern_block(r["model"]["per_pattern_by_severity"], r["fpr_targets"], r["k_values"])
    for name, b in r["baselines"].items():
        print(f"\n  BASELINE  {name}")
        _print_pattern_block(b["per_pattern_by_severity"], r["fpr_targets"], r["k_values"])


def _print_pattern_block(per_pat: dict, fpr_targets: list[float],
                         k_values: list[int]) -> None:
    for pat, by_sev in per_pat.items():
        typical = by_sev.get("typical", {})
        if not typical or typical.get("auc") is None:
            print(f"    {pat:<22} (no positives at typical)")
            continue
        ops = typical["operating_points"]
        pak = typical["precision_at_k"]
        auc = typical["auc"]
        ops_str = "  ".join(
            f"R@{f*100:>4.1f}%={_pct(ops[f'fpr={f:.3f}']['recall']['rate'])}"
            for f in fpr_targets
        )
        pak_str = "  ".join(
            f"P@{k}={(_pct(pak[f'k={k}']) if pak[f'k={k}'] is not None else ' n/a ')}"
            for k in k_values
        )
        print(f"    {pat:<22} ROC={auc['roc_auc']:.3f} PR={auc['pr_auc']:.3f}  "
              f"{ops_str}   {pak_str}")


def _print_streams_multi(r: dict) -> None:
    seeds = r["seeds"]
    print(f"\n  Aggregated across {len(seeds)} seeds (mean +/- 95% CI)")
    for branch_name, branch in [("MODEL", r["aggregate"]["model"]),
                                *((f"BASELINE  {n}", b)
                                  for n, b in r["aggregate"]["baselines"].items())]:
        print(f"\n  {branch_name}")
        for pat, by_sev in branch.items():
            cell = by_sev.get("typical", {})
            if not cell:
                continue
            roc = cell["roc_auc"]
            r_20 = cell["recall_at_fpr"].get("fpr=0.200", {})
            r_01 = cell["recall_at_fpr"].get("fpr=0.010", {})
            print(f"    {pat:<22} ROC mean={roc['mean']:.3f} CI[{roc['ci_low']:.3f},{roc['ci_high']:.3f}]  "
                  f"R@20%={_pct(r_20['mean'])} CI[{_pct(r_20['ci_low'])},{_pct(r_20['ci_high'])}]  "
                  f"R@1%={_pct(r_01['mean'])} CI[{_pct(r_01['ci_low'])},{_pct(r_01['ci_high'])}]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=list(range(5)))
    ap.add_argument("--legacy", action="store_true",
                    help="Run the legacy v2 IID pipeline instead of streams.")
    ap.add_argument("--drift", action="store_true",
                    help="Run only the drift smoke test and exit.")
    ap.add_argument("--fpr", type=float, default=0.20,
                    help="Legacy-only single FPR target.")
    args = ap.parse_args()

    print("UW MarketLens -- S3 synthetic anomaly evaluation")
    print("=" * 78)

    if args.drift:
        result = drift_smoke_test(seed=args.seeds[0])
        print(f"  Drift smoke test (seed={result['seed']})")
        print(f"    shift            : volume x{result['shift']['volume_mult']:.2f}  "
              f"volatility-sigma x{result['shift']['vol_sigma_mult']:.2f}")
        print(f"    AUC baseline     : {result['auc_baseline']:.3f}")
        print(f"    AUC shifted      : {result['auc_shifted']:.3f}")
        print(f"    delta AUC        : {result['delta_auc']:+.3f}")
        print(f"\n  {result['note']}")
        out = ROOT / "app" / "anomaly" / "last_drift.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nWrote {out.relative_to(ROOT.parent)}")
        return 0

    if args.legacy:
        if len(args.seeds) == 1:
            result = run(seed=args.seeds[0], fpr_target=args.fpr)
        else:
            result = run_multi(seeds=args.seeds, fpr_target=args.fpr)
        print(f"  Legacy v2 IID path, fpr_target={args.fpr:.0%}, seeds={args.seeds}")
    else:
        print(f"  Streams pipeline (v3), seeds={args.seeds}")
        print(f"  fpr_targets={list(DEFAULT_FPR_TARGETS)}  k_values={list(DEFAULT_K_VALUES)}")
        print(f"  patterns={list(INJECTORS) + ['coordinated_manip']}  severities={list(SEVERITIES)}")
        if len(args.seeds) == 1:
            result = run_streams(seed=args.seeds[0])
            _print_streams_single(result)
        else:
            result = run_streams_multi(seeds=args.seeds)
            _print_streams_multi(result)

    print()
    print(result["framing"])

    # B7: separate artifact paths so v2 (legacy IID) and v3 (streams) don't
    # clobber each other during debugging. `last_eval.json` is always the v3
    # streams artifact (the primary one).
    fname = "last_eval_v2.json" if args.legacy else "last_eval.json"
    out = ROOT / "app" / "anomaly" / fname
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWrote {out.relative_to(ROOT.parent)}  "
          f"({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
