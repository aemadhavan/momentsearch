import psycopg
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import SCHEMA

def main():
    conn = psycopg.connect("postgresql://ms:ms@localhost:5433/ms")
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
        conn.commit()
        
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
        tables = [t[0] for t in cur.fetchall()]
        print("Successfully Initialized Postgres!")
        print("Tables in Database:", tables)
        
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'ms_documents' ORDER BY ordinal_position;")
        cols = cur.fetchall()
        print("\nColumns in ms_documents:")
        for name, dtype in cols:
            print(f"  - {name} ({dtype})")

if __name__ == "__main__":
    main()
