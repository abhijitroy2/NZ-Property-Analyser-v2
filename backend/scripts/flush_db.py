#!/usr/bin/env python3
"""Flush all data from the database. Use when starting fresh with tests."""
import sys
from pathlib import Path

# Ensure backend app is on path when run from project root or backend/
backend = Path(__file__).resolve().parent.parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

from app.database import flush_db

if __name__ == "__main__":
    flush_db()
    print("Database flushed. All tables are now empty.")
