from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import settings as settings_model
from services.whatsapp_service import check_whatsapp_status

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

SETTINGS_KEYS = [
    'company_name', 'company_address', 'company_phone', 'company_gst',
    'bank_name', 'bank_account', 'bank_ifsc',
    'whatsapp_enabled', 'whatsapp_owner_phone', 'daily_summary_time',
    'traccar_url', 'traccar_enabled',
]


@settings_bp.route('/')
def index():
    current = settings_model.get_all_settings()
    wa_connected = check_whatsapp_status()
    return render_template('settings.html', settings=current, wa_connected=wa_connected)


@settings_bp.route('/save', methods=['POST'])
def save():
    for key in SETTINGS_KEYS:
        value = request.form.get(key, '')
        settings_model.set_setting(key, value)
    flash('Settings saved.', 'success')
    return redirect(url_for('settings.index'))
