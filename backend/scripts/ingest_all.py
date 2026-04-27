"""
Run all data-ingestion pipelines in sequence.

Recommended order:
  1. Kaggle Symptom2Disease   (small, fast — good sanity check)
  2. MedlinePlus XML          (core knowledge base)
  3. WHO fact sheets          (supplementary, needs network)
  4. WHO outbreak news        (live context layer)

Each step is idempotent — it clears its own source-prefix before
inserting, so re-running is safe.

Usage (from project root):
    python -m backend.scripts.ingest_all
    python -m backend.scripts.ingest_all --skip-kaggle --skip-outbreaks
"""

from __future__ import annotations

import argparse
import logging
import traceback

from backend.core.database import SessionLocal
from backend.core.logging import setup_logging
from backend.services import vector_store

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all ingestion pipelines")
    parser.add_argument("--skip-kaggle", action="store_true")
    parser.add_argument("--skip-medlineplus", action="store_true")
    parser.add_argument("--skip-who", action="store_true")
    parser.add_argument("--skip-outbreaks", action="store_true")
    args = parser.parse_args()

    steps: list[tuple[str, str]] = []
    if not args.skip_kaggle:
        steps.append(("Kaggle Symptom2Disease", "kaggle"))
    if not args.skip_medlineplus:
        steps.append(("MedlinePlus Health Topics", "medlineplus"))
    if not args.skip_who:
        steps.append(("WHO Fact Sheets", "who"))
    if not args.skip_outbreaks:
        steps.append(("WHO Outbreak News", "outbreaks"))

    print(f"\n{'=' * 60}")
    print("Medical Symptom Assistant — Full Data Ingestion")
    print(f"{'=' * 60}")
    print(f"Running {len(steps)} step(s)…\n")

    for i, (label, key) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {label}")
        print("-" * 40)

        try:
            if key == "kaggle":
                from backend.scripts.ingest_kaggle import main as _run
                _run()
            elif key == "medlineplus":
                from backend.scripts.ingest_medlineplus import run as _run_mlp
                _run_mlp()
            elif key == "who":
                from backend.scripts.ingest_who import run as _run_who
                _run_who()
            elif key == "outbreaks":
                from backend.scripts.ingest_outbreaks import run as _run_ob
                _run_ob()
        except SystemExit:
            pass
        except Exception:
            logger.error("Step '%s' failed:\n%s", label, traceback.format_exc())
            print(f"  FAILED — see logs for details")

    db = SessionLocal()
    try:
        total = vector_store.count_chunks(db)
    finally:
        db.close()

    print(f"\n{'=' * 60}")
    print(f"All done!  Total chunks in database: {total}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
