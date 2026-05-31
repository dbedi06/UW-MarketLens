"""Train the S3 IsoForestDetector on the real Polymarket corpus and
save it to `app/anomaly/data/trained_model.pkl`.

Run this once after `build_real_corpus.py` has populated the corpus
directory. On the next FastAPI boot (`get_detector()` startup hook),
the pickle is loaded instead of the synthetic fallback.

Usage:
    python -m scripts.train_from_corpus
    python -m scripts.train_from_corpus --corpus-dir <custom> --out <custom>
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.anomaly.scoring import (  # noqa: E402
    CORPUS_DIR, MODEL_PATH, save_detector, train_from_corpus,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus-dir", type=Path, default=CORPUS_DIR)
    p.add_argument("--out", type=Path, default=MODEL_PATH)
    p.add_argument("--n-estimators", type=int, default=200)
    p.add_argument("--contamination", type=float, default=0.05)
    args = p.parse_args()

    print(f"[train] corpus: {args.corpus_dir}")
    print(f"[train] n_estimators={args.n_estimators} "
          f"contamination={args.contamination}")

    t0 = time.perf_counter()
    try:
        det = train_from_corpus(
            args.corpus_dir,
            n_estimators=args.n_estimators,
            contamination=args.contamination,
        )
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    dt = time.perf_counter() - t0
    print(f"[train] fit complete in {dt:.1f}s")
    print(f"[train] markets used: {getattr(det, '_corpus_n_markets', '?')}")
    print(f"[train] total windows: {getattr(det, '_corpus_n_windows', '?')}")
    print(f"[train] network medians: "
          f"{getattr(det, '_network_medians', None)}")

    save_detector(det, args.out)
    print(f"[save]  pickled detector -> {args.out}")
    print(f"[save]  size: {args.out.stat().st_size / 1024:.1f} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
