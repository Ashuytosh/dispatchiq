from flask import Flask
from models.database import init_db
from routes.dashboard_routes import dashboard_bp
from routes.trip_routes import trips_bp
from routes.vehicle_routes import vehicles_bp
from routes.driver_routes import drivers_bp
from routes.client_routes import clients_bp
from routes.settings_routes import settings_bp
from routes.api_routes import api_bp


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
    app.secret_key = 'dispatchiq-dev-secret'

    app.jinja_env.filters['date'] = _fmt_date
    app.jinja_env.filters['money'] = _fmt_money

    init_db()

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(trips_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(drivers_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)

    from services.scheduler import start_scheduler
    try:
        start_scheduler(app)
    except Exception:
        pass

    return app
