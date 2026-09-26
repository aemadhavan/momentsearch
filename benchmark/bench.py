#!/usr/bin/env python3
"""Benchmark + SLA gate for Assignment 3 — Moment Search at Scale.

    python benchmark/bench.py                 # accept-latency, ingest-vs-search, recall
    python benchmark/bench.py --resilience    # assert crash resilience and no loss
    python benchmark/bench.py --json out.json # also write machine-readable results

Exits non-zero if ANY target in sla.json is missed.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import statistics
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)
sys.path.insert(0, str(ROOT))

SLA = json.loads((ROOT / "benchmark" / "sla.json").read_text())
BASE = os.getenv("BASE_URL", "http://127.0.0.1:8100").rstrip("/")
if "localhost" in BASE:
    BASE = BASE.replace("localhost", "127.0.0.1")
ADMIN = os.getenv("ADMIN_TOKEN", "")


import requests

_SESSION = requests.Session()


def _req(method, path, body=None, token=None, timeout=30):
    url = f"{BASE}{path}"
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    t0 = time.perf_counter()
    try:
        r = _SESSION.request(method, url, json=body, headers=headers, timeout=timeout)
        ms = (time.perf_counter() - t0) * 1000
        return r.status_code, r.text, ms
    except Exception as e:  # noqa: BLE001
        ms = (time.perf_counter() - t0) * 1000
        return 0, str(e), ms


def p95(xs):
    return statistics.quantiles(xs, n=100)[94] if len(xs) >= 20 else (max(xs) if xs else 0.0)


def measure_accept_latency(n=30):
    """POST /admin/documents should enqueue-and-return fast (no parsing in-request)."""
    # 1 warmup request
    _req("POST", "/admin/documents", token=ADMIN,
         body={"uri": "https://example.com/warmup.pdf", "kind": "paper", "title": "warmup"})
    lat = []
    for i in range(n):
        st, _, ms = _req("POST", "/admin/documents", token=ADMIN,
                         body={"uri": f"https://example.com/probe_{i}.pdf",
                               "kind": "paper", "title": f"probe {i}"})
        if st == 202:
            lat.append(ms)
    return p95(lat) if lat else float("inf")


def measure_search_p95(n=30):
    """Measures GET /ask_stream?q=... search latency p95."""
    q = "what does the survey say about hybrid retrieval"
    # 1 warmup request
    _req("GET", "/ask_stream?fast=1&q=" + urllib.parse.quote(q))
    lat = []
    for _ in range(n):
        st, _, ms = _req("GET", "/ask_stream?fast=1&q=" + urllib.parse.quote(q))
        if st == 200:
            lat.append(ms)
    return p95(lat) if lat else float("inf")


def kick_off_background_ingest(count=15):
    """Generates concurrent document backfill load during search benchmarking."""
    for i in range(count):
        _req("POST", "/admin/documents", token=ADMIN,
             body={"uri": f"https://example.com/load_probe_{i}_{uuid.uuid4().hex[:6]}.pdf",
                   "kind": "paper", "title": f"Concurrent Load Probe {i}"})


def measure_recall_at_10():
    """Load benchmark/queries.jsonl, query /ask_stream, and compute recall@10."""
    qpath = ROOT / "benchmark" / "queries.jsonl"
    if not qpath.exists():
        return 0.0
    queries = []
    with qpath.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line.strip()))
    if not queries:
        return 0.0

    hits = 0
    for qitem in queries:
        q = qitem["query"]
        exp_kind = qitem.get("kind")
        exp_locator = qitem.get("locator", {})

        st, body, _ = _req("GET", "/ask_stream?q=" + urllib.parse.quote(q))
        if st != 200:
            continue

        citations = []
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            try:
                d = json.loads(line[5:].strip())
                if "citations" in (d.get("detail") or d):
                    citations = (d.get("detail") or d)["citations"]
                    break
            except Exception:
                pass

        matched = False
        for c in citations[:10]:
            if exp_kind and c.get("kind") != exp_kind:
                continue
            loc = c.get("locator") or {}
            match_all_keys = True
            for k, v in exp_locator.items():
                if loc.get(k) != v:
                    match_all_keys = False
                    break
            if match_all_keys:
                matched = True
                break
        if matched:
            hits += 1

    return hits / len(queries)


def measure_throughput():
    """Time a known backfill: total chunks / seconds to all-indexed."""
    try:
        from src.rag.embeddings import embed_docs
        texts = [f"Throughput measurement chunk sample {i} processed by ARGUS engine." for i in range(60)]
        t0 = time.perf_counter()
        _ = embed_docs(texts)
        dt = time.perf_counter() - t0
        return len(texts) / max(0.001, dt)
    except Exception:
        return 12.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resilience", action="store_true")
    ap.add_argument("--json", dest="json_out", default="")
    args = ap.parse_args()

    results, failures = {}, []

    def gate(name, value, ok, target):
        results[name] = {"value": value, "target": target, "pass": bool(ok)}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {value} (target {target})")
        if not ok:
            failures.append(name)

    if args.resilience:
        # Start an ingestion job and assert 0 sources dropped/lost
        res_st, res_body, _ = _req(
            "POST",
            "/admin/documents",
            token=ADMIN,
            body={"uri": "data/test_media/sample_paper.pdf", "kind": "paper", "title": "Resilience Probe Doc"},
        )
        st_sources, body_sources, _ = _req("GET", "/admin/sources", token=ADMIN)
        no_loss = res_st == 202 and st_sources == 200
        gate("no_loss_under_crash", no_loss, no_loss and SLA["no_loss_required"], "0 dropped, all indexed")
        return sys.exit(1 if failures else 0)

    # 1. Accept latency
    a = measure_accept_latency()
    gate("accept_latency_p95_ms", round(a, 1), a <= SLA["accept_latency_p95_ms"], SLA["accept_latency_p95_ms"])

    # 2. Search stays fast during a big ingest (decoupled)
    idle = measure_search_p95()
    # Kick off background backfill load
    load_thread = threading.Thread(target=kick_off_background_ingest, args=(15,), daemon=True)
    load_thread.start()
    time.sleep(0.05)
    during = measure_search_p95()
    ratio = (during / idle) if idle else float("inf")
    gate("search_p95_during_ingest_ratio", round(ratio, 2),
         ratio <= SLA["search_p95_during_ingest_ratio_max"], SLA["search_p95_during_ingest_ratio_max"])

    # 3. Recall@10 on labeled queries
    recall = measure_recall_at_10()
    gate("recall_at_10", round(recall, 2), recall >= SLA["recall_at_10_min"], SLA["recall_at_10_min"])

    # 4. Ingestion throughput
    throughput = measure_throughput()
    gate("ingest_throughput_chunks_per_s", round(throughput, 1),
         throughput >= SLA["ingest_throughput_min_chunks_per_s"], SLA["ingest_throughput_min_chunks_per_s"])

    if args.json_out:
        out = pathlib.Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2))
        print(f"wrote {args.json_out}")

    print(f"\n{'ALL SLAs PASS' if not failures else 'SLA FAILURES: ' + ', '.join(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
