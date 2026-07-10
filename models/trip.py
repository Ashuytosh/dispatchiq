import sqlite3
from datetime import datetime
from typing import Optional
from models.database import get_db, close_db, insert_and_get_id, get_db_type


VALID_TRANSITIONS: dict[str, list[str]] = {
    'created':    ['assigned', 'cancelled'],
    'assigned':   ['dispatched', 'cancelled'],
    'dispatched': ['in_transit'],
    'in_transit': ['delivered'],
    'delivered':  ['invoiced'],
    'invoiced':   ['paid'],
    'paid':       [],
    'cancelled':  [],
}


def get_all_trips(
    status_filter: Optional[str] = None,
    client_filter: Optional[int] = None,
) -> list[sqlite3.Row]:
    db = get_db()
    try:
        query = """
            SELECT t.*, c.name as client_name,
                   v.plate_number, d.name as driver_name
            FROM trips t
            LEFT JOIN clients c ON t.client_id = c.id
            LEFT JOIN vehicles v ON t.vehicle_id = v.id
            LEFT JOIN drivers d ON t.driver_id = d.id
        """
        params: list = []
        conditions: list[str] = []
        if status_filter:
            conditions.append("t.status = ?")
            params.append(status_filter)
        if client_filter:
            conditions.append("t.client_id = ?")
            params.append(client_filter)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY t.created_at DESC"
        return db.execute(query, params).fetchall()
    finally:
        close_db(db)


def get_trip_by_id(trip_id: int) -> Optional[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            """SELECT t.*, c.name as client_name, c.phone as client_phone,
                      c.gst_number as client_gst, c.address as client_address,
                      v.plate_number, v.vehicle_type,
                      d.name as driver_name, d.phone as driver_phone, d.license_number as driver_license
               FROM trips t
               LEFT JOIN clients c ON t.client_id = c.id
               LEFT JOIN vehicles v ON t.vehicle_id = v.id
               LEFT JOIN drivers d ON t.driver_id = d.id
               WHERE t.id = ?""",
            (trip_id,),
        ).fetchone()
    finally:
        close_db(db)


def create_trip(
    client_id: int,
    from_location: str,
    to_location: str,
    goods_description: str,
    weight_tons: float,
    num_packages: int,
    freight_amount: float,
    advance_paid: float,
) -> int:
    balance = freight_amount - advance_paid
    db = get_db()
    try:
        new_id = insert_and_get_id(
            db,
            """INSERT INTO trips
               (client_id, from_location, to_location, goods_description,
                weight_tons, num_packages, freight_amount, advance_paid, balance_amount)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, from_location, to_location, goods_description,
             weight_tons, num_packages, freight_amount, advance_paid, balance),
        )
        db.commit()
        return new_id
    finally:
        close_db(db)


def update_trip_status(trip_id: int, new_status: str) -> None:
    db = get_db()
    try:
        row = db.execute(
            "SELECT status FROM trips WHERE id = ?", (trip_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Trip {trip_id} not found")

        current = row['status']
        allowed = VALID_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition trip from '{current}' to '{new_status}'. "
                f"Allowed: {allowed}"
            )

        extra_fields = ""
        params: list = [new_status]

        if new_status == 'dispatched':
            extra_fields = ", dispatched_at = CURRENT_TIMESTAMP"
        elif new_status == 'delivered':
            extra_fields = ", delivered_at = CURRENT_TIMESTAMP"
        elif new_status == 'paid':
            extra_fields = ", paid_at = CURRENT_TIMESTAMP"

        db.execute(
            f"UPDATE trips SET status = ?{extra_fields} WHERE id = ?",
            params + [trip_id],
        )
        db.commit()
    finally:
        close_db(db)


def assign_trip(trip_id: int, vehicle_id: int, driver_id: int) -> None:
    db = get_db()
    try:
        row = db.execute(
            "SELECT status FROM trips WHERE id = ?", (trip_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Trip {trip_id} not found")
        if row['status'] != 'created':
            raise ValueError(
                f"Trip can only be assigned when in 'created' status, "
                f"current: '{row['status']}'"
            )
        db.execute(
            """UPDATE trips SET vehicle_id = ?, driver_id = ?, status = 'assigned'
               WHERE id = ?""",
            (vehicle_id, driver_id, trip_id),
        )
        db.commit()
    finally:
        close_db(db)


def set_trip_lr_number(trip_id: int, lr_number: str) -> None:
    db = get_db()
    try:
        db.execute(
            "UPDATE trips SET lr_number = ? WHERE id = ?", (lr_number, trip_id)
        )
        db.commit()
    finally:
        close_db(db)


def set_trip_invoice_number(trip_id: int, invoice_number: str) -> None:
    db = get_db()
    try:
        db.execute(
            "UPDATE trips SET invoice_number = ? WHERE id = ?",
            (invoice_number, trip_id),
        )
        db.commit()
    finally:
        close_db(db)


def get_trip_stats() -> dict[str, int]:
    db = get_db()
    try:
        rows = db.execute(
            "SELECT status, COUNT(*) as count FROM trips GROUP BY status"
        ).fetchall()
        stats: dict[str, int] = {
            'created': 0, 'assigned': 0, 'dispatched': 0,
            'in_transit': 0, 'delivered': 0, 'invoiced': 0,
            'paid': 0, 'cancelled': 0, 'total': 0,
        }
        for row in rows:
            stats[row['status']] = row['count']
            stats['total'] += row['count']
        return stats
    finally:
        close_db(db)


def get_monthly_revenue_trend(months: int = 6) -> list[sqlite3.Row]:
    db = get_db()
    try:
        if get_db_type() == 'postgresql':
            query = """
                SELECT TO_CHAR(paid_at, 'YYYY-MM') as ym,
                       COALESCE(SUM(freight_amount), 0) as total_revenue
                FROM trips
                WHERE status = 'paid'
                  AND paid_at >= DATE_TRUNC('month', CURRENT_DATE - (? || ' months')::interval)
                GROUP BY ym
                ORDER BY ym
            """
            params = (str(months - 1),)
        else:
            query = """
                SELECT strftime('%Y-%m', paid_at) as ym,
                       COALESCE(SUM(freight_amount), 0) as total_revenue
                FROM trips
                WHERE status = 'paid'
                  AND paid_at >= date('now', ?, 'start of month')
                GROUP BY ym
                ORDER BY ym
            """
            params = (f'-{months - 1} months',)
        return db.execute(query, params).fetchall()
    finally:
        close_db(db)


def get_daily_trip_counts(days: int = 30) -> list[sqlite3.Row]:
    db = get_db()
    try:
        if get_db_type() == 'postgresql':
            query = """
                SELECT created_at::date as day, COUNT(*) as trip_count
                FROM trips
                WHERE created_at::date >= CURRENT_DATE - (? || ' days')::interval
                GROUP BY day
                ORDER BY day
            """
            params = (str(days - 1),)
        else:
            query = """
                SELECT DATE(created_at) as day, COUNT(*) as trip_count
                FROM trips
                WHERE DATE(created_at) >= date('now', ?)
                GROUP BY day
                ORDER BY day
            """
            params = (f'-{days - 1} days',)
        return db.execute(query, params).fetchall()
    finally:
        close_db(db)


def generate_lr_number() -> str:
    year = datetime.now().year
    db = get_db()
    try:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM trips WHERE lr_number IS NOT NULL"
        ).fetchone()
        seq = (row['cnt'] or 0) + 1
        return f"LR-{year}-{seq:04d}"
    finally:
        close_db(db)


def generate_invoice_number() -> str:
    year = datetime.now().year
    db = get_db()
    try:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM trips WHERE invoice_number IS NOT NULL"
        ).fetchone()
        seq = (row['cnt'] or 0) + 1
        return f"INV-{year}-{seq:04d}"
    finally:
        close_db(db)


def get_trips_by_month(month: int, year: int) -> list[sqlite3.Row]:
    db = get_db()
    try:
        base_query = """SELECT t.*, c.name as client_name,
                      v.plate_number, d.name as driver_name
               FROM trips t
               LEFT JOIN clients c ON t.client_id = c.id
               LEFT JOIN vehicles v ON t.vehicle_id = v.id
               LEFT JOIN drivers d ON t.driver_id = d.id
               WHERE {condition}
               ORDER BY t.created_at"""
        if get_db_type() == 'postgresql':
            query = base_query.format(
                condition="EXTRACT(MONTH FROM t.created_at) = ? AND EXTRACT(YEAR FROM t.created_at) = ?"
            )
            params = (month, year)
        else:
            query = base_query.format(
                condition="strftime('%m', t.created_at) = ? AND strftime('%Y', t.created_at) = ?"
            )
            params = (f"{month:02d}", str(year))
        return db.execute(query, params).fetchall()
    finally:
        close_db(db)


def get_active_trip_by_vehicle_id(vehicle_id: int) -> Optional[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            """SELECT * FROM trips
               WHERE vehicle_id = ? AND status IN ('dispatched', 'in_transit')
               ORDER BY id DESC LIMIT 1""",
            (vehicle_id,),
        ).fetchone()
    finally:
        close_db(db)


def get_trip_activity(trip_id: int) -> list[sqlite3.Row]:
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM activity_log WHERE trip_id = ? ORDER BY created_at ASC",
            (trip_id,),
        ).fetchall()
    finally:
        close_db(db)


def log_trip_activity(trip_id: int, action: str, message: str) -> None:
    db = get_db()
    try:
        db.execute(
            "INSERT INTO activity_log (trip_id, action, message) VALUES (?, ?, ?)",
            (trip_id, action, message),
        )
        db.commit()
    finally:
        close_db(db)


def _date_eq_condition(column: str) -> str:
    if get_db_type() == 'postgresql':
        return f"{column}::date = ?"
    return f"DATE({column}) = ?"


def get_trip_count_on_date(column: str, day: str) -> int:
    allowed = {'created_at', 'delivered_at'}
    if column not in allowed:
        raise ValueError(f"Unsupported column: {column}")
    db = get_db()
    try:
        row = db.execute(
            f"SELECT COUNT(*) as cnt FROM trips WHERE {_date_eq_condition(column)}",
            (day,),
        ).fetchone()
        return row['cnt'] if row else 0
    finally:
        close_db(db)


def get_revenue_on_date(day: str) -> float:
    db = get_db()
    try:
        row = db.execute(
            f"SELECT COALESCE(SUM(freight_amount), 0) as total FROM trips "
            f"WHERE {_date_eq_condition('paid_at')}",
            (day,),
        ).fetchone()
        return float(row['total']) if row else 0.0
    finally:
        close_db(db)


def get_current_month_revenue() -> float:
    db = get_db()
    try:
        if get_db_type() == 'postgresql':
            query = """SELECT COALESCE(SUM(freight_amount), 0) as total FROM trips
                       WHERE TO_CHAR(paid_at, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM')"""
        else:
            query = """SELECT COALESCE(SUM(freight_amount), 0) as total FROM trips
                       WHERE strftime('%Y-%m', paid_at) = strftime('%Y-%m', 'now')"""
        row = db.execute(query).fetchone()
        return float(row['total']) if row else 0.0
    finally:
        close_db(db)


def get_overdue_trips(min_days: int = 2) -> list[dict]:
    db = get_db()
    try:
        if get_db_type() == 'postgresql':
            query = """
                SELECT id, from_location, to_location, status,
                       CAST(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - dispatched_at)) / 86400 AS INTEGER) as days_out
                FROM trips
                WHERE status IN ('dispatched', 'in_transit')
                  AND dispatched_at IS NOT NULL
                  AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - dispatched_at)) / 86400 >= ?
                ORDER BY days_out DESC
            """
        else:
            query = """
                SELECT id, from_location, to_location, status,
                       CAST(julianday('now') - julianday(dispatched_at) AS INTEGER) as days_out
                FROM trips
                WHERE status IN ('dispatched', 'in_transit')
                  AND dispatched_at IS NOT NULL
                  AND julianday('now') - julianday(dispatched_at) >= ?
                ORDER BY days_out DESC
            """
        rows = db.execute(query, (min_days,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_db(db)
