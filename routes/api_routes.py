from flask import Blueprint, jsonify, request
from models import trip as trip_model
from models import vehicle as vehicle_model
from models import client as client_model
from services import trip_service
from services import analytics_service

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


@api_bp.route('/dashboard/charts', methods=['GET'])
def get_dashboard_charts():
    data = analytics_service.get_dashboard_chart_data()
    return jsonify(data)


@api_bp.route('/whatsapp/status', methods=['GET'])
def whatsapp_status():
    from services.whatsapp_service import check_whatsapp_status
    return jsonify({'connected': check_whatsapp_status()})


@api_bp.route('/settings/owner-phone', methods=['GET'])
def get_owner_phone():
    from models.settings import get_setting
    return jsonify({'owner_phone': get_setting('whatsapp_owner_phone', '')})


@api_bp.route('/ai/parse-trip', methods=['POST'])
def ai_parse_trip():
    from services.ai_parser import parse_trip_from_text
    data = request.get_json(force=True) or {}
    text = (data.get('text', '') or '').strip()
    if not text:
        return jsonify({'success': False, 'reply': '❌ Empty message.'})

    result = parse_trip_from_text(text)
    if result is None:
        return jsonify({'success': False,
            'reply': '❌ AI unavailable.\nCheck Gemini API key in Settings.'})
    if 'error' in result:
        return jsonify({'success': False,
            'reply': "❌ Could not understand.\nTry: '20 ton steel Tarapur to Kalamboli Tata Steel'"})
    if not result.get('client_id'):
        return jsonify({'success': False,
            'reply': (f"⚠️ Client not found.\n"
                      f"Parsed: {result.get('from_location')} → {result.get('to_location')}, "
                      f"{result.get('weight_tons')} MT\n"
                      f"Add client in DispatchIQ first.")})
    try:
        trip_id = trip_service.create_new_trip({
            'client_id': result['client_id'],
            'from_location': result['from_location'],
            'to_location': result['to_location'],
            'goods_description': result.get('goods_description') or '',
            'weight_tons': result.get('weight_tons') or 0,
            'num_packages': result.get('num_packages') or 1,
            'freight_amount': result.get('freight_amount') or 0,
            'advance_paid': 0,
        })
        reply = (f"✅ Trip Created!\n━━━━━━━━━━━━\n"
                 f"Trip #: {trip_id}\nClient: {result['client_match']}\n"
                 f"From: {result['from_location']}\nTo: {result['to_location']}\n"
                 f"Weight: {result.get('weight_tons')} MT\n"
                 f"Freight: ₹{float(result.get('freight_amount') or 0):,.0f}\n\n"
                 f"Open DispatchIQ to assign vehicle.")
        return jsonify({'success': True, 'reply': reply})
    except Exception as e:
        return jsonify({'success': False, 'reply': f'❌ Trip creation failed: {e}'})


@api_bp.route('/ai/test-summary', methods=['POST'])
def ai_test_summary():
    from services.daily_summary import generate_daily_summary
    from services.whatsapp_service import send_whatsapp
    from models.settings import get_setting
    summary = generate_daily_summary()
    if not summary:
        return jsonify({'success': False, 'summary': 'Failed — check Gemini API key in Settings.'})
    owner_phone = get_setting('whatsapp_owner_phone', '')
    if owner_phone:
        send_whatsapp(owner_phone, summary)
    return jsonify({'success': True, 'summary': summary})
