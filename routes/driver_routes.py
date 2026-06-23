from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import driver as driver_model
from models import vehicle as vehicle_model

drivers_bp = Blueprint('drivers', __name__, url_prefix='/drivers')


@drivers_bp.route('/')
def list_drivers():
    drivers = driver_model.get_all_drivers()
    return render_template('drivers/list.html', drivers=drivers)


@drivers_bp.route('/create', methods=['GET'])
def create_form():
    vehicles = vehicle_model.get_all_vehicles()
    return render_template('drivers/create.html', vehicles=vehicles)


@drivers_bp.route('/create', methods=['POST'])
def create():
    try:
        assigned_vehicle_id = request.form.get('assigned_vehicle_id') or None
        driver_model.create_driver(
            name=request.form['name'].strip(),
            phone=request.form['phone'].strip(),
            license_number=request.form['license_number'].strip(),
            assigned_vehicle_id=int(assigned_vehicle_id) if assigned_vehicle_id else None,
        )
        flash('Driver added successfully.', 'success')
        return redirect(url_for('drivers.list_drivers'))
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('drivers.create_form'))
