"""
Ingest the Symptom2Disease Kaggle dataset into pgvector.

The dataset: 1200 rows — 24 diseases × 50 symptom descriptions each.
Each row is a natural-language description like:
    "I have been experiencing a skin rash on my arms…"
paired with a disease label like "Psoriasis".

Each description becomes one chunk in document_chunks with:
  - content  = the symptom text (what gets embedded and searched)
  - title    = the disease name (shown in results)
  - source_id = unique identifier for idempotent re-runs
  - section  = "symptoms"
  - url      = link back to the Kaggle dataset

Usage (from project root):
    python -m backend.scripts.ingest_kaggle
"""

import csv
import logging
import sys

import kagglehub

from backend.core.database import SessionLocal
from backend.core.logging import setup_logging
from backend.services import vector_store
from backend.services.ingest import ingest_documents

setup_logging()
logger = logging.getLogger(__name__)

DATASET = "niyarrbarman/symptom2disease"
SOURCE_PREFIX = "s2d"


def main() -> None:
    # ── 1. Download (uses kagglehub cache after first run) ──
    logger.info("Downloading dataset '%s' …", DATASET)
    dataset_path = kagglehub.dataset_download(DATASET)
    csv_path = f"{dataset_path}/Symptom2Disease.csv"
    logger.info("CSV path: %s", csv_path)

    # ── 2. Read CSV → list of document dicts ──
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    diseases = sorted(set(r["label"] for r in rows))
    logger.info("Read %d rows, %d unique diseases", len(rows), len(diseases))

    documents: list[dict] = []
    for i, row in enumerate(rows):
        disease = row["label"].strip()
        text = row["text"].strip()
        documents.append(
            {
                "content": text,
                "source_id": f"{SOURCE_PREFIX}_{disease.lower().replace(' ', '_')}_{i}",
                "title": disease,
                "section": "symptoms",
                "url": "https://www.kaggle.com/datasets/niyarrbarman/symptom2disease",
            }
        )

    # ── 3. Embed + store (clears previous run first) ──
    db = SessionLocal()
    try:
        count = ingest_documents(db, documents, batch_size=64, clear_source=SOURCE_PREFIX)

        # ── 4. Quick verification ──
        total = vector_store.count_chunks(db)
        logger.info("Verification: %d total chunks in document_chunks", total)

        print(f"\nDone!  Ingested {count} chunks into pgvector.")
        print(f"Total chunks in database: {total}")
        print(f"Diseases: {', '.join(diseases)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
