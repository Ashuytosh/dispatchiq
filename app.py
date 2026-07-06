import os
from datetime import timedelta
from flask import Flask, session, request, redirect, url_for
from models.database import init_db
from routes.dashboard_routes import dashboard_bp
from routes.trip_routes import trips_bp
from routes.payment_routes import payment_bp
from routes.vehicle_routes import vehicles_bp
from routes.driver_routes import drivers_bp
from routes.client_routes import clients_bp
from routes.settings_routes import settings_bp
from routes.api_routes import api_bp
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp


def _fmt_date(value: str | None) -> str:
    if not value:
        return ''
    try:
        return f"{value[8:10]}-{value[5:7]}-{value[:4]}"
    except Exception:
        return str(value)


def _fmt_money(value) -> str:
    try:
        return f"₹{float(value):,.0f}"
    except Exception:
        return '₹0'


def create_app() -> Flask:
    app = Flask(__name__)

    app.jinja_env.filters['date'] = _fmt_date
    app.jinja_env.filters['money'] = _fmt_money

    init_db()

    # Secret key: generated once and persisted in settings so sessions survive restarts
    from models.settings import get_setting, set_setting
    secret = get_setting('secret_key', '')
    if not secret:
        secret = os.urandom(32).hex()
        set_setting('secret_key', secret)
    app.secret_key = secret
    app.permanent_session_lifetime = timedelta(hours=24)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(trips_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(drivers_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)

    @app.before_request
    def require_login():
        public_endpoints = {'auth.login', 'auth.signup', 'auth.logout', 'static'}
        if not request.endpoint:
            return
        if request.endpoint in public_endpoints:
            return
        if request.endpoint.startswith('api.'):
            return
        if not session.get('user_id'):
            return redirect(url_for('auth.login', next=request.path))

    @app.context_processor
    def inject_user():
        from services.auth import get_current_user
        return dict(current_user=get_current_user())

    from services.scheduler import start_scheduler
    try:
        start_scheduler(app)
    except Exception:
        pass

    return app
