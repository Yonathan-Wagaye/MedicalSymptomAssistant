"""
Text chunking utilities for the RAG ingestion pipeline.

Splits long documents into overlapping chunks that respect paragraph
boundaries.  Small, focused chunks are easier for embedding models to
represent than entire documents, which improves retrieval quality.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser


class _HTMLStripper(HTMLParser):
    """Strips HTML tags and decodes entities to plain text."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def strip_html(html: str) -> str:
    """Remove HTML tags and return clean plain text."""
    stripper = _HTMLStripper()
    stripper.feed(html)
    text = stripper.get_text()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    max_chars: int = 1500,
    overlap_chars: int = 200,
) -> list[str]:
    """
    Split *text* into chunks at paragraph boundaries.

    When a single paragraph exceeds *max_chars* it is split at sentence
    boundaries instead.  Adjacent chunks share *overlap_chars* characters
    so retrieval context is not lost at boundaries.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            sentences = re.split(r"(?<=[.!?])\s+", para)
            sent_buf = ""
            for sent in sentences:
                if len(sent_buf) + len(sent) + 1 > max_chars and sent_buf:
                    chunks.append(sent_buf.strip())
                    sent_buf = sent
                else:
                    sent_buf = f"{sent_buf} {sent}".strip()
            if sent_buf:
                chunks.append(sent_buf.strip())
            continue

        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current.strip())
            current = para

    if current:
        chunks.append(current.strip())

    if overlap_chars > 0 and len(chunks) > 1:
        overlapped: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap_chars:]
            space_idx = tail.find(" ")
            if space_idx != -1:
                tail = tail[space_idx + 1 :]
            overlapped.append(f"{tail}\n\n{chunks[i]}")
        chunks = overlapped

    return [c for c in chunks if c.strip()]
