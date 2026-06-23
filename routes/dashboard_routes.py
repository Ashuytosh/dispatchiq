from flask import Blueprint, render_template
from services import trip_service
from models import trip as trip_model

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    stats = trip_service.get_dashboard_stats()
    all_trips = trip_model.get_all_trips()
    active_trips = [t for t in all_trips if t['status'] not in ('paid', 'cancelled')]
    return render_template('dashboard.html', stats=stats, trips=active_trips)
