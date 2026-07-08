from flask import Blueprint, render_template, abort
from models import vehicle as vehicle_model
from models import trip as trip_model
from services import tracker_service
from services.auth import login_required

map_bp = Blueprint('map', __name__, url_prefix='/map')


@map_bp.route('/')
@login_required
def fleet_map():
    configured = tracker_service.is_traccar_configured()
    return render_template('map/fleet_map.html', configured=configured)


@map_bp.route('/vehicle/<plate_number>')
@login_required
def vehicle_map(plate_number: str):
    configured = tracker_service.is_traccar_configured()
    target = plate_number.strip().upper()
    vehicle = next(
        (v for v in vehicle_model.get_all_vehicles()
         if v['plate_number'].strip().upper() == target),
        None,
    )
    if not vehicle:
        abort(404)
    active_trip = trip_model.get_active_trip_by_vehicle_id(vehicle['id'])
    return render_template(
        'map/vehicle_map.html',
        configured=configured,
        vehicle=vehicle,
        trip=active_trip,
    )
