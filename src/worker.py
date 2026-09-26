"""Ingest worker entrypoint — serves the Prefect flows.

    python -m src.worker

prefect.serve() registers the deployments:
- ms-ingest-video/ingest
- ms-ingest-paper/ingest
- ms-ingest-deck/ingest
in Prefect Cloud (idempotent) and polls for scheduled runs — outbound HTTPS only, no open ports.
Scale horizontally by running more replicas of this process.
"""
import os
import time

from prefect import serve

from .db import init_schema
from .ingest.pipeline import ingest_video
from .ingest.paper import ingest_paper
from .ingest.deck import ingest_deck


def main():
    init_schema()  # make sure migrations ran before consuming runs
    from .rag import vector_store
    vector_store.ensure_collection()  # multimodal/video collection
    vector_store.ensure_text_collection()  # paper & deck text collection

    from . import dispatcher
    dispatcher.start_in_background()
    limit = int(os.getenv("WORKER_CONCURRENCY", "2"))

    d_vid = ingest_video.to_deployment(name="ingest")
    d_pap = ingest_paper.to_deployment(name="ingest")
    d_dck = ingest_deck.to_deployment(name="ingest")

    while True:
        try:
            print(f"[worker] serving deployments: ms-ingest-video/ingest, ms-ingest-paper/ingest, ms-ingest-deck/ingest (concurrency {limit})")
            serve(d_vid, d_pap, d_dck, limit=limit)
            break  # clean shutdown
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(f"[worker] serve crashed: {type(exc).__name__}: {exc} — retrying in 15s")
            time.sleep(15)


if __name__ == "__main__":
    main()
