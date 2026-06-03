from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .labeled import DEFAULT_CASES_PATH, Case, load_cases  # noqa: F401, E402
from ..ingestion.polymarket import fetch_market  # noqa: E402
from ..resolution import resolve_market  # noqa: E402

BUCKET_LABELS = [
    "0.0–0.2",
    "0.2–0.4",
    "0.4–0.6",
    "0.6–0.8",
    "0.8–1.0",
]

DEFAULT_REPORT_PATH = Path(__file__).resolve().parent / "calibration_report.json"


def _bucket_label(confidence: float) -> str:
    if confidence < 0.2:
        return BUCKET_LABELS[0]
    if confidence < 0.4:
        return BUCKET_LABELS[1]
    if confidence < 0.6:
        return BUCKET_LABELS[2]
    if confidence < 0.8:
        return BUCKET_LABELS[3]
    return BUCKET_LABELS[4]


def _predicted_label(verdict: str) -> str:
    return "mundane" if verdict == "UNVERIFIABLE" else "controversial"


def _case_result(case: Case) -> dict[str, Any]:
    result = {
        "market_url": case.market_url,
        "label": case.label,
        "bucket": BUCKET_LABELS[0],
        "confidence": 0.0,
        "verdict": "UNVERIFIABLE",
        "predicted_label": _predicted_label("UNVERIFIABLE"),
        "match": case.label == "mundane",
        "error": None,
    }
    try:
        market = fetch_market(case.market_url)
        assessment = resolve_market(market.question, resolved=market.resolved)
        confidence = float(assessment.confidence)
        result.update(
            bucket=_bucket_label(confidence),
            confidence=confidence,
            verdict=assessment.verdict,
            predicted_label=_predicted_label(assessment.verdict),
            match=_predicted_label(assessment.verdict) == case.label,
        )
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    return result


def generate_calibration_report(cases_path: str | Path = DEFAULT_CASES_PATH) -> dict[str, Any]:
    cases = load_cases(cases_path)
    rows = [_case_result(case) for case in cases]

    buckets: list[dict[str, Any]] = []
    for label in BUCKET_LABELS:
        bucket_rows = [row for row in rows if row["bucket"] == label]
        count = len(bucket_rows)
        matched = sum(1 for row in bucket_rows if row["match"])
        avg_confidence = (
            sum(float(row["confidence"]) for row in bucket_rows) / count
            if count
            else 0.0
        )
        buckets.append(
            {
                "bucket": label,
                "count": count,
                "accuracy": float(matched / count) if count else 0.0,
                "avg_confidence": avg_confidence,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "n_cases": len(cases),
        "buckets": buckets,
        "rows": rows,
    }


def write_calibration_report(report: dict[str, Any], path: Path | str = DEFAULT_REPORT_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2), encoding="utf-8")
