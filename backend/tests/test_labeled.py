"""Tests for the labeled-cases scaffold (A1).

Validates the YAML schema, the loader, Cohen's κ math, and the
pairwise aggregator. The actual labels live in
`app/anomaly/data/labeled_cases.yaml` and accumulate over time; these
tests work against tiny in-memory fixtures so they stay deterministic
and don't depend on the team's labeling progress."""

from __future__ import annotations
from datetime import date
from pathlib import Path

import pytest
import yaml

from app.anomaly.labeled import (
    Case, LabeledSetError, class_balance, cohens_kappa,
    kappa_with_ci, load_cases, pairwise_kappa,
)


# ---- schema validation ---------------------------------------------------

def _write_yaml(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "cases.yaml"
    p.write_text(yaml.safe_dump({
        "schema_version": 1, "rubric_version": "v1", "cases": rows,
    }), encoding="utf-8")
    return p


def test_load_empty_is_ok(tmp_path):
    p = _write_yaml(tmp_path, [])
    assert load_cases(p) == []


def test_load_real_committed_yaml_validates():
    """The shipped scaffold YAML must always be valid."""
    cases = load_cases()
    assert isinstance(cases, list)  # may be empty; must be a list


def test_missing_required_field_rejected(tmp_path):
    p = _write_yaml(tmp_path, [{
        "market_url": "https://polymarket.com/event/x",
        "label": "mundane",
        # missing notes/date_documented/labeler/rubric_version
    }])
    with pytest.raises(LabeledSetError, match="missing fields"):
        load_cases(p)


def test_bad_label_rejected(tmp_path):
    p = _write_yaml(tmp_path, [{
        "market_url": "https://polymarket.com/event/x",
        "label": "ambiguous",
        "notes": "n/a",
        "date_documented": date(2026, 5, 19),
        "labeler": "AA",
        "rubric_version": "v1",
    }])
    with pytest.raises(LabeledSetError, match="label"):
        load_cases(p)


def test_non_polymarket_url_rejected(tmp_path):
    p = _write_yaml(tmp_path, [{
        "market_url": "https://kalshi.com/markets/x",
        "label": "mundane",
        "notes": "n/a",
        "date_documented": date(2026, 5, 19),
        "labeler": "AA",
        "rubric_version": "v1",
    }])
    with pytest.raises(LabeledSetError, match="polymarket.com"):
        load_cases(p)


def test_controversial_without_evidence_rejected(tmp_path):
    """The rubric requires evidence for `controversial`."""
    p = _write_yaml(tmp_path, [{
        "market_url": "https://polymarket.com/event/x",
        "label": "controversial",
        "notes": "alleged manipulation",
        "date_documented": date(2026, 5, 19),
        "labeler": "AA",
        "rubric_version": "v1",
        # no evidence_url
    }])
    with pytest.raises(LabeledSetError, match="evidence_url"):
        load_cases(p)


def test_well_formed_loads(tmp_path):
    p = _write_yaml(tmp_path, [{
        "market_url": "https://polymarket.com/event/abc",
        "label": "controversial",
        "evidence_url": "https://example.com/report",
        "notes": "documented in [outlet]",
        "date_documented": date(2026, 5, 19),
        "labeler": "AA",
        "rubric_version": "v1",
    }, {
        "market_url": "https://polymarket.com/event/def",
        "label": "mundane",
        "evidence_url": None,
        "notes": "no controversy surfaced in search",
        "date_documented": date(2026, 5, 19),
        "labeler": "BB",
        "rubric_version": "v1",
    }])
    cases = load_cases(p)
    assert len(cases) == 2
    assert isinstance(cases[0], Case)
    assert cases[0].label == "controversial"
    assert cases[1].evidence_url is None


# ---- Cohen's kappa -------------------------------------------------------

def test_kappa_perfect_agreement_is_one():
    labels = ["controversial", "mundane", "controversial", "mundane"]
    assert cohens_kappa(labels, labels) == pytest.approx(1.0)


def test_kappa_anti_agreement_is_negative():
    a = ["controversial", "mundane", "controversial", "mundane"]
    b = ["mundane", "controversial", "mundane", "controversial"]
    assert cohens_kappa(a, b) < 0


def test_kappa_chance_agreement_is_near_zero():
    """If labels are random/independent, κ should be ~0. Use a large n
    with independent draws to keep variance small."""
    import random
    rng = random.Random(0)
    n = 1000
    a = [rng.choice(["controversial", "mundane"]) for _ in range(n)]
    b = [rng.choice(["controversial", "mundane"]) for _ in range(n)]
    k = cohens_kappa(a, b)
    assert abs(k) < 0.1


def test_kappa_known_2x2_example():
    """Hand-computed: 10 controversial agreed + 10 mundane agreed +
    5 disagreed each way. p_o = 20/30 ≈ 0.667. Marginals 15/30 each so
    p_e = 0.5. κ = (0.667 - 0.5) / 0.5 = 0.333."""
    a = (["controversial"] * 15) + (["mundane"] * 15)
    b = (["controversial"] * 10 + ["mundane"] * 5
         + ["controversial"] * 5 + ["mundane"] * 10)
    assert cohens_kappa(a, b) == pytest.approx(1 / 3, abs=0.01)


def test_kappa_empty_inputs_returns_zero():
    assert cohens_kappa([], []) == 0.0


def test_kappa_length_mismatch_raises():
    with pytest.raises(ValueError):
        cohens_kappa(["mundane"], ["mundane", "mundane"])


def test_kappa_ci_brackets_point_estimate():
    a = (["controversial"] * 8) + (["mundane"] * 8)
    b = (["controversial"] * 7 + ["mundane"]
         + ["controversial"] + ["mundane"] * 7)
    stat = kappa_with_ci(a, b, n_boot=500, seed=0)
    assert stat["ci_low"] <= stat["kappa"] <= stat["ci_high"]
    assert stat["n"] == 16


# ---- pairwise aggregator -------------------------------------------------

def test_pairwise_kappa_skips_pairs_with_low_overlap(tmp_path):
    cases = [
        Case("https://polymarket.com/event/a", "controversial",
             "https://x", "n", date(2026, 5, 19), "AA", "v1"),
        Case("https://polymarket.com/event/b", "mundane",
             None, "n", date(2026, 5, 19), "AA", "v1"),
        Case("https://polymarket.com/event/c", "mundane",
             None, "n", date(2026, 5, 19), "BB", "v1"),
        # BB only labels one market AA labeled -> overlap=1, skipped.
    ]
    assert pairwise_kappa(cases) == []


def test_pairwise_kappa_reports_pair_with_enough_overlap():
    cases = [
        # AA labels three markets
        Case("https://polymarket.com/event/a", "controversial",
             "https://x", "n", date(2026, 5, 19), "AA", "v1"),
        Case("https://polymarket.com/event/b", "mundane",
             None, "n", date(2026, 5, 19), "AA", "v1"),
        Case("https://polymarket.com/event/c", "mundane",
             None, "n", date(2026, 5, 19), "AA", "v1"),
        # BB labels the same three
        Case("https://polymarket.com/event/a", "controversial",
             "https://x", "n", date(2026, 5, 19), "BB", "v1"),
        Case("https://polymarket.com/event/b", "mundane",
             None, "n", date(2026, 5, 19), "BB", "v1"),
        Case("https://polymarket.com/event/c", "controversial",
             "https://x", "n", date(2026, 5, 19), "BB", "v1"),
    ]
    pairs = pairwise_kappa(cases)
    assert len(pairs) == 1
    p = pairs[0]
    assert p["labeler_a"] == "AA" and p["labeler_b"] == "BB"
    assert p["n_shared"] == 3
    assert -1.0 <= p["ci_low"] <= p["kappa"] <= p["ci_high"] <= 1.0


# ---- class balance -------------------------------------------------------

def test_class_balance_counts():
    cases = [
        Case("https://polymarket.com/event/a", "controversial",
             "https://x", "n", date(2026, 5, 19), "AA", "v1"),
        Case("https://polymarket.com/event/b", "mundane",
             None, "n", date(2026, 5, 19), "AA", "v1"),
        Case("https://polymarket.com/event/c", "mundane",
             None, "n", date(2026, 5, 19), "BB", "v1"),
    ]
    bal = class_balance(cases)
    assert bal == {"controversial": 1, "mundane": 2}
