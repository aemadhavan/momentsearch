# Assignment 3 — Moment Search at Scale · Eval Report

Student: Madhavan  ·  Base URL: https://momentsearch-api-production.up.railway.app

| Check | Result | Evidence |
|---|---|---|
| app_up | ✅ pass | GET / -> 200 |
| documents_async | ❌ fail | POST /admin/documents -> 202 in 560ms |
| sources_status | ✅ pass | GET /admin/sources -> 200, kinds=['paper'] |
| paper_indexed | ❌ fail | page-locator citation present: False |
| deck_indexed | ❌ fail | slide-locator citation present: False |
| cross_source | ❌ fail | kinds across answers: [] |
| grounded | ❌ fail | 0 citations, all with text+locator: False |
| decoupled | ❌ fail | run `python benchmark/bench.py` — search p95 during ingest <= 1.3x idle |
| RED_LINE_canary_clean | ✅ pass | clean |

_Manual criteria (resilience, deploy, video demo) graded from your submission._
Run `python benchmark/bench.py --resilience` for the no-loss proof.