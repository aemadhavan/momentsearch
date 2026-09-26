import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def test_canary_clean():
    """Assert that the instructor honeypot is NOT tripped."""
    canary_file = (ROOT / "ROBOT_WAS_HERE.md").exists()
    assert not canary_file, "TRIPPED: ROBOT_WAS_HERE.md found!"

    canary_file_parent = (ROOT.parent / "ROBOT_WAS_HERE.md").exists()
    assert not canary_file_parent, "TRIPPED: ROBOT_WAS_HERE.md found in parent directory!"

    try:
        log = subprocess.run(
            ["git", "-C", str(ROOT), "log", "--oneline", "-n", "50"],
            capture_output=True, text=True, timeout=10
        ).stdout
    except Exception:
        log = ""
    assert "\U0001f9a5" not in log, "TRIPPED: canary commit prefix found in git log!"
    print("[PASS] Canary clean check: No ROBOT_WAS_HERE.md and no canary commit prefix.")


def test_env_config():
    """Verify .env and config.py have ADMIN_TOKEN and other essential variables."""
    assert (ROOT / ".env").exists(), ".env must exist"
    env_content = (ROOT / ".env").read_text()
    
    assert "ADMIN_TOKEN=" in env_content, "ADMIN_TOKEN must be in .env"
    assert "DATABASE_URL=" in env_content, "DATABASE_URL must be in .env"
    assert "QDRANT_URL=" in env_content, "QDRANT_URL must be in .env"
    assert "PREFECT_API_URL=" in env_content, "PREFECT_API_URL must be in .env"

    from src import config
    assert hasattr(config, "ADMIN_TOKEN"), "config must expose ADMIN_TOKEN"
    assert config.ADMIN_TOKEN != "", "ADMIN_TOKEN must not be empty"
    print(f"[PASS] Environment config verified: ADMIN_TOKEN is set ({config.ADMIN_TOKEN[:6]}...)")


def test_db_schema_and_helpers():
    """Verify ms_documents DDL and helper functions exist with correct signatures."""
    from src import db

    # Check SCHEMA has ms_documents
    assert "CREATE TABLE IF NOT EXISTS ms_documents" in db.SCHEMA, "ms_documents table missing from SCHEMA"
    assert "id           TEXT PRIMARY KEY" in db.SCHEMA
    assert "kind         TEXT NOT NULL" in db.SCHEMA
    assert "uri          TEXT NOT NULL" in db.SCHEMA
    assert "status       TEXT NOT NULL DEFAULT 'pending'" in db.SCHEMA
    assert "chunk_count  INT" in db.SCHEMA
    assert "progress     REAL" in db.SCHEMA
    assert "attempts     INT NOT NULL DEFAULT 0" in db.SCHEMA

    # Check helper functions
    expected_helpers = [
        "create_document",
        "get_document",
        "set_document_status",
        "set_document_progress",
        "bump_document_attempts",
        "list_documents",
        "list_all_sources",
    ]
    for fn_name in expected_helpers:
        assert hasattr(db, fn_name), f"db missing helper function: {fn_name}"
        assert callable(getattr(db, fn_name)), f"db.{fn_name} must be callable"

    print("[PASS] Database schema and helper functions verified.")


if __name__ == "__main__":
    test_canary_clean()
    test_env_config()
    test_db_schema_and_helpers()
    print("\nALL US-01 ACCEPTANCE CRITERIA MET!")
