from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from models import user as user_model
from services.auth import login_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard.index'))

    no_users = user_model.count_users() == 0

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        user = user_model.get_user_by_username(identifier)
        if not user:
            user = user_model.get_user_by_email(identifier)

        if not user or not user_model.verify_password(user['password_hash'], password):
            flash('Invalid username or password.', 'error')
            return render_template('auth/login.html', no_users=no_users)

        if not user['is_active']:
            flash('Your account has been deactivated. Contact admin.', 'error')
            return render_template('auth/login.html', no_users=no_users)

        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['full_name'] = user['full_name']

        user_model.update_last_login(user['id'])

        next_url = request.args.get('next') or url_for('dashboard.index')
        return redirect(next_url)

    return render_template('auth/login.html', no_users=no_users)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    total = user_model.count_users()
    is_first = total == 0

    # After first user, only admins can sign up new users
    if not is_first and session.get('role') != 'admin':
        flash('Account creation requires admin access.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        errors = []
        if not all([full_name, email, username, password]):
            errors.append('All fields are required.')
        if password != confirm:
            errors.append('Passwords do not match.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if user_model.get_user_by_username(username):
            errors.append(f'Username "{username}" is already taken.')
        if user_model.get_user_by_email(email):
            errors.append(f'Email "{email}" is already registered.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('auth/signup.html', is_first=is_first,
                                   form=request.form)

        role = 'admin' if is_first else 'dispatcher'
        user_model.create_user(username, email, password, full_name, role)
        flash(f'Account created for {full_name}. Please sign in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html', is_first=is_first, form={})


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    user = user_model.get_user_by_id(session['user_id'])
    return render_template('auth/profile.html', user=user)


@auth_bp.route('/profile/info', methods=['POST'])
@login_required
def update_profile_info():
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()

    if not full_name or not email:
        flash('Name and email are required.', 'error')
        return redirect(url_for('auth.profile'))

    existing = user_model.get_user_by_email(email)
    if existing and existing['id'] != session['user_id']:
        flash('That email is already used by another account.', 'error')
        return redirect(url_for('auth.profile'))

    user_model.update_user(session['user_id'], full_name=full_name, email=email)
    session['full_name'] = full_name
    flash('Profile updated.', 'success')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/profile/password', methods=['POST'])
@login_required
def update_password():
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')

    user = user_model.get_user_by_id(session['user_id'])

    if not user_model.verify_password(user['password_hash'], current_pw):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('auth.profile'))
    if len(new_pw) < 6:
        flash('New password must be at least 6 characters.', 'error')
        return redirect(url_for('auth.profile'))
    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('auth.profile'))

    from werkzeug.security import generate_password_hash
    user_model.update_user(session['user_id'], password_hash=generate_password_hash(new_pw))
    flash('Password changed successfully.', 'success')
    return redirect(url_for('auth.profile'))
