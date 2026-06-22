from flask import Flask
from models.database import init_db
from routes.dashboard_routes import dashboard_bp
from routes.trip_routes import trips_bp
from routes.vehicle_routes import vehicles_bp
from routes.driver_routes import drivers_bp
from routes.client_routes import clients_bp
from routes.settings_routes import settings_bp
from routes.api_routes import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = 'dispatchiq-dev-secret'

    init_db()

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(trips_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(drivers_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)

    return app
