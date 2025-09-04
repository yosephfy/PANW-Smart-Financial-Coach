import os
import sqlite3
from pathlib import Path


def _repo_root() -> Path:
    # services/api/app -> parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def get_db_path() -> Path:
    env_path = os.getenv("DB_PATH")
    if env_path:
        return Path(env_path)
    return _repo_root() / "db" / "dev.db"


def get_schema_path() -> Path:
    env_path = os.getenv("SCHEMA_PATH")
    if env_path:
        return Path(env_path)
    return _repo_root() / "db" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    schema_path = get_schema_path()
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with get_connection() as conn:
        conn.executescript(schema_sql)
        # Lightweight migrations for new columns

        def _has_column(table: str, col: str) -> bool:
            cur = conn.execute(f"PRAGMA table_info({table})")
            return any(r[1] == col for r in cur.fetchall())

        if not _has_column("transactions", "category_source"):
            conn.execute(
                "ALTER TABLE transactions ADD COLUMN category_source TEXT;")
        if not _has_column("transactions", "category_provenance"):
            conn.execute(
                "ALTER TABLE transactions ADD COLUMN category_provenance TEXT;")
        # Insights optional columns for LLM rewrite cache
        if not _has_column("insights", "rewritten_title"):
            conn.execute(
                "ALTER TABLE insights ADD COLUMN rewritten_title TEXT;")
        if not _has_column("insights", "rewritten_body"):
            conn.execute(
                "ALTER TABLE insights ADD COLUMN rewritten_body TEXT;")
        if not _has_column("insights", "rewritten_at"):
            conn.execute(
                "ALTER TABLE insights ADD COLUMN rewritten_at TIMESTAMP;")

        # Add trial_converted to subscriptions if running against an older DB
        if not _has_column("subscriptions", "trial_converted"):
            conn.execute(
                "ALTER TABLE subscriptions ADD COLUMN trial_converted BOOLEAN DEFAULT 0;")

        # Users auth columns
        if not _has_column("users", "password_hash"):
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT;")
        if not _has_column("users", "password_salt"):
            conn.execute("ALTER TABLE users ADD COLUMN password_salt TEXT;")
