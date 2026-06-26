from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import vehicle as vehicle_model

vehicles_bp = Blueprint('vehicles', __name__, url_prefix='/vehicles')


@vehicles_bp.route('/')
def list_vehicles():
    vehicles = vehicle_model.get_all_vehicles()
    return render_template('vehicles/list.html', vehicles=vehicles)


@vehicles_bp.route('/create', methods=['GET'])
def create_form():
    return render_template('vehicles/create.html')


@vehicles_bp.route('/create', methods=['POST'])
def create():
    try:
        vehicle_model.create_vehicle(
            plate_number=request.form['plate_number'].strip().upper(),
            vehicle_type=request.form['vehicle_type'],
            capacity_tons=float(request.form['capacity_tons']),
        )
        flash('Vehicle added successfully.', 'success')
        return redirect(url_for('vehicles.list_vehicles'))
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('vehicles.create_form'))


@vehicles_bp.route('/<int:vehicle_id>/edit', methods=['GET'])
def edit_form(vehicle_id: int):
    vehicle = vehicle_model.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        flash('Vehicle not found.', 'error')
        return redirect(url_for('vehicles.list_vehicles'))
    return render_template('vehicles/edit.html', vehicle=vehicle)


@vehicles_bp.route('/<int:vehicle_id>/edit', methods=['POST'])
def edit(vehicle_id: int):
    try:
        vehicle_model.update_vehicle(
            vehicle_id,
            plate_number=request.form['plate_number'].strip().upper(),
            vehicle_type=request.form['vehicle_type'],
            capacity_tons=float(request.form['capacity_tons']),
            status=request.form['status'],
        )
        flash('Vehicle updated.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('vehicles.list_vehicles'))


@vehicles_bp.route('/<int:vehicle_id>/delete', methods=['POST'])
def delete(vehicle_id: int):
    vehicle_model.delete_vehicle(vehicle_id)
    flash('Vehicle deleted.', 'success')
    return redirect(url_for('vehicles.list_vehicles'))
