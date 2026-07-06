import sqlite3
from typing import Optional
from models.database import get_db, close_db


def _recalculate_trip_totals(db: sqlite3.Connection, trip_id: int) -> None:
    row = db.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE trip_id = ?",
        (trip_id,),
    ).fetchone()
    total_received = row['total']

    trip = db.execute(
        "SELECT freight_amount FROM trips WHERE id = ?", (trip_id,)
    ).fetchone()
    freight_amount = trip['freight_amount'] if trip else 0

    if freight_amount > 0 and total_received >= freight_amount:
        status = 'paid'
    elif total_received > 0:
        status = 'partial'
    else:
        status = 'unpaid'

    db.execute(
        "UPDATE trips SET total_received = ?, payment_status = ? WHERE id = ?",
        (total_received, status, trip_id),
    )


def create_payment(
    trip_id: int,
    amount: float,
    payment_mode: str,
    payment_reference: Optional[str],
    payment_date: str,
    notes: Optional[str],
    recorded_by: Optional[str],
) -> int:
    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO payments
               (trip_id, amount, payment_mode, payment_reference, payment_date, notes, recorded_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (trip_id, amount, payment_mode, payment_reference, payment_date, notes, recorded_by),
        )
        payment_id = cursor.lastrowid
        _recalculate_trip_totals(db, trip_id)
        db.commit()
        return payment_id
    finally:
        close_db(db)


def get_payments_for_trip(trip_id: int) -> list[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM payments WHERE trip_id = ? ORDER BY payment_date DESC, id DESC",
            (trip_id,),
        ).fetchall()
    finally:
        close_db(db)


def get_all_payments(
    client_filter: Optional[int] = None,
    status_filter: Optional[str] = None,
) -> list[sqlite3.Row]:
    db = get_db()
    try:
        query = """
            SELECT t.id as trip_id, t.lr_number, t.from_location, t.to_location,
                   t.freight_amount, t.total_received, t.payment_status,
                   (t.freight_amount - t.total_received) as pending_amount,
                   c.id as client_id, c.name as client_name
            FROM trips t
            LEFT JOIN clients c ON t.client_id = c.id
            WHERE t.status != 'cancelled'
        """
        params: list = []
        if status_filter:
            query += " AND t.payment_status = ?"
            params.append(status_filter)
        if client_filter:
            query += " AND t.client_id = ?"
            params.append(client_filter)
        query += " ORDER BY t.created_at DESC"
        return db.execute(query, params).fetchall()
    finally:
        close_db(db)


def get_client_dues() -> list[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute("""
            SELECT c.id as client_id, c.name as client_name,
                   COUNT(t.id) as trip_count,
                   COALESCE(SUM(t.freight_amount), 0) as total_freight,
                   COALESCE(SUM(t.total_received), 0) as total_received,
                   COALESCE(SUM(t.freight_amount - t.total_received), 0) as total_pending
            FROM clients c
            JOIN trips t ON t.client_id = c.id
            WHERE t.status != 'cancelled' AND t.payment_status != 'paid'
            GROUP BY c.id, c.name
            HAVING total_pending > 0
            ORDER BY total_pending DESC
        """).fetchall()
    finally:
        close_db(db)


def get_client_pending_trips(client_id: int) -> list[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute("""
            SELECT * FROM trips
            WHERE client_id = ? AND status != 'cancelled' AND payment_status != 'paid'
            ORDER BY created_at DESC
        """, (client_id,)).fetchall()
    finally:
        close_db(db)


def get_payment_summary() -> dict:
    db = get_db()
    try:
        row = db.execute("""
            SELECT COALESCE(SUM(freight_amount), 0) as total_receivable,
                   COALESCE(SUM(total_received), 0) as total_received
            FROM trips WHERE status != 'cancelled'
        """).fetchone()
        total_receivable = row['total_receivable']
        total_received = row['total_received']
        return {
            'total_receivable': total_receivable,
            'total_received': total_received,
            'total_pending': total_receivable - total_received,
        }
    finally:
        close_db(db)


def delete_payment(payment_id: int) -> None:
    db = get_db()
    try:
        row = db.execute(
            "SELECT trip_id FROM payments WHERE id = ?", (payment_id,)
        ).fetchone()
        if not row:
            return
        trip_id = row['trip_id']
        db.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
        _recalculate_trip_totals(db, trip_id)
        db.commit()
    finally:
        close_db(db)
