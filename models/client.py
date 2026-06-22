import sqlite3
from typing import Optional
from models.database import get_db, close_db


def get_all_clients() -> list[sqlite3.Row]:
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM clients ORDER BY name"
        ).fetchall()
        return rows
    finally:
        close_db(db)


def get_client_by_id(client_id: int) -> Optional[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
    finally:
        close_db(db)


def create_client(
    name: str,
    phone: str,
    email: str,
    address: str,
    gst_number: str,
) -> int:
    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO clients (name, phone, email, address, gst_number)
               VALUES (?, ?, ?, ?, ?)""",
            (name, phone, email, address, gst_number),
        )
        db.commit()
        return cursor.lastrowid
    finally:
        close_db(db)


def update_client(client_id: int, **kwargs: str) -> None:
    if not kwargs:
        return
    allowed = {'name', 'phone', 'email', 'address', 'gst_number'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [client_id]
    db = get_db()
    try:
        db.execute(f"UPDATE clients SET {set_clause} WHERE id = ?", values)
        db.commit()
    finally:
        close_db(db)


def delete_client(client_id: int) -> None:
    db = get_db()
    try:
        db.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        db.commit()
    finally:
        close_db(db)
