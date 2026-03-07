"""Database initialization and migration."""

import sqlite3
from config import DB_PATH

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            base_url TEXT,
            api_key TEXT,
            is_active INTEGER DEFAULT 1,
            models TEXT DEFAULT '[]',
            selected_models TEXT DEFAULT '[]',
            max_requests_per_day INTEGER DEFAULT 1000,
            max_rpm INTEGER DEFAULT 0,
            max_tpm INTEGER DEFAULT 0,
            current_requests_today INTEGER DEFAULT 0,
            last_reset_date TEXT,
            weight INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS model_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            alias TEXT UNIQUE,
            target_models TEXT DEFAULT '[]',
            strategy TEXT DEFAULT 'weighted_random'
        );

        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER,
            model TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            status_code INTEGER,
            error_message TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_usage_logs_provider_ts
            ON usage_logs (provider_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_usage_logs_provider_model_ts
            ON usage_logs (provider_id, model, timestamp);
    """)
    _migrate(conn)
    conn.close()

def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def _migrate(conn: sqlite3.Connection):
    if not _has_column(conn, "providers", "selected_models"):
        conn.execute("ALTER TABLE providers ADD COLUMN selected_models TEXT DEFAULT '[]'")
        conn.execute("UPDATE providers SET selected_models = models WHERE selected_models = '[]' AND models != '[]'")

    if not _has_column(conn, "providers", "max_rpm"):
        conn.execute("ALTER TABLE providers ADD COLUMN max_rpm INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE providers ADD COLUMN max_tpm INTEGER DEFAULT 0")

    if not _has_column(conn, "providers", "max_requests_total"):
        conn.execute("ALTER TABLE providers ADD COLUMN max_requests_total INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE providers ADD COLUMN max_tokens_total INTEGER DEFAULT 0")

    if not _has_column(conn, "model_groups", "strategy"):
        conn.execute("ALTER TABLE model_groups ADD COLUMN strategy TEXT DEFAULT 'weighted_random'")

    if not _has_column(conn, "usage_logs", "error_message"):
        conn.execute("ALTER TABLE usage_logs ADD COLUMN error_message TEXT")

    conn.commit()
