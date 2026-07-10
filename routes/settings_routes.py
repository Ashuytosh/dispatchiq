import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import settings as settings_model
from models import client as client_model
from services.whatsapp_service import check_whatsapp_status
from services import db_service
from services.auth import admin_required

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

SETTINGS_KEYS = [
    'company_name', 'company_address', 'company_phone', 'company_gst',
    'bank_name', 'bank_account', 'bank_ifsc',
    'whatsapp_enabled', 'whatsapp_owner_phone', 'daily_summary_time',
    'notify_on_dispatched', 'notify_on_delivered', 'notify_on_invoiced', 'notify_on_paid',
    'gemini_api_key', 'ai_trip_creation_enabled',
    'traccar_url', 'traccar_enabled', 'traccar_username', 'traccar_password',
]


@settings_bp.route('/')
@admin_required
def index():
    current = settings_model.get_all_settings()
    wa_connected = check_whatsapp_status()
    clients = client_model.get_all_clients()
    try:
        notify_clients = json.loads(current.get('notify_clients', '{}') or '{}')
    except (json.JSONDecodeError, TypeError):
        notify_clients = {}
    db_status = db_service.get_database_status()
    return render_template('settings.html', settings=current, wa_connected=wa_connected,
                           clients=clients, notify_clients=notify_clients, db_status=db_status)


@settings_bp.route('/save', methods=['POST'])
@admin_required
def save():
    for key in SETTINGS_KEYS:
        value = request.form.get(key, '')
        settings_model.set_setting(key, value)
    all_clients = client_model.get_all_clients()
    notify_map = {
        str(c['id']): request.form.get(f'notify_client_{c["id"]}') == 'true'
        for c in all_clients
    }
    settings_model.set_setting('notify_clients', json.dumps(notify_map))
    flash('Settings saved.', 'success')
    return redirect(url_for('settings.index'))
