from flask import Blueprint, jsonify, request
from models import trip as trip_model
from models import vehicle as vehicle_model
from models import client as client_model
from services import trip_service

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _row(r):
    return dict(r) if r else None


@api_bp.route('/trips', methods=['GET'])
def get_trips():
    status = request.args.get('status')
    client_id = request.args.get('client_id')
    trips = trip_model.get_all_trips(
        status_filter=status or None,
        client_filter=int(client_id) if client_id else None,
    )
    return jsonify([_row(t) for t in trips])


@api_bp.route('/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id: int):
    trip = trip_model.get_trip_by_id(trip_id)
    if not trip:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(_row(trip))


@api_bp.route('/trips', methods=['POST'])
def create_trip():
    data = request.get_json(force=True) or {}
    try:
        trip_id = trip_service.create_new_trip(data)
        return jsonify({'id': trip_id}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/vehicles', methods=['GET'])
def get_vehicles():
    vehicles = vehicle_model.get_all_vehicles()
    return jsonify([_row(v) for v in vehicles])


@api_bp.route('/vehicles/available', methods=['GET'])
def get_available_vehicles():
    vehicles = vehicle_model.get_available_vehicles()
    return jsonify([_row(v) for v in vehicles])


@api_bp.route('/clients', methods=['GET'])
def get_clients():
    clients = client_model.get_all_clients()
    return jsonify([_row(c) for c in clients])


@api_bp.route('/dashboard/stats', methods=['GET'])
def get_stats():
    stats = trip_service.get_dashboard_stats()
    return jsonify(stats)
