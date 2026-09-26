import subprocess

body = """Parent Epic: #12

### As a / I want / So that
- **As a**: Knowledge Worker
- **I want to**: Ingest presentation slide decks (PDF / PPTX) with slide segmentation and visual captioning
- **So that**: Visual diagrams and concise slide bullets are indexed with verifiable slide locators.

### Tasks
- [x] Implement `src/ingest/deck.py` supporting slide extraction from PDF/PPTX presentations.
- [x] Extract raw text, titles, and layout from each slide.
- [x] Implement targeted vision-LLM captioning on visual/diagram-heavy slides (slides with low text density).
- [x] Format slide chunk payload with `kind: "deck"` and `locator: {"slide": S}`.
- [x] Upsert slide vectors into the single shared Qdrant text collection.

### Acceptance Criteria
- [x] Multi-slide decks are parsed into discrete slide chunks.
- [x] Visual diagrams produce meaningful descriptive captions incorporated into search embeddings.
- [x] Each indexed slide chunk carries exact `locator: {"slide": S}`.
"""

comment = """### US-03 Verified & Completed ✅

1. **Slide Extraction**:
   - Implemented `src/ingest/deck.py` with multi-page PDF rendering via PyMuPDF and native PPTX extraction via `python-pptx`.
   - Segments presentations into 1-indexed slide units (`locator: {"slide": S}`).

2. **Visual LLM Captioning**:
   - Integrated vision LLM (`gemini-2.5-flash` / OpenAI vision compatible fallback) to inspect diagram/flowchart slides and synthesize high-density captions.

3. **Shared Text Qdrant Collection**:
   - Indexed slide chunks with `kind: "deck"` and slide locator into the shared Qdrant collection.

4. **Automated Verification**:
   - `tests/test_us03.py` passed with 100% compliance.
   - Exact locator `{"slide": 2}` retrieved for cross-source slide query.
"""

subprocess.run(["gh", "issue", "edit", "15", "--repo", "aemadhavan/lumina", "--body", body], check=True)
subprocess.run(["gh", "issue", "comment", "15", "--repo", "aemadhavan/lumina", "--body", comment], check=True)
subprocess.run(["gh", "issue", "close", "15", "--repo", "aemadhavan/lumina", "--reason", "completed"], check=True)
print("Issue 15 updated and closed.")
