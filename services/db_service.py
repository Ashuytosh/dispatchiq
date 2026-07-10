import os
from models.database import get_db, close_db, get_db_type


def get_database_status() -> dict:
    db_type = get_db_type()
    if db_type == 'postgresql':
        host = os.environ.get('PG_HOST', 'localhost')
        port = os.environ.get('PG_PORT', '5432')
        dbname = os.environ.get('PG_DBNAME', 'dispatchiq')
        display = f"PostgreSQL ({host}:{port}/{dbname})"
    else:
        display = "SQLite (dispatchiq.db)"

    connected = False
    try:
        db = get_db()
        close_db(db)
        connected = True
    except Exception:
        connected = False

    return {'type': db_type, 'display': display, 'connected': connected}
