"""
Ingest WHO Disease Outbreak News into pgvector.

Queries the WHO Disease Outbreak News API for recent alerts and stores
them as document chunks.  This forms the "live context" layer — separate
from the stable symptom knowledge base — so the app can answer questions
like "Are there recent measles outbreaks?" without contaminating core
symptom-to-condition retrieval.

Re-running this script replaces all previous outbreak chunks (idempotent).

Usage (from project root):
    python -m backend.scripts.ingest_outbreaks
    python -m backend.scripts.ingest_outbreaks --limit 50
"""

from __future__ import annotations

import argparse
import logging
import re
import sys

import requests

from backend.core.database import SessionLocal
from backend.core.logging import setup_logging
from backend.services import vector_store
from backend.services.chunking import chunk_text, strip_html
from backend.services.ingest import ingest_documents

setup_logging()
logger = logging.getLogger(__name__)

SOURCE_PREFIX = "who_outbreak"
API_URL = "https://www.who.int/api/news/diseaseoutbreaknews"


def _fetch_outbreaks(limit: int = 30) -> list[dict]:
    """Query the WHO DON API and return a list of document dicts."""
    logger.info("Fetching up to %d outbreak items from WHO API …", limit)

    try:
        resp = requests.get(
            API_URL,
            params={
                "sf_culture": "en",
                "$orderby": "PublicationDateAndTime desc",
                "$top": limit,
            },
            timeout=30,
            headers={"User-Agent": "MedicalSymptomAssistant/1.0 (educational project)"},
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("WHO API request failed: %s", exc)
        return []

    data = resp.json()
    items = data.get("value", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        logger.warning("Unexpected API response structure (type=%s)", type(items).__name__)
        return []

    documents: list[dict] = []
    for item in items:
        title = (item.get("Title") or item.get("title") or "").strip()
        summary = item.get("Summary") or item.get("summary") or ""
        body = item.get("BodyContent") or item.get("body") or ""
        url_name = item.get("UrlName") or item.get("ItemDefaultUrl") or ""
        pub_date = item.get("PublicationDateAndTime") or ""

        raw_text = strip_html(body or summary)
        if not raw_text:
            continue

        if pub_date:
            content = f"[Published: {pub_date[:10]}]\n\n{title}\n\n{raw_text}"
        else:
            content = f"{title}\n\n{raw_text}"

        if url_name and not url_name.startswith("http"):
            url_name = f"https://www.who.int/emergencies/disease-outbreak-news/{url_name}"

        chunks = chunk_text(content, max_chars=1500, overlap_chars=200)

        safe_key = re.sub(r"[^a-z0-9]+", "_", title.lower())[:50].strip("_")
        for ci, chunk_body in enumerate(chunks):
            documents.append(
                {
                    "content": chunk_body,
                    "source_id": f"{SOURCE_PREFIX}_{safe_key}_{ci}",
                    "title": title,
                    "section": "WHO Outbreak News",
                    "url": url_name,
                }
            )

    logger.info("Parsed %d API items → %d chunks", len(items), len(documents))
    return documents


def run(*, limit: int = 30, batch_size: int = 64) -> int:
    """Core logic — returns the number of chunks ingested."""
    documents = _fetch_outbreaks(limit=limit)
    if not documents:
        logger.warning("No outbreak documents fetched — nothing to ingest")
        return 0

    db = SessionLocal()
    try:
        count = ingest_documents(
            db, documents, batch_size=batch_size, clear_source=SOURCE_PREFIX,
        )
        total = vector_store.count_chunks(db)
        logger.info("Verification: %d total chunks in document_chunks", total)
        print(f"\nDone!  Ingested {count} WHO outbreak-news chunks.")
        print(f"Total chunks in database: {total}")
        return count
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest WHO Disease Outbreak News")
    parser.add_argument("--limit", type=int, default=30, help="Recent items to fetch (default: 30)")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    run(limit=args.limit, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
