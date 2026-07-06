import os
from datetime import date
from flask import Blueprint, render_template, request, send_file
from services import trip_service
from services import export_service
from services.auth import login_required
from models import trip as trip_model
from models import payment as payment_model

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    stats = trip_service.get_dashboard_stats()
    all_trips = trip_model.get_all_trips()
    active_trips = [t for t in all_trips if t['status'] not in ('paid', 'cancelled')]
    payment_summary = payment_model.get_payment_summary()
    return render_template('dashboard.html', stats=stats, trips=active_trips,
                           payment_summary=payment_summary)


@dashboard_bp.route('/reports/monthly/export')
@login_required
def export_monthly_report():
    today = date.today()
    month = int(request.args.get('month', today.month))
    year = int(request.args.get('year', today.year))
    file_path = export_service.export_monthly_report(month, year)
    return send_file(file_path, as_attachment=True,
                     download_name=os.path.basename(file_path),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
