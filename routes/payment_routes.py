from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import payment as payment_model
from models import trip as trip_model
from models import client as client_model
from services.auth import login_required, get_current_user

payment_bp = Blueprint('payments', __name__, url_prefix='/payments')


@payment_bp.route('/')
@login_required
def list_payments():
    status = request.args.get('status', '')
    client_id = request.args.get('client_id', '')
    trips = payment_model.get_all_payments(
        client_filter=int(client_id) if client_id else None,
        status_filter=status or None,
    )
    clients = client_model.get_all_clients()
    summary = payment_model.get_payment_summary()
    return render_template('payments/list.html', trips=trips, clients=clients,
                           selected_status=status, selected_client=client_id, summary=summary)


@payment_bp.route('/dues')
@login_required
def dues():
    dues_list = payment_model.get_client_dues()
    summary = payment_model.get_payment_summary()
    dues_with_trips = [
        {'client': row, 'trips': payment_model.get_client_pending_trips(row['client_id'])}
        for row in dues_list
    ]
    return render_template('payments/dues.html', dues=dues_with_trips, summary=summary)


@payment_bp.route('/record/<int:trip_id>', methods=['GET'])
@login_required
def record_form(trip_id: int):
    trip = trip_model.get_trip_by_id(trip_id)
    if not trip:
        flash('Trip not found.', 'error')
        return redirect(url_for('payments.list_payments'))
    payments = payment_model.get_payments_for_trip(trip_id)
    remaining = trip['freight_amount'] - trip['total_received']
    today_str = date.today().strftime('%d-%m-%Y')
    return render_template('payments/record.html', trip=trip, payments=payments,
                           remaining=remaining, today=today_str)


@payment_bp.route('/record/<int:trip_id>', methods=['POST'])
@login_required
def record(trip_id: int):
    trip = trip_model.get_trip_by_id(trip_id)
    if not trip:
        flash('Trip not found.', 'error')
        return redirect(url_for('payments.list_payments'))
    try:
        amount = float(request.form['amount'])
        payment_mode = request.form['payment_mode']
        payment_reference = request.form.get('payment_reference', '') or None
        payment_date = request.form['payment_date']
        notes = request.form.get('notes', '') or None
        current = get_current_user()
        recorded_by = current['full_name'] if current else None

        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        remaining = trip['freight_amount'] - trip['total_received']
        if amount > remaining:
            raise ValueError(f"Amount exceeds remaining balance of {remaining}.")

        payment_model.create_payment(trip_id, amount, payment_mode, payment_reference,
                                     payment_date, notes, recorded_by)
        flash('Payment recorded successfully.', 'success')
        return redirect(url_for('payments.list_payments'))
    except (ValueError, KeyError) as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('payments.record_form', trip_id=trip_id))
