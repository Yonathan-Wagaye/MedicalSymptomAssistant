"""
Ingest WHO fact sheets into pgvector.

Fetches a curated set of WHO disease fact sheets, extracts the article
body, chunks it, and stores it.  These supplement the MedlinePlus core
knowledge base with WHO's authoritative disease guidance.

The curated list targets diseases most useful for a symptom-checking
application.  Add or remove slugs in ``FACT_SHEET_SLUGS`` to customise.

Usage (from project root):
    python -m backend.scripts.ingest_who
"""

from __future__ import annotations

import logging
import sys
import time

import requests
from bs4 import BeautifulSoup

from backend.core.database import SessionLocal
from backend.core.logging import setup_logging
from backend.services import vector_store
from backend.services.chunking import chunk_text
from backend.services.ingest import ingest_documents

setup_logging()
logger = logging.getLogger(__name__)

SOURCE_PREFIX = "who"
BASE_URL = "https://www.who.int/news-room/fact-sheets/detail"

FACT_SHEET_SLUGS: list[str] = [
    # --- infectious diseases ---
    "influenza-(seasonal)",
    "dengue-and-severe-dengue",
    "malaria",
    "tuberculosis",
    "hiv-aids",
    "hepatitis-b",
    "hepatitis-c",
    "cholera",
    "measles",
    "rabies",
    "meningococcal-meningitis",
    "typhoid",
    "ebola-virus-disease",
    "nipah-virus-infection",
    "mpox",
    "yellow-fever",
    "chikungunya",
    "zika-virus",
    "pneumonia",
    "diarrhoeal-disease",
    "leprosy",
    "tetanus",
    # --- non-communicable diseases ---
    "diabetes",
    "cardiovascular-diseases-(cvds)",
    "cancer",
    "chronic-obstructive-pulmonary-disease-(copd)",
    "asthma",
    "epilepsy",
    "hypertension",
    "obesity-and-overweight",
    # --- other high-relevance topics ---
    "antimicrobial-resistance",
    "mental-disorders",
    "depression",
]


def _fetch_fact_sheet(slug: str) -> dict | None:
    """Fetch and extract body text from one WHO fact sheet page."""
    url = f"{BASE_URL}/{slug}"

    try:
        resp = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "MedicalSymptomAssistant/1.0 (educational project)"},
        )
        if resp.status_code != 200:
            logger.warning("HTTP %d for %s — skipping", resp.status_code, url)
            return None
    except requests.RequestException as exc:
        logger.warning("Request failed for %s: %s", url, exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    title_el = soup.find("h1")
    title = title_el.get_text(strip=True) if title_el else slug.replace("-", " ").title()

    article = (
        soup.find("article")
        or soup.find("div", class_="sf-detail-body-wrapper")
        or soup.find("div", {"id": "PageContent"})
        or soup.find("main")
    )
    if not article:
        logger.warning("No article body found for %s — skipping", slug)
        return None

    for tag in article.find_all(["script", "style", "nav", "footer"]):
        tag.decompose()

    parts: list[str] = []
    for el in article.find_all(["h2", "h3", "h4", "p", "li"]):
        text = el.get_text(strip=True)
        if not text:
            continue
        if el.name in ("h2", "h3", "h4"):
            parts.append(f"\n{text}\n")
        else:
            parts.append(text)

    body = "\n".join(parts).strip()
    if len(body) < 100:
        logger.warning("Content too short for %s (%d chars) — skipping", slug, len(body))
        return None

    return {"title": title, "url": url, "content": f"{title}\n\n{body}"}


def run(*, batch_size: int = 64) -> int:
    """Core logic — returns the number of chunks ingested."""
    logger.info("Fetching %d WHO fact sheets …", len(FACT_SHEET_SLUGS))

    all_docs: list[dict] = []
    fetched = 0

    for slug in FACT_SHEET_SLUGS:
        result = _fetch_fact_sheet(slug)
        if result is None:
            continue

        fetched += 1
        chunks = chunk_text(result["content"], max_chars=1500, overlap_chars=200)

        slug_key = slug.replace("-", "_").replace("(", "").replace(")", "")
        for ci, chunk_body in enumerate(chunks):
            all_docs.append(
                {
                    "content": chunk_body,
                    "source_id": f"{SOURCE_PREFIX}_{slug_key}_{ci}",
                    "title": result["title"],
                    "section": "WHO Fact Sheet",
                    "url": result["url"],
                }
            )

        time.sleep(1.5)

    logger.info("Fetched %d/%d fact sheets → %d chunks", fetched, len(FACT_SHEET_SLUGS), len(all_docs))

    if not all_docs:
        logger.warning("No documents fetched — nothing to ingest")
        return 0

    db = SessionLocal()
    try:
        count = ingest_documents(db, all_docs, batch_size=batch_size, clear_source=SOURCE_PREFIX)
        total = vector_store.count_chunks(db)
        logger.info("Verification: %d total chunks in document_chunks", total)
        print(f"\nDone!  Ingested {count} WHO fact-sheet chunks.")
        print(f"Total chunks in database: {total}")
        return count
    finally:
        db.close()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
