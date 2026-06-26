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


@clients_bp.route('/<int:client_id>/edit', methods=['GET'])
def edit_form(client_id: int):
    client = client_model.get_client_by_id(client_id)
    if not client:
        flash('Client not found.', 'error')
        return redirect(url_for('clients.list_clients'))
    return render_template('clients/edit.html', client=client)


@clients_bp.route('/<int:client_id>/edit', methods=['POST'])
def edit(client_id: int):
    try:
        client_model.update_client(
            client_id,
            name=request.form['name'].strip(),
            phone=request.form['phone'].strip(),
            email=request.form.get('email', '').strip(),
            address=request.form.get('address', '').strip(),
            gst_number=request.form.get('gst_number', '').strip(),
        )
        flash('Client updated.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('clients.list_clients'))


@clients_bp.route('/<int:client_id>/delete', methods=['POST'])
def delete(client_id: int):
    client_model.delete_client(client_id)
    flash('Client deleted.', 'success')
    return redirect(url_for('clients.list_clients'))
