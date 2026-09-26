"""Verification test suite for US-02: Structural PDF Paper Ingestion Pipeline."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fitz  # PyMuPDF
from src import config, db
from src.ingest.paper import ingest_paper, t_parse_chunk_paper
from src.rag import vector_store
from src.rag.embeddings import embed_query


def create_sample_pdf(file_path: Path) -> None:
    """Create a 3-page PDF with distinct, verifiable content on each page."""
    doc = fitz.open()
    
    # Page 1: Abstract & Introduction
    page1 = doc.new_page()
    page1.insert_text(
        (50, 72),
        "Title: Retrieval Augmented Generation for Enterprise Search\n\n"
        "Abstract: Retrieval augmented generation combines external knowledge retrieval with "
        "large language model generation to produce grounded and factually accurate responses.\n"
        "Introduction: Traditional knowledge engines rely exclusively on parametric memory. "
        "Enterprise workflows require real-time updates and verifiable source attribution.",
        fontsize=12,
    )
    
    # Page 2: Hybrid Retrieval Architecture
    page2 = doc.new_page()
    page2.insert_text(
        (50, 72),
        "Section 2: Hybrid Retrieval with Dense and Sparse Signals\n\n"
        "Hybrid retrieval fuses dense vector similarity with sparse BM25 keyword matching. "
        "Dense vectors capture high-level conceptual semantics while sparse indices preserve "
        "exact keywords, serial numbers, and specialized technical acronyms.\n"
        "Reciprocal Rank Fusion (RRF) normalizes rank positions across both channels without "
        "requiring fragile score calibration.",
        fontsize=12,
    )
    
    # Page 3: Evaluation and Benchmarks
    page3 = doc.new_page()
    page3.insert_text(
        (50, 72),
        "Section 3: Empirical Benchmarking and SLA Analysis\n\n"
        "Our experiments demonstrate that decoupled queue-based ingestion prevents read starvation. "
        "Under sustained backfill loads, search p95 latency remains within 1.15x of idle latency. "
        "Cross-source recall@10 consistently exceeds 0.78 across heterogeneous multimodal formats.",
        fontsize=12,
    )
    
    doc.save(str(file_path))
    doc.close()


def test_paper_ingestion():
    test_dir = ROOT / "data" / "test_media"
    test_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = test_dir / "sample_rag_survey.pdf"
    create_sample_pdf(pdf_path)
    print(f"[1] Created test PDF at: {pdf_path}")

    # 1. Test parsing & page-aware chunking directly
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    user_id = config.SINGLE_USER_ID
    chunks = t_parse_chunk_paper.fn(doc_id, user_id, str(pdf_path))
    assert len(chunks) >= 3, f"Expected at least 3 chunks (one per page), got {len(chunks)}"
    pages_found = {c.page for c in chunks}
    assert pages_found == {1, 2, 3}, f"Expected pages {1, 2, 3}, found {pages_found}"
    print(f"[2] Page-aware chunking verified: {len(chunks)} chunks with pages {pages_found}")

    # 2. Register document row in database
    db.create_document(
        doc_id=doc_id,
        user_id=user_id,
        kind="paper",
        uri=str(pdf_path),
        title="RAG Survey and Empirical Benchmarks",
    )
    row = db.get_document(doc_id)
    assert row is not None, "Failed to insert document row into DB"
    assert row["status"] == "pending", f"Expected pending status, got {row['status']}"
    print(f"[3] Inserted pending document {doc_id} into Postgres.")

    # 3. Execute ingest_paper flow
    result = ingest_paper.fn(doc_id, user_id)
    print(f"[4] Ingestion flow result: {result}")
    assert result["kind"] == "paper"
    assert result["chunks"] >= 3

    # 4. Check DB status transitioned to indexed
    updated_row = db.get_document(doc_id)
    assert updated_row["status"] == "indexed", f"Expected status 'indexed', got {updated_row['status']}"
    assert updated_row["chunk_count"] == result["chunks"]
    assert updated_row["progress"] == 1.0
    print(f"[5] DB status verified: {updated_row['status']} (chunks: {updated_row['chunk_count']})")

    # 5. Search Qdrant text collection to verify vector retrieval and exact locators
    query_vec = embed_query("how does hybrid retrieval fuse dense and sparse signals")
    hits = vector_store.search_text(query_vec, user_id, top_k=5)
    assert len(hits) > 0, "No hits returned from Qdrant search"
    
    paper_hits = [h for h in hits if h.get("source_id") == doc_id or h.get("doc_id") == doc_id]
    assert len(paper_hits) > 0, "Ingested paper was not retrieved in top search hits"
    
    top_hit = paper_hits[0]
    print(f"[6] Top retrieved paper hit: score={top_hit.get('score'):.4f}, locator={top_hit.get('locator')}")
    assert top_hit.get("kind") == "paper", f"Expected kind 'paper', got {top_hit.get('kind')}"
    assert "locator" in top_hit, "locator missing from payload"
    assert top_hit["locator"].get("page") == 2, f"Expected page 2 for hybrid retrieval query, got {top_hit['locator']}"
    assert "Hybrid retrieval fuses dense vector similarity" in top_hit.get("text", "")
    print(f"[7] Exact page locator verified: Page {top_hit['locator']['page']} matched correctly!")


if __name__ == "__main__":
    test_paper_ingestion()
    print("\nALL US-02 ACCEPTANCE CRITERIA MET!")
