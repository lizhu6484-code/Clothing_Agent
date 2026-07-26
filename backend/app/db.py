import sqlite3

from app.config import settings


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            gender TEXT NOT NULL DEFAULT '',
            height_cm REAL,
            weight_kg REAL,
            age INTEGER,
            notes TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS wardrobe_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            image_path TEXT NOT NULL,
            image_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '',
            color TEXT NOT NULL DEFAULT '',
            material TEXT,
            season TEXT NOT NULL DEFAULT '[]',
            formality INTEGER NOT NULL DEFAULT 3,
            style TEXT NOT NULL DEFAULT '[]',
            features TEXT NOT NULL DEFAULT '[]',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
