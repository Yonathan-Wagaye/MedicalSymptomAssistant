"""
Ingest MedlinePlus health topics XML into pgvector.

MedlinePlus provides ~1 000 authoritative health-topic summaries covering
symptoms, causes, treatments, and prevention.  Each topic becomes one or
more chunks in ``document_chunks``.

The XML file is published at https://medlineplus.gov/xml.html and updated
weekly.  This script can auto-download it or accept a local path.

Usage (from project root):
    python -m backend.scripts.ingest_medlineplus            # auto-download
    python -m backend.scripts.ingest_medlineplus --xml-path data/mplus.xml
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from lxml import etree

from backend.core.database import SessionLocal
from backend.core.logging import setup_logging
from backend.services import vector_store
from backend.services.chunking import chunk_text, strip_html
from backend.services.ingest import ingest_documents

setup_logging()
logger = logging.getLogger(__name__)

SOURCE_PREFIX = "mlp"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "medlineplus"
XML_LISTING_URL = "https://medlineplus.gov/xml.html"


# ------------------------------------------------------------------
# Download helpers
# ------------------------------------------------------------------

def _find_local_xml() -> Path | None:
    """Return the newest cached XML in DATA_DIR, or None."""
    if not DATA_DIR.exists():
        return None
    candidates = sorted(DATA_DIR.glob("mplus_topics*.xml"), reverse=True)
    return candidates[0] if candidates else None


def _resolve_download_url() -> str:
    """Build or discover the current MedlinePlus health-topics XML URL.

    Strategy:
      1. Try date-stamped URLs for the last 7 days (the file is updated weekly).
      2. Fall back to scraping the XML listing page.
    """
    base = "https://medlineplus.gov/xml/mplus_topics_{}.xml"
    today = date.today()

    for offset in range(7):
        candidate = base.format((today - timedelta(days=offset)).isoformat())
        logger.info("Probing %s …", candidate)
        try:
            head = requests.head(candidate, timeout=15, allow_redirects=True)
            if head.status_code == 200:
                logger.info("Found XML at %s", candidate)
                return candidate
        except requests.RequestException:
            continue

    logger.info("Date-based probe failed; scraping %s …", XML_LISTING_URL)
    resp = requests.get(XML_LISTING_URL, timeout=30)
    resp.raise_for_status()

    match = re.search(
        r'href="(/xml/mplus_topics[^"]*\.xml)"',
        resp.text,
    )
    if not match:
        raise RuntimeError(
            "Could not find the health-topics XML link on the MedlinePlus "
            "listing page.  Download it manually from "
            "https://medlineplus.gov/xml.html and pass --xml-path."
        )
    return f"https://medlineplus.gov{match.group(1)}"


def _download_xml() -> Path:
    """Download the health-topics XML and cache it locally."""
    url = _resolve_download_url()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    filename = url.rsplit("/", 1)[-1]
    dest = DATA_DIR / filename

    logger.info("Downloading %s …", url)
    resp = requests.get(url, timeout=180, stream=True)
    resp.raise_for_status()

    with open(dest, "wb") as f:
        for block in resp.iter_content(chunk_size=1024 * 64):
            f.write(block)

    size_mb = dest.stat().st_size / (1024 * 1024)
    logger.info("Saved %.1f MB → %s", size_mb, dest)
    return dest


# ------------------------------------------------------------------
# XML parsing
# ------------------------------------------------------------------

def _parse_topics(xml_path: Path) -> list[dict]:
    """Parse ``<health-topic>`` elements into document dicts."""
    logger.info("Parsing %s …", xml_path)
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    documents: list[dict] = []
    topic_count = 0

    for topic in root.iter("health-topic"):
        if topic.get("language", "English") != "English":
            continue

        title = (topic.get("title") or "").strip()
        url = topic.get("url", "")
        topic_id = topic.get("id", "")

        summary_el = topic.find("full-summary")
        if summary_el is None or not (summary_el.text or "").strip():
            continue

        body = strip_html(summary_el.text or "")
        if not body:
            continue

        alt_names = [
            el.text.strip()
            for el in topic.findall("also-called")
            if el.text
        ]
        groups = [
            el.text.strip()
            for el in topic.findall("group")
            if el.text
        ]
        section = ", ".join(groups) if groups else "General"

        header = title
        if alt_names:
            header += f" (also called: {', '.join(alt_names)})"

        body_chunks = chunk_text(body, max_chars=1400, overlap_chars=200)

        for ci, chunk_body in enumerate(body_chunks):
            content = f"{header}\n\n{chunk_body}" if ci == 0 else f"{title}\n\n{chunk_body}"
            documents.append(
                {
                    "content": content,
                    "source_id": f"{SOURCE_PREFIX}_{topic_id}_{ci}",
                    "title": title,
                    "section": section,
                    "url": url,
                }
            )

        topic_count += 1

    logger.info("Parsed %d English topics → %d chunks", topic_count, len(documents))
    return documents


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def run(*, xml_path: str | None = None, batch_size: int = 64) -> int:
    """Core logic — returns the number of chunks ingested."""
    if xml_path:
        path = Path(xml_path)
        if not path.exists():
            logger.error("File not found: %s", path)
            sys.exit(1)
    else:
        path = _find_local_xml()
        if path:
            logger.info("Using cached XML: %s", path)
        else:
            path = _download_xml()

    documents = _parse_topics(path)
    if not documents:
        logger.warning("No documents parsed — nothing to ingest")
        return 0

    db = SessionLocal()
    try:
        count = ingest_documents(
            db, documents, batch_size=batch_size, clear_source=SOURCE_PREFIX,
        )
        total = vector_store.count_chunks(db)
        logger.info("Verification: %d total chunks in document_chunks", total)
        print(f"\nDone!  Ingested {count} MedlinePlus chunks.")
        print(f"Total chunks in database: {total}")
        return count
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest MedlinePlus health topics")
    parser.add_argument("--xml-path", default=None, help="Local XML file (skip download)")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    run(xml_path=args.xml_path, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
