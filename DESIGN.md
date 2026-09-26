# DESIGN.md — ARGUS (Moment Search at Scale)

## 1. Chunking — one strategy per source type, or one for all?

We choose **source-specialized chunking strategies** rather than a single uniform chunker, because a talk, an academic paper, and a presentation deck have fundamentally different semantic and layout structures.
- **Videos**: Retain the existing pipeline’s timed cue grouping bounded by speaker diarization transitions and silence pauses (average 15–30 seconds per segment). The unit is temporal, bounded by `start_ms` and `end_ms`.
- **Papers (PDF)**: Bounded strictly by physical pages and structural section boundaries. We parse using `pymupdf` to extract text blocks with explicit page tracking. Chunks are sized at ~500–800 tokens with an overlap of 100 tokens, but crucially, **chunks never cross page boundaries without explicit assignment to a primary page**. The locator is `{ "page": int }` (1-indexed).
- **Decks (PDF/PPTX)**: A slide is intrinsically an atomic unit of presentation. We treat **one slide as one chunk** (or at most 2–3 sub-chunks if a slide contains extensive tabular data). The chunk text fuses extracted slide body text, title headers, and a vision-generated caption. The locator is `{ "slide": int }` (1-indexed).

**Known failure modes**:
- **Multi-column papers**: Standard text extraction can interleave left and right columns if block reading order detection fails on complex IEEE/ACM formats. We rely on block-level bounding box sorting (`get_text("blocks")`) to traverse column by column.
- **Scanned / OCR-less PDFs**: Papers without an embedded text layer yield zero text; without an expensive OCR fallback in the fast path, these will produce empty chunks unless flagged for offline OCR.
- **Image-only or diagrammatic slides**: A slide containing only an architecture diagram or screenshot with minimal text breaks text chunking completely. We detect low text density (< 20 words) and route the slide image to the vision captioning stage.

---

## 2. Retrieval — how do three source types share one index?

All three modalities land in **a single Qdrant collection** (`momentsearch_text` / unified hybrid collection) using dense embeddings (BGE-small / OpenAI text-embedding-3-small) paired with sparse BM25 payload matching.
- **Unified Ranking**: A user query does not know in advance which medium holds the answer; queries are executed across the full collection without pre-filtering by `kind`. Dense vector search ensures conceptual similarity matches across speech transcripts, paper paragraphs, and slide bullets.
- **Payload Schema**: Every point carries a normalized metadata contract:
  ```json
  {
    "user_id": "...",
    "source_id": "vid_... | doc_...",
    "kind": "video | paper | deck",
    "title": "...",
    "text": "...",
    "locator": {
      "start_ms": 142000, "end_ms": 158000, // if kind == video
      "page": 4,                             // if kind == paper
      "slide": 12                            // if kind == deck
    }
  }
  ```
- **Tie-Breaking & Normalization**: Video spoken text tends to be colloquial and conversational, paper text is dense and technical, and slide text is sparse and terse. Raw cosine similarity can naturally favor dense academic text over brief slide titles. To counter this, we apply **Reciprocal Rank Fusion (RRF)** across dense and sparse retrievals, followed by a light cross-encoder reranker on the top-30 candidates to score semantic relevance independent of raw chunk token length.

---

## 3. Enrichment — what do you spend an LLM call on during ingestion?

LLM calls during ingestion are expensive, slow, and can starve worker queues if overused. We strictly budget LLM enrichment where it creates the highest marginal retrieval lift:
- **Papers**: **Zero LLM enrichment on standard paragraphs.** Academic text is already syntactically dense and self-describing. Spending an LLM call to summarize every page doubles ingestion time with negligible gain in recall@10. We only run an LLM call on the document level once to generate a 3-sentence abstract/summary and domain keywords attached to the root document record.
- **Decks**: **Targeted Vision-LLM captioning on image-heavy slides.** If a slide contains fewer than 25 words or includes visual figures/charts, we render the slide image to JPEG and invoke a lightweight vision model (e.g. Gemini 1.5 Flash or GPT-4o-mini) with a prompt: *"Describe the key message, diagram components, and data points on this slide in two factual sentences."*
- **Unit Economics**: At ~$0.0004 per slide image call, captioning 15 visual slides in a 50-slide deck costs ~$0.006 per deck. For 100 decks, this amounts to $0.60 total. In contrast, blindly running LLM summarization on all 3,000 pages of 100 papers would cost over $15.00 and add 40 minutes of worker wall-clock time.

---

## 4. Grounding — how do you know a citation is real?

Grounding is enforced structurally at the system boundary, not through prompt polite requests:
1. **Immutable Ingestion Provenance**: When `pymupdf` parses page $P$, the integer $P$ is immediately stamped into the chunk's payload dictionary (`locator: {"page": P}`). During slide extraction, the slide index $S$ is stamped as `locator: {"slide": S}`. This payload travels untouched through embedding and Qdrant storage.
2. **Context-Only Synthesis**: The LLM prompt for answer generation receives only the top retrieved contexts, formatted with structured XML blocks containing unambiguous IDs:
   ```xml
   <context id="c1" kind="paper" page="4" source_id="doc_123">
   Hybrid retrieval fuses dense vectors with sparse BM25 indices...
   </context>
   ```
3. **Deterministic Locator Mapping**: The LLM is instructed to cite only `[c1]`, `[c2]`, etc. In the server response handler, the backend regex extracts citation tags and deterministically attaches the exact `locator` from the retrieved `context` object. The LLM never synthesizes or outputs the page number or slide number directly.
4. **Read-Your-Write Probe & Verification**: If retrieval yields 0 hits above the confidence threshold, the endpoint halts immediately and returns an honest empty state citing nothing. No hallucinated citations can pass through.

---

## 5. Cost and caching — what do you cache, and what must never be cached?

- **What We Cache**:
  1. **Source Downloads & Parsed Artifacts**: Downloaded PDFs and slide decks are stored in object storage / local blob cache keyed by SHA-256 of the content. A worker crash or re-index never re-downloads or re-extracts the source.
  2. **Chunk Embeddings**: Embeddings are keyed by `sha256(text + model_version)`. If a document is re-indexed or chunks re-ordered, unchanged text chunks hit the embedding cache.
  3. **Search Results (Short-lived LRU)**: Top-k retrieval results for identical normalized query strings are cached in-memory with a 60-second TTL.
- **What Must NEVER Be Cached**:
  - **Dynamic Ingest Status**: `GET /admin/sources` must always reflect the live Postgres state (`pending`, `embedding`, `indexed`, `pct`).
  - **Long-term Synthesized Answers**: We do not store long-term static question-answer pairs because the corpus is continuously growing. An answer generated when only 1 video was indexed would become stale the moment a relevant paper or deck is ingested.

---

## 6. Trade-offs and what you'd do with another week

### Deliberate Trade-offs Made
1. **Single Collection vs. Isolated Collections**: We chose a single shared Qdrant collection with `kind` metadata rather than separate collections for video, paper, and deck. While separate collections allow modality-specific HNSW tuning, a single collection drastically simplifies cross-source ranking and atomic queries.
2. **Synchronous Slide Rendering vs. Background Async Vision Queue**: We render slide images in the worker thread during deck ingestion rather than splitting vision captioning into an independent sub-queue. This simplifies Prefect flow state management at the cost of slight deck ingestion latency.
3. **No Heavy OCR for Scanned PDFs**: We deliberately chose lightweight `pymupdf` text parsing over running a full Tesseract/PaddleOCR pipeline to guarantee rapid ingestion throughput ($\ge 8\text{ chunks/sec}$) and sub-minute paper indexing.

### Things We Are Unsure About / Below Customer Quality
- **Cross-Modality Score Skew**: Spoken language from video transcripts is often colloquial, repetitive, and verbose, whereas academic papers are dense and terse. In pure cosine distance, dense paper text frequently outscores spoken dialogue. A learned cross-encoder reranker tuned across modalities would be necessary for optimal real-world ranking.
- **Table Structure Parsing**: Complex multi-row/multi-column tables in PDF papers are currently flattened to sequential text blocks, which occasionally loses relational alignment between headers and numbers.

### Next Feature If Given Another Week
- **Visual Bounding-Box Locators for Papers and Slides**: Instead of merely citing `{ "page": 4 }` or `{ "slide": 12 }`, capture the bounding box `[x0, y0, x1, y1]` of the specific paragraph or diagram in the PDF/slide and highlight it in the web viewer in real time.
