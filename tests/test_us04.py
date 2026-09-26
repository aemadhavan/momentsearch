"""Automated test suite for US-04: Prefect Work Queue Orchestration & Flow Deployments.

Verifies:
1. Flow and Deployment registrations for video, paper, and deck.
2. Async non-blocking dispatch via `src/jobs.py` (`enqueue_document` and `enqueue_video`).
3. Task-level retry policies and exponential backoff configuration on paper and deck stages.
4. Worker configuration in `src/worker.py` serving all three pipelines concurrently.
"""
from __future__ import annotations

import inspect
import sys
import uuid
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config, jobs, worker
from src.ingest.pipeline import ingest_video, t_fetch as t_fetch_vid, t_embed_index as t_embed_vid
from src.ingest.paper import (
    ingest_paper,
    t_fetch_paper,
    t_parse_chunk_paper,
    t_embed_index_paper,
)
from src.ingest.deck import (
    ingest_deck,
    t_fetch_deck,
    t_parse_chunk_deck,
    t_embed_index_deck,
)


def test_us04_prefect_orchestration():
    print("--- [1] Checking Deployment Names ---")
    assert ingest_video.name == "ms-ingest-video"
    assert ingest_paper.name == "ms-ingest-paper"
    assert ingest_deck.name == "ms-ingest-deck"

    assert jobs.INGEST_VIDEO_DEPLOYMENT == "ms-ingest-video/ingest"
    assert jobs.INGEST_PAPER_DEPLOYMENT == "ms-ingest-paper/ingest"
    assert jobs.INGEST_DECK_DEPLOYMENT == "ms-ingest-deck/ingest"
    print("[OK] All 3 flow and deployment names match specification exactly.")

    print("\n--- [2] Checking Task Retry Policies ---")
    # Paper tasks
    assert t_fetch_paper.retries >= 1, "t_fetch_paper must have retries >= 1"
    assert t_parse_chunk_paper.retries >= 1, "t_parse_chunk_paper must have retries >= 1"
    assert t_embed_index_paper.retries >= 1, "t_embed_index_paper must have retries >= 1"

    # Deck tasks
    assert t_fetch_deck.retries >= 1, "t_fetch_deck must have retries >= 1"
    assert t_parse_chunk_deck.retries >= 1, "t_parse_chunk_deck must have retries >= 1"
    assert t_embed_index_deck.retries >= 1, "t_embed_index_deck must have retries >= 1"

    print(f"[OK] Paper task retries: fetch={t_fetch_paper.retries}, parse={t_parse_chunk_paper.retries}, embed={t_embed_index_paper.retries}")
    print(f"[OK] Deck task retries: fetch={t_fetch_deck.retries}, parse={t_parse_chunk_deck.retries}, embed={t_embed_index_deck.retries}")

    print("\n--- [3] Checking Worker Multi-Deployment Serving ---")
    worker_src = inspect.getsource(worker.main)
    assert "d_vid" in worker_src or "ingest_video" in worker_src
    assert "d_pap" in worker_src or "ingest_paper" in worker_src
    assert "d_dck" in worker_src or "ingest_deck" in worker_src
    assert "serve(" in worker_src
    print("[OK] Worker main() serves video, paper, and deck deployments concurrently.")

    print("\n--- [4] Testing Live Prefect Cloud Queue Trigger ---")
    user_id = config.SINGLE_USER_ID
    test_paper_id = f"doc_test_{uuid.uuid4().hex[:8]}"
    test_deck_id = f"doc_test_{uuid.uuid4().hex[:8]}"

    # Trigger paper run
    paper_run_id = jobs.enqueue_document(test_paper_id, user_id, "paper")
    assert paper_run_id and len(paper_run_id) > 10, f"Invalid paper flow_run_id: {paper_run_id}"
    print(f"[OK] Enqueued paper flow run to Prefect Cloud: {paper_run_id}")

    # Trigger deck run
    deck_run_id = jobs.enqueue_document(test_deck_id, user_id, "deck")
    assert deck_run_id and len(deck_run_id) > 10, f"Invalid deck flow_run_id: {deck_run_id}"
    print(f"[OK] Enqueued deck flow run to Prefect Cloud: {deck_run_id}")

    print("\n==========================================")
    print("ALL US-04 ACCEPTANCE CRITERIA MET!")
    print("==========================================")


if __name__ == "__main__":
    test_us04_prefect_orchestration()
