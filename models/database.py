import os
import sqlite3
from typing import Any, Optional


def get_db_type() -> str:
    return os.environ.get('DB_TYPE', 'sqlite')


class _PGCursorWrapper:
    """Wraps a psycopg2 cursor so callers can read cursor.lastrowid uniformly.

    psycopg2 never populates lastrowid; insert_and_get_id() is the real
    mechanism for postgres, this attribute just avoids AttributeErrors for
    any code path that doesn't need the inserted id.
    """

    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor
        self.lastrowid: Optional[int] = None

    def fetchone(self) -> Any:
        return self._cursor.fetchone()

    def fetchall(self) -> Any:
        return self._cursor.fetchall()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)


class _PGConnection:
    """Wraps a psycopg2 connection to mimic the sqlite3.Connection surface
    that every model file already calls: .execute(), .executemany(),
    .commit(), .rollback(), .close(). Translates '?' placeholders to '%s'
    so existing query strings work unchanged.

    Known limitation: this does a plain string replace, so it would break
    if a query ever embedded a literal '?' character inside a string
    literal. No current query does.
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def execute(self, sql: str, params: Any = ()) -> _PGCursorWrapper:
        cursor = self._conn.cursor()
        cursor.execute(sql.replace('?', '%s'), tuple(params))
        return _PGCursorWrapper(cursor)

    def executemany(self, sql: str, seq_of_params: Any) -> _PGCursorWrapper:
        cursor = self._conn.cursor()
        cursor.executemany(sql.replace('?', '%s'), seq_of_params)
        return _PGCursorWrapper(cursor)

    def executescript(self, sql: str) -> None:
        cursor = self._conn.cursor()
        cursor.execute(sql)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def get_db() -> Any:
    if get_db_type() == 'postgresql':
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host=os.environ.get('PG_HOST', 'localhost'),
            port=os.environ.get('PG_PORT', '5432'),
            dbname=os.environ.get('PG_DBNAME', 'dispatchiq'),
            user=os.environ.get('PG_USER', 'postgres'),
            password=os.environ.get('PG_PASSWORD', ''),
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        return _PGConnection(conn)

    db = sqlite3.connect('dispatchiq.db')
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def close_db(db: Any) -> None:
    if db:
        db.close()


def get_auto_id() -> str:
    if get_db_type() == 'postgresql':
        return 'SERIAL PRIMARY KEY'
    return 'INTEGER PRIMARY KEY AUTOINCREMENT'


def insert_and_get_id(db: Any, sql: str, params: tuple, id_column: str = 'id') -> int:
    """Runs an INSERT and returns the new row's id. sqlite populates
    cursor.lastrowid; postgres has no equivalent, so RETURNING is appended.
    """
    if get_db_type() == 'postgresql':
        cursor = db.execute(f"{sql} RETURNING {id_column}", params)
        return cursor.fetchone()[id_column]
    cursor = db.execute(sql, params)
    return cursor.lastrowid


def _schema_sql() -> str:
    auto_id = get_auto_id()
    is_active_default = 'TRUE' if get_db_type() == 'postgresql' else '1'
    return f"""
        CREATE TABLE IF NOT EXISTS clients (
            id {auto_id},
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            gst_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vehicles (
            id {auto_id},
            plate_number TEXT NOT NULL UNIQUE,
            vehicle_type TEXT NOT NULL,
            capacity_tons REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'available'
                CHECK(status IN ('available', 'on_trip', 'maintenance')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS drivers (
            id {auto_id},
            name TEXT NOT NULL,
            phone TEXT,
            license_number TEXT NOT NULL UNIQUE,
            assigned_vehicle_id INTEGER REFERENCES vehicles(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS trips (
            id {auto_id},
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
            id {auto_id},
            trip_id INTEGER NOT NULL REFERENCES trips(id),
            doc_type TEXT NOT NULL CHECK(doc_type IN ('lr', 'invoice')),
            file_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(trip_id, doc_type)
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id {auto_id},
            trip_id INTEGER REFERENCES trips(id),
            action TEXT NOT NULL,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS payments (
            id {auto_id},
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
            id {auto_id},
            key TEXT NOT NULL UNIQUE,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id {auto_id},
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'dispatcher'
                CHECK(role IN ('admin', 'dispatcher', 'viewer')),
            is_active BOOLEAN NOT NULL DEFAULT {is_active_default},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
    """


def init_db() -> None:
    db_type = get_db_type()
    db = get_db()
    try:
        db.executescript(_schema_sql())
        db.commit()

        for alter_sql in (
            "ALTER TABLE trips ADD COLUMN total_received REAL DEFAULT 0",
            "ALTER TABLE trips ADD COLUMN payment_status TEXT DEFAULT 'unpaid'",
        ):
            try:
                db.execute(alter_sql)
                db.commit()
            except sqlite3.OperationalError as e:
                if db_type != 'sqlite' or "duplicate column" not in str(e).lower():
                    raise
                db.rollback()
            except Exception as e:
                if db_type != 'postgresql' or "already exists" not in str(e).lower():
                    raise
                db.rollback()

        # Backfills the UNIQUE(trip_id, doc_type) constraint for databases
        # created before it was added to the documents table DDL above.
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_trip_doctype "
            "ON documents(trip_id, doc_type)"
        )

        for index_sql in (
            "CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status)",
            "CREATE INDEX IF NOT EXISTS idx_trips_client_id ON trips(client_id)",
            "CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status)",
        ):
            db.execute(index_sql)

        db.commit()
    finally:
        close_db(db)
