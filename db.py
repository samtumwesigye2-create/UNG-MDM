from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DATABASE_URL = os.environ.get("UNG_MDM_DATABASE_URL", "").strip()
BASE = Path(__file__).resolve().parent
SQLITE_PATH = Path(os.environ.get("UNG_MDM_DB", str(BASE / "ung_mdm.db")))


def is_postgres() -> bool:
    return DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")


def connect():
    if is_postgres():
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)
    conn = sqlite3.connect(SQLITE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def sql(query: str) -> str:
    return query.replace("?", "%s") if is_postgres() else query


def database_name() -> str:
    return "postgresql" if is_postgres() else "sqlite"
