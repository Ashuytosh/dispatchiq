import sqlite3
from typing import Optional


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect('dispatchiq.db')
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def close_db(db: sqlite3.Connection) -> None:
    if db:
        db.close()


def init_db() -> None:
    db = get_db()
    try:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT,
                gst_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT NOT NULL UNIQUE,
                vehicle_type TEXT NOT NULL,
                capacity_tons REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'available'
                    CHECK(status IN ('available', 'on_trip', 'maintenance')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                license_number TEXT NOT NULL UNIQUE,
                assigned_vehicle_id INTEGER REFERENCES vehicles(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL REFERENCES clients(id),
                vehicle_id INTEGER REFERENCES vehicles(id),
                driver_id INTEGER REFERENCES drivers(id),
                from_location TEXT NOT NULL,
                to_location TEXT NOT NULL,
                goods_description TEXT,
                weight_tons REAL,
                num_packages INTEGER,
                freight_amount REAL NOT NULL DEFAULT 0,
                advance_paid REAL NOT NULL DEFAULT 0,
                balance_amount REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'created'
                    CHECK(status IN ('created','assigned','dispatched','in_transit',
                                     'delivered','invoiced','paid','cancelled')),
                lr_number TEXT,
                invoice_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                dispatched_at TIMESTAMP,
                delivered_at TIMESTAMP,
                paid_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL REFERENCES trips(id),
                doc_type TEXT NOT NULL CHECK(doc_type IN ('lr', 'invoice')),
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER REFERENCES trips(id),
                action TEXT NOT NULL,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL REFERENCES trips(id),
                amount REAL NOT NULL,
                payment_mode TEXT NOT NULL
                    CHECK(payment_mode IN ('cash', 'bank_transfer', 'upi', 'cheque')),
                payment_reference TEXT,
                payment_date TEXT NOT NULL,
                notes TEXT,
                recorded_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'dispatcher'
                    CHECK(role IN ('admin', 'dispatcher', 'viewer')),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
        """)
        db.commit()

        for alter_sql in (
            "ALTER TABLE trips ADD COLUMN total_received REAL DEFAULT 0",
            "ALTER TABLE trips ADD COLUMN payment_status TEXT DEFAULT 'unpaid'",
        ):
            try:
                db.execute(alter_sql)
                db.commit()
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise
    finally:
        close_db(db)
