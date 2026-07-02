from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import user as user_model
from services.auth import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
@admin_required
def list_users():
    users = user_model.get_all_users()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'dispatcher')

        errors = []
        if not all([full_name, email, username, password]):
            errors.append('All fields are required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if user_model.get_user_by_username(username):
            errors.append(f'Username "{username}" is already taken.')
        if user_model.get_user_by_email(email):
            errors.append(f'Email "{email}" is already registered.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('admin/add_user.html', form=request.form)

        user_model.create_user(username, email, password, full_name, role)
        flash(f'User {username} created successfully.', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/add_user.html', form={})


@admin_bp.route('/users/deactivate/<int:user_id>', methods=['POST'])
@admin_required
def deactivate_user(user_id: int):
    from flask import session
    if user_id == session.get('user_id'):
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('admin.list_users'))
    user_model.deactivate_user(user_id)
    flash('User deactivated.', 'success')
    return redirect(url_for('admin.list_users'))


@admin_bp.route('/users/role/<int:user_id>', methods=['POST'])
@admin_required
def change_role(user_id: int):
    from flask import session
    if user_id == session.get('user_id'):
        flash('You cannot change your own role.', 'error')
        return redirect(url_for('admin.list_users'))
    role = request.form.get('role', 'dispatcher')
    if role not in ('admin', 'dispatcher', 'viewer'):
        flash('Invalid role.', 'error')
        return redirect(url_for('admin.list_users'))
    user_model.update_user(user_id, role=role)
    flash('Role updated.', 'success')
    return redirect(url_for('admin.list_users'))
