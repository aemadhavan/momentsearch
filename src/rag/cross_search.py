"""Cross-source hybrid retrieval and grounded synthesis engine.

Unified search across all modalities:
- Video moments (timestamps: {"start_ms": M1, "end_ms": M2})
- Research papers (pages: {"page": P})
- Presentation decks (slides: {"slide": S})

Provides:
- cross_retrieve(): Unified multi-source candidate retrieval with exact locators
- synthesize_grounded_answer(): Multi-citation answer generation citing [1], [2]
- stream_ask_cross(): Server-Sent Events (SSE) generator for GET /ask_stream
"""
from __future__ import annotations

import json
import logging
from typing import Any, Generator

from .. import config, llm
from . import vector_store
from .embeddings import embed_query, embed_text

logger = logging.getLogger(__name__)


def _format_citation(h: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw Qdrant point payload into standard Citation schema."""
    kind = h.get("kind")
    if not kind:
        if "page" in h:
            kind = "paper"
        elif "slide" in h:
            kind = "deck"
        else:
            kind = "video"

    source_id = h.get("source_id") or h.get("doc_id") or h.get("video_id") or "unknown_src"
    
    # Determine exact locator according to contract
    locator = h.get("locator")
    if not locator or not isinstance(locator, dict):
        if kind == "paper":
            locator = {"page": int(h.get("page", 1))}
        elif kind == "deck":
            locator = {"slide": int(h.get("slide", 1))}
        else:
            # video
            start_ms = int(h.get("start_ms", h.get("ms", 0)))
            end_ms = int(h.get("end_ms", start_ms + 15000))
            locator = {"start_ms": start_ms, "end_ms": end_ms}
    else:
        # Guarantee types
        if "page" in locator:
            locator = {"page": int(locator["page"])}
        elif "slide" in locator:
            locator = {"slide": int(locator["slide"])}
        elif "start_ms" in locator:
            locator = {
                "start_ms": int(locator["start_ms"]),
                "end_ms": int(locator.get("end_ms", int(locator["start_ms"]) + 15000)),
            }

    raw_text = (h.get("text") or "").strip()
    if not raw_text and kind == "video":
        ms = h.get("ms", 0)
        raw_text = f"Video moment at {ms // 1000}s"

    title = h.get("title") or source_id
    score = float(h.get("score", 0.0))

    cit: dict[str, Any] = {
        "sourceId": source_id,
        "kind": kind,
        "locator": locator,
        "text": raw_text,
        "title": title,
        "score": round(score, 4),
    }
    if h.get("speaker"):
        cit["speaker"] = h["speaker"]

    return cit


def cross_retrieve(query: str, user_id: str, top_k: int = 6) -> list[dict[str, Any]]:
    """Retrieve top candidates across videos, papers, and slide decks from shared Qdrant indexes."""
    query = query.strip()
    if not query:
        return []

    # 1. Search dense text collection (papers, decks, video transcripts)
    text_hits: list[dict[str, Any]] = []
    try:
        q_vec = embed_query(query)
        text_hits = vector_store.search_text(q_vec, user_id, top_k=top_k * 2)
    except Exception as exc:
        logger.warning(f"[cross_retrieve] text search warning: {exc}")

    # 2. Search visual collection (video frames)
    visual_hits: list[dict[str, Any]] = []
    try:
        clip_vec = embed_text(query)
        visual_hits = vector_store.search(clip_vec, user_id, top_k=top_k)
    except Exception as exc:
        logger.debug(f"[cross_retrieve] visual search warning: {exc}")

    all_raw = text_hits + visual_hits
    if not all_raw:
        return []

    # Format all hits
    formatted = [_format_citation(h) for h in all_raw if h.get("text") or h.get("ms") is not None]

    # Deduplicate by (sourceId, locator) preserving highest score
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    
    # Sort primarily by score descending
    formatted.sort(key=lambda x: x["score"], reverse=True)

    for item in formatted:
        loc_key = json.dumps(item["locator"], sort_keys=True)
        key = f"{item['sourceId']}:{loc_key}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= top_k:
            break

    return deduped


def synthesize_answer(query: str, citations: list[dict[str, Any]], user_id: str, fast: bool = False) -> str:
    """Produce grounded multi-source synthesis citing [1], [2], etc."""
    if not citations:
        return "I couldn't find anything matching your query in the indexed videos, papers, or decks."

    cfg = llm.env_config()
    if not fast and cfg is not None and (cfg.api_key or cfg.base_url):
        # Build prompt for LLM
        prompt_lines = [
            f"Question: {query}",
            "",
            "Answer the question directly and factually using ONLY the evidence in the citations below.",
            "Cite each supporting claim using [1], [2], etc. matching the citation numbers.",
            "Do not hallucinate any facts not present in the citations.",
            "",
            "Citations:",
        ]
        for i, c in enumerate(citations, 1):
            kind = c["kind"].upper()
            title = c["title"]
            loc = c["locator"]
            text = c["text"]
            prompt_lines.append(f"[{i}] ({kind}: {title} | locator: {loc})\n{text}\n")

        prompt = "\n".join(prompt_lines)
        system_prompt = "You are an expert multimodal AI assistant answering questions grounded strictly in the provided retrieved citations."
        try:
            return llm.complete(cfg, system_prompt, prompt).strip()
        except Exception as exc:
            logger.warning(f"[synthesize_answer] LLM completion failed ({exc}), falling back to deterministic synthesis.")

    # Deterministic grounded synthesis fallback
    lines = [f"Based on the indexed sources for '{query}':\n"]
    for i, c in enumerate(citations[:4], 1):
        k = c["kind"]
        loc_desc = ""
        if "page" in c["locator"]:
            loc_desc = f"page {c['locator']['page']}"
        elif "slide" in c["locator"]:
            loc_desc = f"slide {c['locator']['slide']}"
        elif "start_ms" in c["locator"]:
            secs = c["locator"]["start_ms"] // 1000
            loc_desc = f"timestamp {secs // 60:02d}:{secs % 60:02d}"

        body = c["text"].strip().replace("\n", " ")
        if len(body) > 200:
            body = body[:197] + "..."
        lines.append(f"[{i}] {c['title']} ({loc_desc}): {body}")

    return "\n\n".join(lines)


def stream_ask_cross(query: str, user_id: str, fast: bool = False) -> Generator[str, None, None]:
    """Generate Server-Sent Events (SSE) stream for GET /ask_stream."""
    # 1. Trace: Embedding
    yield "data: " + json.dumps({
        "type": "stage",
        "stage": "embedding",
        "detail": "Generating dense semantic embeddings",
    }) + "\n\n"

    # 2. Retrieval
    citations = cross_retrieve(query, user_id, top_k=6)

    # 3. Trace: Searching
    yield "data: " + json.dumps({
        "type": "stage",
        "stage": "searching",
        "detail": f"Retrieved {len(citations)} cross-source candidates",
    }) + "\n\n"

    # 4. Citations event (parsed by eval.py and UI)
    yield "data: " + json.dumps({
        "type": "citations",
        "citations": citations,
    }) + "\n\n"

    # 5. Synthesize answer
    answer = synthesize_answer(query, citations, user_id, fast=fast)

    # 6. Stream tokens
    words = answer.split(" ")
    for i in range(0, len(words), 3):
        chunk = " ".join(words[i:i + 3]) + " "
        yield "data: " + json.dumps({
            "type": "token",
            "token": chunk,
        }) + "\n\n"

    # 7. Done event
    yield "data: " + json.dumps({
        "type": "done",
        "result": {
            "answer": answer,
            "citations": citations,
        },
    }) + "\n\n"
