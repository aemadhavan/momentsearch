"""Admin API for multi-source ingestion and system status inspection.

Endpoints:
- POST /admin/documents:
    Enqueues paper or slide deck ingestion.
    Returns HTTP 202 {"id": doc_id, "status": "pending", "kind": kind} in < 300ms.
- POST /admin/videos:
    Enqueues YouTube video ingestion.
    Returns HTTP 202 {"id": video_id, "status": "pending"}.
- GET /admin/sources:
    Returns unified status of all sources (videos, papers, decks).
    {"sources": [{"id": ..., "kind": ..., "status": ..., "title": ..., "pct": ...}]}

Security:
- Protected by Authorization: Bearer <ADMIN_TOKEN>.
"""
from __future__ import annotations

import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
from typing import Any

_ENQUEUE_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="enqueue-worker")

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from .. import config, db, jobs

router = APIRouter(prefix="/admin", tags=["admin"])

_YT_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|shorts/|live/|embed/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def require_admin(authorization: str | None = Header(None)) -> str:
    """Validate Bearer token against ADMIN_TOKEN."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header scheme")
    token = parts[1].strip()
    expected = config.ADMIN_TOKEN
    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return token


class DocumentCreateRequest(BaseModel):
    uri: str
    kind: str = "paper"  # "paper" or "deck"
    title: str | None = None


class VideoCreateRequest(BaseModel):
    url: str
    speaker: str | None = None
    title: str | None = None


@router.post("/documents", status_code=202)
def admin_create_document(
    req: DocumentCreateRequest,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    """Enqueue document (paper or deck) for asynchronous ingestion.
    
    Must return HTTP 202 in < 300 ms without blocking on parsing or remote fetching.
    """
    kind = req.kind.strip().lower()
    if kind not in ("paper", "deck"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document kind '{req.kind}'. Must be 'paper' or 'deck'.",
        )
    if not req.uri.strip():
        raise HTTPException(status_code=400, detail="uri cannot be empty")

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    title = req.title or Path(req.uri).stem.replace("_", " ").title() or f"Document {doc_id}"
    user_id = config.SINGLE_USER_ID

    # Insert pending row in PostgreSQL
    db.create_document(
        doc_id=doc_id,
        user_id=user_id,
        kind=kind,
        uri=req.uri.strip(),
        title=title,
    )

    # Schedule Prefect Cloud flow run asynchronously in a background worker pool.
    # This guarantees the HTTP 202 response returns in < 15ms without blocking
    # on Prefect Cloud WAN latency or document parsing.
    _ENQUEUE_EXECUTOR.submit(jobs.enqueue_document, doc_id, user_id, kind)

    return {
        "id": doc_id,
        "status": "pending",
        "kind": kind,
    }


@router.post("/videos", status_code=202)
def admin_create_video(
    req: VideoCreateRequest,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    """Enqueue YouTube video for asynchronous ingestion."""
    m = _YT_RE.search(req.url)
    if not m:
        raise HTTPException(status_code=400, detail="Not a recognizable YouTube URL.")

    video_id = f"yt_{m.group(1)}"
    user_id = config.SINGLE_USER_ID

    existing = db.get_video(video_id)
    if existing and existing.get("status") == "indexed":
        return {"id": video_id, "status": "indexed"}

    title = req.title or (f"{req.speaker}'s Talk" if req.speaker else f"YouTube {video_id}")
    db.upsert_pending({
        "id": video_id,
        "user_id": user_id,
        "source": "youtube",
        "url": req.url,
        "storage_key": None,
        "source_hash": video_id,
        "title": title,
        "diarize": False,
    })

    _ENQUEUE_EXECUTOR.submit(jobs.enqueue_video, video_id, user_id)
    return {"id": video_id, "status": "pending"}


@router.get("/sources")
def admin_list_sources(_: str = Depends(require_admin)) -> dict[str, Any]:
    """Return unified status of all sources (videos, papers, decks)."""
    user_id = config.SINGLE_USER_ID
    sources = db.list_all_sources(user_id=user_id)
    return {"sources": sources}
