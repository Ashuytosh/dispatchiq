import sqlite3
from typing import Optional
from models.database import get_db, close_db, insert_and_get_id


def get_all_drivers() -> list[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM drivers ORDER BY name"
        ).fetchall()
    finally:
        close_db(db)


def get_driver_by_id(driver_id: int) -> Optional[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM drivers WHERE id = ?", (driver_id,)
        ).fetchone()
    finally:
        close_db(db)


def get_available_drivers() -> list[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            """SELECT d.* FROM drivers d
               LEFT JOIN trips t ON t.driver_id = d.id
                   AND t.status NOT IN ('delivered', 'invoiced', 'paid', 'cancelled')
               WHERE t.id IS NULL
               ORDER BY d.name"""
        ).fetchall()
    finally:
        close_db(db)


def create_driver(
    name: str,
    phone: str,
    license_number: str,
    assigned_vehicle_id: Optional[int] = None,
) -> int:
    db = get_db()
    try:
        new_id = insert_and_get_id(
            db,
            """INSERT INTO drivers (name, phone, license_number, assigned_vehicle_id)
               VALUES (?, ?, ?, ?)""",
            (name, phone, license_number, assigned_vehicle_id),
        )
        db.commit()
        return new_id
    finally:
        close_db(db)


def update_driver(driver_id: int, **kwargs) -> None:
    if not kwargs:
        return
    allowed = {'name', 'phone', 'license_number', 'assigned_vehicle_id'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [driver_id]
    db = get_db()
    try:
        db.execute(f"UPDATE drivers SET {set_clause} WHERE id = ?", values)
        db.commit()
    finally:
        close_db(db)


def delete_driver(driver_id: int) -> None:
    db = get_db()
    try:
        db.execute("DELETE FROM drivers WHERE id = ?", (driver_id,))
        db.commit()
    finally:
        close_db(db)
