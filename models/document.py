import sqlite3
from typing import Optional
from models.database import get_db, close_db


def save_document(trip_id: int, doc_type: str, file_path: str) -> int:
    db = get_db()
    try:
        db.execute(
            """INSERT INTO documents (trip_id, doc_type, file_path) VALUES (?, ?, ?)
               ON CONFLICT(trip_id, doc_type) DO UPDATE SET file_path = excluded.file_path""",
            (trip_id, doc_type, file_path),
        )
        db.commit()
        row = db.execute(
            "SELECT id FROM documents WHERE trip_id = ? AND doc_type = ?",
            (trip_id, doc_type),
        ).fetchone()
        return row['id']
    finally:
        close_db(db)


def get_document(trip_id: int, doc_type: str) -> Optional[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM documents WHERE trip_id = ? AND doc_type = ? ORDER BY created_at DESC LIMIT 1",
            (trip_id, doc_type),
        ).fetchone()
    finally:
        close_db(db)
