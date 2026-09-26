import subprocess

body = """Parent Epic: #12

### As a / I want / So that
- **As a**: End User
- **I want to**: Query the system via SSE streaming endpoint `GET /ask_stream?q=...`
- **So that**: I receive an answer citing multiple modalities (video moment, paper page, slide) grounded in retrieved passages.

### Tasks
- [x] Implement `GET /ask_stream` endpoint supporting Server-Sent Events (SSE) as specified in `TECHNICAL.md`.
- [x] Query the single shared Qdrant collection across all source modalities without pre-filtering.
- [x] Structure the SSE event stream: emit trace, then `citations` event, followed by streamed answer tokens and completion.
- [x] Enforce deterministic locator mapping: ensure citations contain exact locators:
  - Video: `locator: {"start_ms": int, "end_ms": int}`
  - Paper: `locator: {"page": int}`
  - Deck: `locator: {"slide": int}`
- [x] Guarantee grounded synthesis: every citation refers strictly to a retrieved passage; empty retrieval yields empty citations.

### Acceptance Criteria
- [x] `GET /ask_stream?q=...` returns valid SSE events.
- [x] Citations include proper `kind` and exact `locator` payloads.
- [x] Single cross-domain query successfully cites at least two different modalities (e.g. video + paper/deck).
- [x] Zero hallucinated page numbers, slides, or timestamps.
"""

comment = """### US-06 Verified & Completed ✅

1. **Cross-Source Hybrid Retrieval (`src/rag/cross_search.py`)**:
   - Queries the single shared Qdrant collection across all modalities (video moments, paper pages, presentation slides).
   - Normalized citation schema carrying deterministic locators:
     - Paper: `locator: {"page": P}` (1-indexed page)
     - Deck: `locator: {"slide": S}` (1-indexed slide)
     - Video: `locator: {"start_ms": M1, "end_ms": M2}`

2. **Server-Sent Events (`GET /ask_stream?q=...`)**:
   - Streams trace stages (`embedding` -> `searching`), followed by the `citations` event, streamed answer `token` events, and terminal `done` event.

3. **Grounded Synthesis**:
   - Synthesizes factual answers citing `[1]`, `[2]`, strictly grounded in retrieved evidence with zero hallucinated locators.

4. **Automated Verification**:
   - `tests/test_us06.py` passed with 100% compliance:
     - Exact page locator verified for paper queries (`{"page": 2}`).
     - Exact slide locator verified for deck queries (`{"slide": 2}`).
     - Multi-modality representation confirmed.
"""

subprocess.run(["gh", "issue", "edit", "18", "--repo", "aemadhavan/lumina", "--body", body], check=True)
subprocess.run(["gh", "issue", "comment", "18", "--repo", "aemadhavan/lumina", "--body", comment], check=True)
subprocess.run(["gh", "issue", "close", "18", "--repo", "aemadhavan/lumina", "--reason", "completed"], check=True)

# Update project status to Done
subprocess.run([
    "gh", "project", "item-edit",
    "--project-id", "PVT_kwHOAAOLZM4BRsV8",
    "--id", "PVTI_lAHOAAOLZM4BRsV8zg825_c",
    "--field-id", "PVTSSF_lAHOAAOLZM4BRsV8zg_clj8",
    "--single-select-option-id", "98236657"
], check=True)

print("Issue 18 updated, closed, and moved to Done in Project 5.")
