import sqlite3
from typing import Optional
from models.database import get_db, close_db


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    db = get_db()
    try:
        row = db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row['value'] if row else default
    finally:
        close_db(db)


def set_setting(key: str, value: str) -> None:
    db = get_db()
    try:
        db.execute(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                              updated_at = CURRENT_TIMESTAMP""",
            (key, value),
        )
        db.commit()
    finally:
        close_db(db)


def get_all_settings() -> dict[str, str]:
    db = get_db()
    try:
        rows = db.execute("SELECT key, value FROM settings").fetchall()
        return {row['key']: row['value'] for row in rows}
    finally:
        close_db(db)
