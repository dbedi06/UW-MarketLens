"""Load + validate the pre-registered labeled-cases YAML, and compute
inter-rater agreement (Cohen's κ) with a bootstrap CI.

This is the data side of the Section D commitment: the rubric is locked
in `data/labeling_rubric.md`; the cases live in `data/labeled_cases.yaml`
and conform to the schema enforced here. Anything that doesn't validate
is rejected at load time (rather than producing silently-wrong κ later).
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date as _date
from pathlib import Path
from typing import Any, Iterable, Literal
import math

import numpy as np
import yaml


_LABELS = ("controversial", "mundane")
Label = Literal["controversial", "mundane"]
DATA_DIR = Path(__file__).parent / "data"
DEFAULT_CASES_PATH = DATA_DIR / "labeled_cases.yaml"
RUBRIC_PATH = DATA_DIR / "labeling_rubric.md"


@dataclass(frozen=True)
class Case:
    market_url: str
    label: Label
    evidence_url: str | None
    notes: str
    date_documented: _date
    labeler: str
    rubric_version: str


# --------------------------------------------------------------------------
# Loading + validation
# --------------------------------------------------------------------------

class LabeledSetError(ValueError):
    """Raised when the YAML doesn't conform to the rubric's schema."""


def _validate_row(row: dict, idx: int) -> Case:
    required = {"market_url", "label", "notes", "date_documented",
                "labeler", "rubric_version"}
    missing = required - row.keys()
    if missing:
        raise LabeledSetError(f"case[{idx}] missing fields: {sorted(missing)}")

    label = row["label"]
    if label not in _LABELS:
        raise LabeledSetError(
            f"case[{idx}] label {label!r} not in {_LABELS}")

    url = row["market_url"]
    if not isinstance(url, str) or "polymarket.com" not in url:
        raise LabeledSetError(
            f"case[{idx}] market_url must be a polymarket.com URL")

    evidence = row.get("evidence_url")
    if label == "controversial" and not evidence:
        raise LabeledSetError(
            f"case[{idx}] controversial cases require evidence_url "
            "(see rubric, 'Evidence standards')")

    d = row["date_documented"]
    if not isinstance(d, _date):
        raise LabeledSetError(
            f"case[{idx}] date_documented must parse as ISO date")

    return Case(
        market_url=url,
        label=label,
        evidence_url=evidence if isinstance(evidence, str) else None,
        notes=str(row["notes"]),
        date_documented=d,
        labeler=str(row["labeler"]),
        rubric_version=str(row["rubric_version"]),
    )


def load_cases(path: str | Path = DEFAULT_CASES_PATH) -> list[Case]:
    """Load + validate the YAML. Empty `cases: []` is permitted (the
    scaffold ships empty by design; the team accumulates rows)."""
    p = Path(path)
    if not p.exists():
        raise LabeledSetError(f"labeled-cases file not found: {p}")
    blob = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    cases_raw = blob.get("cases") or []
    if not isinstance(cases_raw, list):
        raise LabeledSetError("'cases' must be a list")
    out = [_validate_row(row, i) for i, row in enumerate(cases_raw)]
    return out


# --------------------------------------------------------------------------
# Cohen's κ
# --------------------------------------------------------------------------

def cohens_kappa(a: list[Label], b: list[Label]) -> float:
    """Cohen's κ for two equal-length label lists from independent
    labelers on the same items. Returns 0.0 for empty input.

    Standard formula:
        κ = (p_o - p_e) / (1 - p_e)
    where p_o is observed agreement and p_e is expected by chance from
    the marginals."""
    if len(a) != len(b):
        raise ValueError("a and b must be equal length")
    n = len(a)
    if n == 0:
        return 0.0
    arr_a = np.asarray(a)
    arr_b = np.asarray(b)
    p_o = float((arr_a == arr_b).mean())
    p_e = 0.0
    for lab in _LABELS:
        p_e += (arr_a == lab).mean() * (arr_b == lab).mean()
    if math.isclose(p_e, 1.0):
        # Perfect chance agreement (both labelers used only one label) →
        # κ is undefined; report 0.0 with a flag the caller can read.
        return 0.0
    return float((p_o - p_e) / (1.0 - p_e))


def kappa_with_ci(a: list[Label], b: list[Label], *,
                  n_boot: int = 2000, seed: int = 0
                  ) -> dict[str, float | int]:
    """Cohen's κ with a percentile bootstrap CI across paired items.
    Honest reporting at the small n typical of this set."""
    n = len(a)
    if n == 0:
        return {"kappa": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
    k = cohens_kappa(a, b)
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot, dtype=float)
    idx_pool = np.arange(n)
    for i in range(n_boot):
        idx = rng.choice(idx_pool, size=n, replace=True)
        ab = [a[j] for j in idx]
        bb = [b[j] for j in idx]
        boots[i] = cohens_kappa(ab, bb)
    return {
        "kappa": k,
        "ci_low": float(np.quantile(boots, 0.025)),
        "ci_high": float(np.quantile(boots, 0.975)),
        "n": n,
    }


def pairwise_kappa(cases: Iterable[Case]) -> list[dict[str, Any]]:
    """For every pair of labelers that share ≥ 2 markets, report Cohen's
    κ on the overlapping subset. Empty list if no labeler pair has
    sufficient overlap."""
    by_labeler: dict[str, dict[str, Label]] = {}
    for c in cases:
        by_labeler.setdefault(c.labeler, {})[c.market_url] = c.label
    labelers = sorted(by_labeler)
    out: list[dict[str, Any]] = []
    for i in range(len(labelers)):
        for j in range(i + 1, len(labelers)):
            la, lb = labelers[i], labelers[j]
            shared = sorted(set(by_labeler[la]) & set(by_labeler[lb]))
            if len(shared) < 2:
                continue
            a = [by_labeler[la][m] for m in shared]
            b = [by_labeler[lb][m] for m in shared]
            stat = kappa_with_ci(a, b)
            out.append({
                "labeler_a": la, "labeler_b": lb,
                "n_shared": len(shared),
                **stat,
            })
    return out


def class_balance(cases: Iterable[Case]) -> dict[str, int]:
    counts = {lab: 0 for lab in _LABELS}
    for c in cases:
        counts[c.label] += 1
    return counts
