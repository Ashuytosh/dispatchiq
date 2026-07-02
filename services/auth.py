from functools import wraps
from flask import session, redirect, url_for, flash


def get_current_user() -> dict | None:
    user_id = session.get('user_id')
    if not user_id:
        return None
    from models.user import get_user_by_id
    return get_user_by_id(user_id)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated
