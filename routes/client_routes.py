from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import client as client_model

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')


@clients_bp.route('/')
def list_clients():
    clients = client_model.get_all_clients()
    return render_template('clients/list.html', clients=clients)


@clients_bp.route('/create', methods=['GET'])
def create_form():
    return render_template('clients/create.html')


@clients_bp.route('/create', methods=['POST'])
def create():
    try:
        client_model.create_client(
            name=request.form['name'].strip(),
            phone=request.form['phone'].strip(),
            email=request.form.get('email', '').strip(),
            address=request.form.get('address', '').strip(),
            gst_number=request.form.get('gst_number', '').strip(),
        )
        flash('Client added successfully.', 'success')
        return redirect(url_for('clients.list_clients'))
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('clients.create_form'))
