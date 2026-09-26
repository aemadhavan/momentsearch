from pathlib import Path
import sys, os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from src import setup_check, config

def main():
    print("=== CONFIGURATION CHECK ===")
    print("DATABASE_URL:", config.DATABASE_URL)
    print("QDRANT_URL:", config.QDRANT_URL)
    print("PREFECT_API_URL:", os.getenv("PREFECT_API_URL") or "(NOT SET)")
    print("PREFECT_API_KEY:", "SET" if os.getenv("PREFECT_API_KEY") else "(NOT SET)")
    print("LLM_API_KEY:", "SET" if config.LLM_API_KEY else "(NOT SET)")
    print("GEMINI_API_KEY:", "SET" if config.GEMINI_API_KEY else "(NOT SET)")
    print("ADMIN_TOKEN:", "SET" if config.ADMIN_TOKEN else "(NOT SET)")
    print("STORAGE_PROVIDER:", config.STORAGE_PROVIDER)

    print("\n=== SETUP READINESS REPORT ===")
    rep = setup_check.report()
    print("Ready:", rep["ready"])
    for issue in rep["issues"]:
        lvl = issue["level"].upper()
        feat = issue["feature"]
        fix = issue["fix"]
        env_vars = ", ".join(issue["env"])
        print(f"[{lvl}] {feat}: {fix} ({env_vars})")

if __name__ == "__main__":
    main()
