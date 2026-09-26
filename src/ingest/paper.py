"""Paper ingest pipeline — Prefect flow for PDF academic and technical papers.

Lifecycle:
pending -> fetching -> parsing -> chunking -> embedding -> indexed | failed

Locators:
Every chunk carries `locator: {"page": page_num}` where page_num is 1-based,
guaranteeing grounded, exact citations for the search and answer synthesis layers.
"""
from __future__ import annotations

import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf as fitz
from prefect import flow, task

try:
    from .. import db
    from ..config import DATA, TEXT_EMBED_VERSION
    from ..rag import vector_store
    from ..rag.embeddings import embed_docs
except (ImportError, ValueError):
    from src import db
    from src.config import DATA, TEXT_EMBED_VERSION
    from src.rag import vector_store
    from src.rag.embeddings import embed_docs

SCRATCH_DIR = DATA / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PaperChunk:
    text: str
    page: int
    chunk_idx: int


def _download_pdf(uri: str, target_path: Path) -> None:
    """Download PDF from HTTP/HTTPS URL or copy from local file path."""
    if uri.startswith("http://") or uri.startswith("https://"):
        req = urllib.request.Request(
            uri,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/pdf,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp, open(target_path, "wb") as f:
            while chunk := resp.read(1024 * 1024):
                f.write(chunk)
    elif uri.startswith("file://"):
        local_path = Path(urllib.parse.unquote(uri[7:]))
        target_path.write_bytes(local_path.read_bytes())
    else:
        # Direct local filesystem path
        local_path = Path(uri)
        if not local_path.is_file():
            raise FileNotFoundError(f"Source file not found at: {uri}")
        target_path.write_bytes(local_path.read_bytes())


@task(name="fetch-paper", retries=2, retry_delay_seconds=[10, 30])
def t_fetch_paper(doc_id: str, user_id: str, uri: str) -> str:
    """Acquire paper into local scratch space."""
    db.set_document_status(doc_id, "fetching", progress=0.1)
    target = SCRATCH_DIR / f"{doc_id}.pdf"
    try:
        _download_pdf(uri, target)
        if not target.exists() or target.stat().st_size == 0:
            raise RuntimeError(f"Downloaded PDF is empty for {doc_id} from {uri}")
    except Exception as exc:
        db.set_document_status(doc_id, "failed", error=f"Fetch failed: {exc}")
        raise
    return str(target)


def _clean_text(text: str) -> str:
    """Normalize whitespace and strip spurious control characters."""
    text = re.sub(r"[\r\n]+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _split_into_page_aware_chunks(page_text: str, page_num: int, start_idx: int,
                                   target_words: int = 400, overlap_words: int = 50) -> list[PaperChunk]:
    """Break long page text into bounded chunks without crossing page boundary."""
    words = page_text.split()
    if not words:
        return []
    
    if len(words) <= target_words + overlap_words:
        return [PaperChunk(text=" ".join(words), page=page_num, chunk_idx=start_idx)]

    chunks = []
    i = 0
    cur_idx = start_idx
    step = target_words - overlap_words
    while i < len(words):
        chunk_words = words[i:i + target_words]
        if not chunk_words:
            break
        chunk_str = " ".join(chunk_words)
        chunks.append(PaperChunk(text=chunk_str, page=page_num, chunk_idx=cur_idx))
        cur_idx += 1
        i += step
        if i + overlap_words >= len(words):
            # Trailing small piece: append to last chunk or as final chunk
            tail = words[i:]
            if tail:
                chunks.append(PaperChunk(text=" ".join(tail), page=page_num, chunk_idx=cur_idx))
            break
    return chunks


@task(name="parse-chunk-paper", retries=1, retry_delay_seconds=10)
def t_parse_chunk_paper(doc_id: str, user_id: str, pdf_path: str) -> list[PaperChunk]:
    """Parse PDF with PyMuPDF and generate page-aware semantic chunks."""
    db.set_document_status(doc_id, "parsing", progress=0.3)
    doc = fitz.open(pdf_path)
    all_chunks: list[PaperChunk] = []
    chunk_counter = 0

    db.set_document_status(doc_id, "chunking", progress=0.5)
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1  # 1-indexed page numbering
        raw_text = page.get_text("text") or ""
        cleaned = _clean_text(raw_text)
        if not cleaned:
            continue
        page_chunks = _split_into_page_aware_chunks(cleaned, page_num, chunk_counter)
        all_chunks.extend(page_chunks)
    page_count = len(doc)
    doc.close()
    if not all_chunks:
        raise RuntimeError(f"No readable text could be extracted from PDF: {pdf_path}")
    print(f"[paper] {doc_id}: Extracted {len(all_chunks)} page-aware chunks across {page_count} pages.")
    return all_chunks


@task(name="embed-index-paper", retries=2, retry_delay_seconds=30)
def t_embed_index_paper(doc_id: str, user_id: str, chunks: list[PaperChunk],
                        title: str | None = None) -> int:
    """Compute dense text embeddings and upsert to the shared Qdrant text collection."""
    db.set_document_status(doc_id, "embedding", progress=0.7)
    vector_store.ensure_text_collection()
    # Idempotent cleanup of prior chunks from failed attempts
    vector_store.delete_document(user_id, doc_id)

    texts = [c.text for c in chunks]
    vectors = embed_docs(texts)

    payloads = [
        {
            "user_id": user_id,
            "source_id": doc_id,
            "doc_id": doc_id,
            "video_id": doc_id,  # supports shared query filters
            "kind": "paper",
            "title": title or doc_id,
            "text": c.text,
            "locator": {"page": c.page},
            "page": c.page,
            "chunk_idx": c.chunk_idx,
            "embed_version": TEXT_EMBED_VERSION,
        }
        for c in chunks
    ]

    vector_store.upsert_document_chunks(user_id, doc_id, vectors, payloads)
    
    # State update happens strictly AFTER successful vector write for crash resilience
    db.set_document_status(
        doc_id,
        "indexed",
        chunk_count=len(chunks),
        title=title,
        progress=1.0,
    )
    print(f"[paper] {doc_id}: Successfully indexed {len(chunks)} chunks in shared text collection.")
    return len(chunks)


@flow(name="ms-ingest-paper", log_prints=True, timeout_seconds=1800)
def ingest_paper(doc_id: str, user_id: str) -> dict[str, Any]:
    """Prefect orchestration flow for academic/technical paper PDF ingestion."""
    attempt = db.bump_document_attempts(doc_id)
    doc_row = db.get_document(doc_id)
    if not doc_row:
        print(f"[paper] No document row found for {doc_id} (skipping stale run)")
        return {"doc_id": doc_id, "status": "skipped"}

    uri = doc_row["uri"]
    title = doc_row.get("title") or Path(uri).stem
    scratch_path: str | None = None

    try:
        scratch_path = t_fetch_paper(doc_id, user_id, uri)
        chunks = t_parse_chunk_paper(doc_id, user_id, scratch_path)
        count = t_embed_index_paper(doc_id, user_id, chunks, title=title)
        return {"doc_id": doc_id, "kind": "paper", "chunks": count, "attempt": attempt}
    except Exception as exc:
        db.set_document_status(doc_id, "failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if scratch_path:
            Path(scratch_path).unlink(missing_ok=True)
