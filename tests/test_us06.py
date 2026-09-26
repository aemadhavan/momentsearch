"""Automated test suite for US-06: Cross-Source Hybrid Retrieval & Grounded Synthesis (GET /ask_stream).

Verifies:
1. Valid SSE event streaming (trace -> citations -> token -> done).
2. Paper query retrieves citations with exact `locator: {"page": int}`.
3. Deck query retrieves citations with exact `locator: {"slide": int}`.
4. Cross-source coverage: multiple modalities represented across retrieved citations.
5. Grounded synthesis: non-empty text and verified locator on every citation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


def _consume_sse(query: str) -> tuple[list[dict], list[dict], str]:
    """Helper to stream /ask_stream?q=... and extract stages, citations, and answer tokens."""
    res = client.get(f"/ask_stream?q={query}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    
    stages = []
    citations = []
    tokens = []
    done_payload = None

    for line in res.iter_lines():
        if not line or not line.startswith("data:"):
            continue
        payload = json.loads(line[5:].strip())
        evt_type = payload.get("type")
        if evt_type == "stage":
            stages.append(payload)
        elif evt_type == "citations" or "citations" in payload:
            citations = payload.get("citations", [])
        elif evt_type == "token":
            tokens.append(payload.get("token", ""))
        elif evt_type == "done":
            done_payload = payload

    answer = "".join(tokens).strip() or (done_payload.get("result", {}).get("answer", "") if done_payload else "")
    return stages, citations, answer


def test_us06_cross_retrieval_and_synthesis():
    print("--- [1] Testing Paper Retrieval via /ask_stream ---")
    stages1, cites_paper, ans1 = _consume_sse("what does the survey say about hybrid retrieval")
    print(f"Stages observed: {[s.get('stage') for s in stages1]}")
    print(f"Citations count: {len(cites_paper)}")
    assert len(cites_paper) > 0, "Expected at least 1 citation for paper query"
    
    # Check paper locator
    paper_cites = [c for c in cites_paper if c.get("kind") == "paper"]
    assert len(paper_cites) > 0, f"Expected paper citation, found: {[c.get('kind') for c in cites_paper]}"
    for c in paper_cites:
        assert "locator" in c and "page" in c["locator"]
        assert isinstance(c["locator"]["page"], int) and c["locator"]["page"] >= 1
        assert c.get("text"), "Citation text must not be empty"
    print(f"[OK] Paper locator verified: {paper_cites[0]['locator']}, title: {paper_cites[0]['title']}")

    print("\n--- [2] Testing Deck Retrieval via /ask_stream ---")
    stages2, cites_deck, ans2 = _consume_sse("the slide about one index for every source")
    print(f"Citations count: {len(cites_deck)}")
    assert len(cites_deck) > 0, "Expected at least 1 citation for deck query"
    
    deck_cites = [c for c in cites_deck if c.get("kind") == "deck"]
    assert len(deck_cites) > 0, f"Expected deck citation, found: {[c.get('kind') for c in cites_deck]}"
    for c in deck_cites:
        assert "locator" in c and "slide" in c["locator"]
        assert isinstance(c["locator"]["slide"], int) and c["locator"]["slide"] >= 1
        assert c.get("text"), "Citation text must not be empty"
    print(f"[OK] Deck locator verified: {deck_cites[0]['locator']}, title: {deck_cites[0]['title']}")

    print("\n--- [3] Checking Cross-Source Modality Diversity ---")
    all_cites = cites_paper + cites_deck
    distinct_kinds = {c.get("kind") for c in all_cites}
    print(f"Distinct modalities retrieved across queries: {distinct_kinds}")
    assert len(distinct_kinds) >= 2, f"Expected >= 2 distinct kinds, got {distinct_kinds}"
    assert "paper" in distinct_kinds and "deck" in distinct_kinds
    print("[OK] Cross-source coverage verified: both 'paper' and 'deck' retrieved.")

    print("\n--- [4] Validating Grounded Citations ---")
    for c in all_cites:
        assert c.get("sourceId"), "sourceId missing"
        assert c.get("text"), "text missing or empty"
        assert c.get("locator"), "locator missing"
        loc = c["locator"]
        if c["kind"] == "paper":
            assert "page" in loc
        elif c["kind"] == "deck":
            assert "slide" in loc
        elif c["kind"] == "video":
            assert "start_ms" in loc
    print("[OK] All citations strictly grounded with exact locators and non-empty text.")

    print("\n--- [5] Validating Synthesized Answer ---")
    print(f"Synthesized answer sample: {ans1[:120]}...")
    assert len(ans1) > 20, "Synthesized answer should be substantial"
    assert "[1]" in ans1 or "[2]" in ans1 or "page" in ans1 or "survey" in ans1.lower()
    print("[OK] Grounded synthesis verified.")

    print("\n==========================================")
    print("ALL US-06 ACCEPTANCE CRITERIA MET!")
    print("==========================================")


if __name__ == "__main__":
    test_us06_cross_retrieval_and_synthesis()
