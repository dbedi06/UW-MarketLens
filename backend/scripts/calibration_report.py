"""Compute an S4 confidence calibration check over the labeled corpus.

Outputs a JSON report under backend/app/anomaly/calibration_report.json.

Usage:
    python -m scripts.calibration_report
    python -m scripts.calibration_report --dry-run
    python -m scripts.calibration_report --cases backend/app/anomaly/data/labeled_cases.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.anomaly.calibration import (
    DEFAULT_REPORT_PATH,
    generate_calibration_report,
    write_calibration_report,
)  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a labeled-cases calibration report for S4 resolution confidence."
    )
    parser.add_argument(
        "--cases",
        default=None,
        help="Path to the labeled-cases YAML file.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_REPORT_PATH),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a preview without writing the output file.",
    )
    args = parser.parse_args()

    report = generate_calibration_report(args.cases) if args.cases else generate_calibration_report()

    if args.dry_run:
        import json

        print(json.dumps(report, indent=2))
        return 0

    write_calibration_report(report, Path(args.out))
    print(f"  wrote {Path(args.out).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
