"""Deck ingest pipeline — Prefect flow for presentation slide decks (PDF and PPTX).

Lifecycle:
pending -> fetching -> parsing -> captioning -> embedding -> indexed | failed

Locators:
Every chunk carries `locator: {"slide": slide_num}` (1-based), guaranteeing
exact, clickable slide references in cross-source citations.

Enrichment:
For image-heavy or diagrammatic slides with low text density (< 25 words),
a vision LLM generates a concise semantic caption that is fused into the slide chunk
text before embedding.
"""
from __future__ import annotations

import base64
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf as fitz
from prefect import flow, task

from .. import config, db
from ..config import DATA, TEXT_EMBED_VERSION
from ..rag import vector_store
from ..rag.embeddings import embed_docs

SCRATCH_DIR = DATA / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DeckChunk:
    text: str
    slide: int
    title: str = ""


def _download_deck(uri: str, target_path: Path) -> None:
    """Download presentation deck from HTTP/HTTPS URL or copy from local file path."""
    if uri.startswith("http://") or uri.startswith("https://"):
        req = urllib.request.Request(
            uri,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp, open(target_path, "wb") as f:
            while chunk := resp.read(1024 * 1024):
                f.write(chunk)
    elif uri.startswith("file://"):
        local_path = Path(urllib.parse.unquote(uri[7:]))
        target_path.write_bytes(local_path.read_bytes())
    else:
        local_path = Path(uri)
        if not local_path.is_file():
            raise FileNotFoundError(f"Source presentation file not found at: {uri}")
        target_path.write_bytes(local_path.read_bytes())


def _caption_slide_image(jpeg_bytes: bytes, api_key: str | None = None, model: str = "gpt-4o") -> str:
    """Invoke vision LLM to summarize slide architecture or diagrams."""
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        b64 = base64.b64encode(jpeg_bytes).decode("ascii")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Describe the key architecture, visual diagrams, and takeaways on this "
                                "presentation slide in 2 concise, factual sentences for search retrieval."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=150,
            timeout=15,
        )
        caption = resp.choices[0].message.content or ""
        return caption.strip()
    except Exception as exc:
        print(f"[caption] Slide image captioning skipped ({type(exc).__name__}: {exc})")
        return ""


@task(name="fetch-deck", retries=2, retry_delay_seconds=[10, 30])
def t_fetch_deck(doc_id: str, user_id: str, uri: str) -> str:
    """Acquire deck file into local scratch space."""
    db.set_document_status(doc_id, "fetching", progress=0.1)
    suffix = Path(urllib.parse.urlparse(uri).path).suffix or ".pdf"
    if suffix.lower() not in (".pdf", ".pptx"):
        suffix = ".pdf"
    target = SCRATCH_DIR / f"{doc_id}{suffix}"
    try:
        _download_deck(uri, target)
        if not target.exists() or target.stat().st_size == 0:
            raise RuntimeError(f"Downloaded presentation file is empty for {doc_id} from {uri}")
    except Exception as exc:
        db.set_document_status(doc_id, "failed", error=f"Fetch failed: {exc}")
        raise
    return str(target)


def _extract_pdf_slides(pdf_path: Path) -> list[dict[str, Any]]:
    doc = fitz.open(str(pdf_path))
    slides_data = []
    for idx in range(len(doc)):
        slide_num = idx + 1
        page = doc[idx]
        raw_text = page.get_text("text") or ""
        cleaned = re.sub(r"[ \t]+", " ", raw_text).strip()
        
        # Render slide image for vision captioning on visual slides
        pix = page.get_pixmap(dpi=150)
        jpeg_bytes = pix.tobytes("jpeg")
        slides_data.append({
            "slide": slide_num,
            "title": f"Slide {slide_num}",
            "text": cleaned,
            "image_bytes": jpeg_bytes,
        })
    doc.close()
    return slides_data


def _extract_pptx_slides(pptx_path: Path) -> list[dict[str, Any]]:
    from pptx import Presentation
    prs = Presentation(str(pptx_path))
    slides_data = []
    for idx, slide in enumerate(prs.slides):
        slide_num = idx + 1
        title = ""
        text_parts = []
        if slide.shapes.title and slide.shapes.title.text:
            title = slide.shapes.title.text.strip()
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    t = paragraph.text.strip()
                    if t and t != title:
                        text_parts.append(t)
        body = "\n".join(text_parts).strip()
        slides_data.append({
            "slide": slide_num,
            "title": title or f"Slide {slide_num}",
            "text": body,
            "image_bytes": None,
        })
    return slides_data


@task(name="parse-chunk-deck", retries=1, retry_delay_seconds=10)
def t_parse_chunk_deck(doc_id: str, user_id: str, deck_path: str) -> list[DeckChunk]:
    """Parse slides, generate visual captions for diagram slides, and create slide chunks."""
    db.set_document_status(doc_id, "parsing", progress=0.3)
    path = Path(deck_path)
    if path.suffix.lower() == ".pptx":
        raw_slides = _extract_pptx_slides(path)
    else:
        raw_slides = _extract_pdf_slides(path)

    if not raw_slides:
        raise RuntimeError(f"No slides extracted from presentation: {deck_path}")

    db.set_document_status(doc_id, "chunking", progress=0.5)
    chunks: list[DeckChunk] = []
    api_key = config.LLM_API_KEY or os.getenv("OPENAI_API_KEY", "")

    for s in raw_slides:
        slide_num = s["slide"]
        slide_title = s["title"]
        body_text = s["text"]
        words = body_text.split()

        # Visual captioning for low-text or diagrammatic slides
        caption = ""
        if len(words) < 25 and s.get("image_bytes") and api_key:
            caption = _caption_slide_image(s["image_bytes"], api_key=api_key)

        combined_parts = [f"Slide {slide_num}: {slide_title}"] if slide_title else [f"Slide {slide_num}"]
        if body_text:
            combined_parts.append(body_text)
        if caption:
            combined_parts.append(f"Visual Context: {caption}")

        full_text = "\n".join(combined_parts)
        chunks.append(DeckChunk(text=full_text, slide=slide_num, title=slide_title))

    print(f"[deck] {doc_id}: Extracted {len(chunks)} slide chunks from {path.name}.")
    return chunks


@task(name="embed-index-deck", retries=2, retry_delay_seconds=30)
def t_embed_index_deck(doc_id: str, user_id: str, chunks: list[DeckChunk],
                       title: str | None = None) -> int:
    """Embed slide chunks and upsert to the shared Qdrant text collection."""
    db.set_document_status(doc_id, "embedding", progress=0.7)
    vector_store.ensure_text_collection()
    # Idempotent cleanup of prior chunks
    vector_store.delete_document(user_id, doc_id)

    texts = [c.text for c in chunks]
    vectors = embed_docs(texts)

    payloads = [
        {
            "user_id": user_id,
            "source_id": doc_id,
            "doc_id": doc_id,
            "video_id": doc_id,  # supports shared query filters
            "kind": "deck",
            "title": title or doc_id,
            "locator": {"slide": c.slide},
            "slide": c.slide,
            "text": c.text,
            "chunk_idx": c.slide - 1,
            "embed_version": TEXT_EMBED_VERSION,
        }
        for c in chunks
    ]

    vector_store.upsert_document_chunks(user_id, doc_id, vectors, payloads)

    # Status update strictly AFTER vector upsert for crash resilience
    db.set_document_status(
        doc_id,
        "indexed",
        chunk_count=len(chunks),
        title=title,
        progress=1.0,
    )
    print(f"[deck] {doc_id}: Successfully indexed {len(chunks)} slides in shared text collection.")
    return len(chunks)


@flow(name="ms-ingest-deck", log_prints=True, timeout_seconds=1800)
def ingest_deck(doc_id: str, user_id: str) -> dict[str, Any]:
    """Prefect orchestration flow for presentation slide deck ingestion."""
    attempt = db.bump_document_attempts(doc_id)
    doc_row = db.get_document(doc_id)
    if not doc_row:
        raise ValueError(f"No document row found for {doc_id}")

    uri = doc_row["uri"]
    title = doc_row.get("title") or Path(uri).stem
    scratch_path: str | None = None

    try:
        scratch_path = t_fetch_deck(doc_id, user_id, uri)
        chunks = t_parse_chunk_deck(doc_id, user_id, scratch_path)
        count = t_embed_index_deck(doc_id, user_id, chunks, title=title)
        return {"doc_id": doc_id, "kind": "deck", "chunks": count, "attempt": attempt}
    except Exception as exc:
        db.set_document_status(doc_id, "failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if scratch_path:
            Path(scratch_path).unlink(missing_ok=True)
