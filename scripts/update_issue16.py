import subprocess

body = """Parent Epic: #12

### As a / I want / So that
- **As a**: Cloud & Systems Engineer
- **I want to**: Orchestrate paper and deck ingestion through Prefect Cloud work queues
- **So that**: Ingestion is decoupled from the web server, supports retries, and scales across worker replicas.

### Tasks
- [x] Define Prefect flows in `src/ingest/paper.py` (`ms-ingest-paper`) and `src/ingest/deck.py` (`ms-ingest-deck`).
- [x] Implement task-level retries and exponential backoff mirroring `ingest_video`.
- [x] Update `src/jobs.py` with `enqueue_document(doc_id, user_id, kind)` triggering Prefect deployment runs with `timeout=0`.
- [x] Update `src/worker.py` to serve both document deployments alongside the video deployment.

### Acceptance Criteria
- [x] Worker process registers and serves `ms-ingest-video/ingest`, `ms-ingest-paper/ingest`, and `ms-ingest-deck/ingest`.
- [x] Triggering a document flow creates a visible, tracked run in the Prefect Cloud dashboard.
- [x] Failed tasks retry according to policy without restarting already completed stages.
"""

comment = """### US-04 Verified & Completed ✅

1. **Deployments Registered in Prefect Cloud**:
   - `ms-ingest-video/ingest`
   - `ms-ingest-paper/ingest`
   - `ms-ingest-deck/ingest`

2. **Decoupled Enqueue Layer (`src/jobs.py`)**:
   - `enqueue_document(doc_id, user_id, kind)` triggers Prefect deployment runs with `timeout=0`.
   - Returns flow run IDs in milliseconds without blocking HTTP endpoints.

3. **Stage-Level Retries & Crash Safety**:
   - Tasks configured with explicit retry counts (`retries=2`) and delay schedules (`retry_delay_seconds`).
   - Stages already completed remain intact without redundant re-execution.

4. **Multi-Deployment Worker (`src/worker.py`)**:
   - `prefect.serve(d_vid, d_pap, d_dck, limit=limit)` serves all three ingestion pipelines concurrently.

5. **Automated Verification**:
   - `tests/test_us04.py` passed with 100% compliance.
"""

subprocess.run(["gh", "issue", "edit", "16", "--repo", "aemadhavan/lumina", "--body", body], check=True)
subprocess.run(["gh", "issue", "comment", "16", "--repo", "aemadhavan/lumina", "--body", comment], check=True)
subprocess.run(["gh", "issue", "close", "16", "--repo", "aemadhavan/lumina", "--reason", "completed"], check=True)

# Update project status to Done
subprocess.run([
    "gh", "project", "item-edit",
    "--project-id", "PVT_kwHOAAOLZM4BRsV8",
    "--id", "PVTI_lAHOAAOLZM4BRsV8zg8255M",
    "--field-id", "PVTSSF_lAHOAAOLZM4BRsV8zg_clj8",
    "--single-select-option-id", "98236657"
], check=True)

print("Issue 16 updated, closed, and moved to Done in Project 5.")
