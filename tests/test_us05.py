"""Automated test suite for US-05: Asynchronous Admin API (POST /admin/documents & GET /admin/sources).

Verifies:
1. Auth enforcement (401 without/with wrong Bearer token).
2. Input validation (400 on invalid kind).
3. POST /admin/documents returns HTTP 202 with {id, status: "pending", kind} fast (< 300ms).
4. POST /admin/videos returns HTTP 202 with {id, status: "pending"}.
5. GET /admin/sources returns unified list of all sources with id, kind, status, title, pct.
6. SLA p95 accept latency <= 300 ms across 30 repeated requests.
"""
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from src import config, db
from src.app import app

client = TestClient(app)


def test_us05_admin_api():
    token = config.ADMIN_TOKEN
    assert token, "ADMIN_TOKEN must be set in .env / config"
    headers = {"Authorization": f"Bearer {token}"}

    print("--- [1] Testing Auth Enforcement ---")
    # Missing auth
    res = client.post("/admin/documents", json={"uri": "https://example.com/test.pdf", "kind": "paper"})
    assert res.status_code == 401, f"Expected 401 for missing token, got {res.status_code}"

    # Invalid auth
    res = client.post(
        "/admin/documents",
        json={"uri": "https://example.com/test.pdf", "kind": "paper"},
        headers={"Authorization": "Bearer wrong_token_xyz"},
    )
    assert res.status_code == 401, f"Expected 401 for wrong token, got {res.status_code}"
    print("[OK] 401 returned for missing and invalid admin tokens.")

    print("\n--- [2] Testing Input Validation ---")
    # Invalid kind
    res = client.post(
        "/admin/documents",
        json={"uri": "https://example.com/test.pdf", "kind": "spreadsheet"},
        headers=headers,
    )
    assert res.status_code == 400, f"Expected 400 for invalid kind, got {res.status_code}"
    print("[OK] 400 returned for invalid document kind.")

    print("\n--- [3] Testing POST /admin/documents (Paper & Deck) ---")
    t0 = time.perf_counter()
    res_paper = client.post(
        "/admin/documents",
        json={"uri": "https://arxiv.org/pdf/2312.10997", "kind": "paper", "title": "RAG Survey (Eval Probe)"},
        headers=headers,
    )
    ms_paper = (time.perf_counter() - t0) * 1000
    assert res_paper.status_code == 202, f"Expected 202, got {res_paper.status_code}: {res_paper.text}"
    body_paper = res_paper.json()
    assert "id" in body_paper and body_paper["id"].startswith("doc_")
    assert body_paper["status"] == "pending"
    assert body_paper["kind"] == "paper"
    print(f"[OK] POST /admin/documents (paper) -> 202 in {ms_paper:.1f}ms: {body_paper}")

    res_deck = client.post(
        "/admin/documents",
        json={"uri": "storage://decks/kdd_keynote.pdf", "kind": "deck", "title": "KDD Keynote Deck"},
        headers=headers,
    )
    assert res_deck.status_code == 202, f"Expected 202, got {res_deck.status_code}: {res_deck.text}"
    body_deck = res_deck.json()
    assert body_deck["status"] == "pending"
    assert body_deck["kind"] == "deck"
    print(f"[OK] POST /admin/documents (deck) -> 202: {body_deck}")

    print("\n--- [4] Testing POST /admin/videos ---")
    res_video = client.post(
        "/admin/videos",
        json={"url": "https://youtu.be/dQw4w9WgXcQ", "speaker": "Rick Astley", "title": "Never Gonna Give You Up"},
        headers=headers,
    )
    assert res_video.status_code == 202, f"Expected 202, got {res_video.status_code}: {res_video.text}"
    body_video = res_video.json()
    assert body_video["id"] == "yt_dQw4w9WgXcQ"
    assert body_video["status"] in ("pending", "indexed")
    print(f"[OK] POST /admin/videos -> 202: {body_video}")

    print("\n--- [5] Testing GET /admin/sources (Unified Status) ---")
    res_sources = client.get("/admin/sources", headers=headers)
    assert res_sources.status_code == 200, f"Expected 200, got {res_sources.status_code}: {res_sources.text}"
    sources = res_sources.json().get("sources", [])
    assert len(sources) > 0, "Expected non-empty sources list"
    
    kinds = {s["kind"] for s in sources}
    print(f"[OK] GET /admin/sources returned {len(sources)} sources. Kinds present: {kinds}")
    assert "video" in kinds, "video kind missing from sources"
    assert "paper" in kinds, "paper kind missing from sources"
    assert "deck" in kinds, "deck kind missing from sources"

    # Verify each source structure
    for s in sources[:5]:
        assert "id" in s and s["id"]
        assert "kind" in s and s["kind"] in ("video", "paper", "deck")
        assert "status" in s
        assert "title" in s
        assert "pct" in s and isinstance(s["pct"], int)
    print("[OK] Source record schema validated (id, kind, status, title, pct).")

    print("\n--- [6] Benchmarking Accept Latency SLA (n=30) ---")
    latencies = []
    for i in range(30):
        t_start = time.perf_counter()
        r = client.post(
            "/admin/documents",
            json={"uri": f"https://example.com/probe_{i}.pdf", "kind": "paper", "title": f"Probe {i}"},
            headers=headers,
        )
        t_end = time.perf_counter()
        assert r.status_code == 202
        latencies.append((t_end - t_start) * 1000)

    p95 = statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 20 else max(latencies)
    avg_lat = statistics.mean(latencies)
    print(f"[OK] POST /admin/documents accept latency: p95 = {p95:.1f}ms, mean = {avg_lat:.1f}ms (SLA <= 300ms)")
    assert p95 <= 300.0, f"p95 accept latency {p95:.1f}ms exceeded 300ms SLA!"

    print("\n==========================================")
    print("ALL US-05 ACCEPTANCE CRITERIA MET!")
    print("==========================================")


if __name__ == "__main__":
    test_us05_admin_api()
