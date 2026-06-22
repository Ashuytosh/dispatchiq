import sqlite3
from typing import Optional
from models.database import get_db, close_db


def get_all_vehicles() -> list[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM vehicles ORDER BY plate_number"
        ).fetchall()
    finally:
        close_db(db)


def get_vehicle_by_id(vehicle_id: int) -> Optional[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)
        ).fetchone()
    finally:
        close_db(db)


def get_available_vehicles() -> list[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM vehicles WHERE status = 'available' ORDER BY plate_number"
        ).fetchall()
    finally:
        close_db(db)


def create_vehicle(
    plate_number: str,
    vehicle_type: str,
    capacity_tons: float,
) -> int:
    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO vehicles (plate_number, vehicle_type, capacity_tons)
               VALUES (?, ?, ?)""",
            (plate_number, vehicle_type, capacity_tons),
        )
        db.commit()
        return cursor.lastrowid
    finally:
        close_db(db)


def update_vehicle(vehicle_id: int, **kwargs) -> None:
    if not kwargs:
        return
    allowed = {'plate_number', 'vehicle_type', 'capacity_tons', 'status'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [vehicle_id]
    db = get_db()
    try:
        db.execute(f"UPDATE vehicles SET {set_clause} WHERE id = ?", values)
        db.commit()
    finally:
        close_db(db)


def update_vehicle_status(vehicle_id: int, status: str) -> None:
    db = get_db()
    try:
        db.execute(
            "UPDATE vehicles SET status = ? WHERE id = ?", (status, vehicle_id)
        )
        db.commit()
    finally:
        close_db(db)


def delete_vehicle(vehicle_id: int) -> None:
    db = get_db()
    try:
        db.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        db.commit()
    finally:
        close_db(db)
