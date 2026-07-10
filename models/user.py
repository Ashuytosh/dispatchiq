from werkzeug.security import generate_password_hash, check_password_hash
from models.database import get_db, close_db, insert_and_get_id


def create_user(username: str, email: str, password: str, full_name: str,
                role: str = 'dispatcher') -> int:
    db = get_db()
    try:
        new_id = insert_and_get_id(
            db,
            """INSERT INTO users (username, email, password_hash, full_name, role)
               VALUES (?, ?, ?, ?, ?)""",
            (username.strip(), email.strip().lower(),
             generate_password_hash(password), full_name.strip(), role),
        )
        db.commit()
        return new_id
    finally:
        close_db(db)


def get_user_by_id(user_id: int) -> dict | None:
    db = get_db()
    try:
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        close_db(db)


def get_user_by_username(username: str) -> dict | None:
    db = get_db()
    try:
        row = db.execute(
            "SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        close_db(db)


def get_user_by_email(email: str) -> dict | None:
    db = get_db()
    try:
        row = db.execute(
            "SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        close_db(db)


def get_all_users() -> list[dict]:
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_db(db)


def verify_password(stored_hash: str, password: str) -> bool:
    return check_password_hash(stored_hash, password)


def update_last_login(user_id: int) -> None:
    db = get_db()
    try:
        db.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,)
        )
        db.commit()
    finally:
        close_db(db)


def update_user(user_id: int, **kwargs) -> None:
    allowed = {'full_name', 'email', 'password_hash', 'role', 'is_active'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    if 'password' in kwargs:
        fields['password_hash'] = generate_password_hash(kwargs['password'])
    sets = ', '.join(f"{k} = ?" for k in fields)
    db = get_db()
    try:
        db.execute(f"UPDATE users SET {sets} WHERE id = ?", (*fields.values(), user_id))
        db.commit()
    finally:
        close_db(db)


def deactivate_user(user_id: int) -> None:
    db = get_db()
    try:
        db.execute("UPDATE users SET is_active = ? WHERE id = ?", (False, user_id))
        db.commit()
    finally:
        close_db(db)


def count_users() -> int:
    db = get_db()
    try:
        row = db.execute("SELECT COUNT(*) as n FROM users").fetchone()
        return row['n'] if row else 0
    finally:
        close_db(db)
