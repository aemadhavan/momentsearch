"""Prefect Cloud trigger layer — the API schedules runs, workers execute them.

Three flows:
- "ms-ingest-video" -> deployment "ms-ingest-video/ingest"
- "ms-ingest-paper" -> deployment "ms-ingest-paper/ingest"
- "ms-ingest-deck"  -> deployment "ms-ingest-deck/ingest"

The API never imports the pipeline or its heavy dependencies (torch, ffmpeg, fitz) —
it schedules a run via Prefect Cloud with timeout=0 so the HTTP request returns in < 300ms.
Workers pick up runs from the queue; retries/backoff live on the flow tasks.
"""
from __future__ import annotations

import logging
from prefect.deployments import run_deployment

logger = logging.getLogger(__name__)

INGEST_VIDEO_DEPLOYMENT = "ms-ingest-video/ingest"
INGEST_PAPER_DEPLOYMENT = "ms-ingest-paper/ingest"
INGEST_DECK_DEPLOYMENT = "ms-ingest-deck/ingest"


def enqueue_video(video_id: str, user_id: str) -> str:
    """Schedule the ingest flow for one video. Returns the Prefect flow-run id."""
    flow_run = run_deployment(
        name=INGEST_VIDEO_DEPLOYMENT,
        parameters={"video_id": video_id, "user_id": user_id},
        timeout=0,  # fire-and-forget: don't block the API waiting for the run
        flow_run_name=f"ingest-video-{video_id}",
    )
    return str(flow_run.id)


def enqueue_document(doc_id: str, user_id: str, kind: str) -> str:
    """Schedule the ingest flow for one paper or deck. Returns the Prefect flow-run id."""
    deployment_name = INGEST_PAPER_DEPLOYMENT if kind == "paper" else INGEST_DECK_DEPLOYMENT
    flow_run = run_deployment(
        name=deployment_name,
        parameters={"doc_id": doc_id, "user_id": user_id},
        timeout=0,  # fire-and-forget: returns in < 300ms
        flow_run_name=f"ingest-{kind}-{doc_id}",
    )
    return str(flow_run.id)
