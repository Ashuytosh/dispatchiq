import io
import os
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, send_file)
from models import trip as trip_model
from models import vehicle as vehicle_model
from models import driver as driver_model
from models import client as client_model
from models import document as document_model
from models import payment as payment_model
from services import trip_service
from services import lr_generator
from services import invoice_generator
from services import export_service
from services import tracker_service
from services.auth import login_required

trips_bp = Blueprint('trips', __name__, url_prefix='/trips')


@trips_bp.route('/')
def list_trips():
    status = request.args.get('status', '')
    client_id = request.args.get('client_id', '')
    trips = trip_model.get_all_trips(
        status_filter=status or None,
        client_filter=int(client_id) if client_id else None,
    )
    clients = client_model.get_all_clients()
    return render_template('trips/list.html', trips=trips, clients=clients,
                           selected_status=status, selected_client=client_id)


@trips_bp.route('/export')
@login_required
def export():
    status = request.args.get('status', '')
    client_id = request.args.get('client_id', '')
    file_path = export_service.export_trips_to_excel(
        filters={'status': status, 'client_id': client_id}
    )
    return send_file(file_path, as_attachment=True,
                     download_name=os.path.basename(file_path),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@trips_bp.route('/create', methods=['GET'])
def create_form():
    clients = client_model.get_all_clients()
    return render_template('trips/create.html', clients=clients)


@trips_bp.route('/create', methods=['POST'])
def create():
    try:
        trip_id = trip_service.create_new_trip(request.form)
        flash('Trip created successfully.', 'success')
        return redirect(url_for('trips.detail', trip_id=trip_id))
    except ValueError as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('trips.create_form'))


@trips_bp.route('/<int:trip_id>')
def detail(trip_id: int):
    trip = trip_model.get_trip_by_id(trip_id)
    if not trip:
        flash('Trip not found.', 'error')
        return redirect(url_for('trips.list_trips'))
    activity = trip_model.get_trip_activity(trip_id)
    available_vehicles = vehicle_model.get_available_vehicles()
    available_drivers = driver_model.get_available_drivers()
    payments = payment_model.get_payments_for_trip(trip_id)
    return render_template('trips/detail.html', trip=trip, activity=activity,
                           available_vehicles=available_vehicles,
                           available_drivers=available_drivers,
                           payments=payments,
                           traccar_configured=tracker_service.is_traccar_configured())


@trips_bp.route('/<int:trip_id>/assign', methods=['POST'])
def assign(trip_id: int):
    try:
        vehicle_id = int(request.form['vehicle_id'])
        driver_id = int(request.form['driver_id'])
        trip_service.assign_vehicle_and_driver(trip_id, vehicle_id, driver_id)
        flash('Vehicle and driver assigned.', 'success')
    except (ValueError, KeyError) as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('trips.detail', trip_id=trip_id))


@trips_bp.route('/<int:trip_id>/status', methods=['POST'])
def update_status(trip_id: int):
    new_status = request.form.get('new_status', '')
    try:
        trip_service.advance_trip_status(trip_id, new_status)
        flash(f'Status updated to {new_status.replace("_", " ").title()}.', 'success')
    except ValueError as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('trips.detail', trip_id=trip_id))


@trips_bp.route('/<int:trip_id>/cancel', methods=['POST'])
def cancel(trip_id: int):
    try:
        trip_service.cancel_trip(trip_id)
        flash('Trip cancelled.', 'success')
    except ValueError as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('trips.detail', trip_id=trip_id))


@trips_bp.route('/<int:trip_id>/lr')
def download_lr(trip_id: int):
    trip = trip_model.get_trip_by_id(trip_id)
    if not trip or not trip['lr_number']:
        flash('LR not available for this trip.', 'error')
        return redirect(url_for('trips.detail', trip_id=trip_id))
    doc = document_model.get_document(trip_id, 'lr')
    if doc and os.path.exists(doc['file_path']):
        return send_file(doc['file_path'], mimetype='application/pdf',
                         as_attachment=True, download_name=f"{trip['lr_number']}.pdf")
    pdf_bytes = lr_generator.generate_lr_pdf(trip)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{trip['lr_number']}.pdf",
    )


@trips_bp.route('/<int:trip_id>/invoice')
def download_invoice(trip_id: int):
    trip = trip_model.get_trip_by_id(trip_id)
    if not trip or not trip['invoice_number']:
        flash('Invoice not available for this trip.', 'error')
        return redirect(url_for('trips.detail', trip_id=trip_id))
    doc = document_model.get_document(trip_id, 'invoice')
    if doc and os.path.exists(doc['file_path']):
        return send_file(doc['file_path'], mimetype='application/pdf',
                         as_attachment=True, download_name=f"{trip['invoice_number']}.pdf")
    pdf_bytes = invoice_generator.generate_invoice_pdf(trip)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{trip['invoice_number']}.pdf",
    )
