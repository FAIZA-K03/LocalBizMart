import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models import User, Business
from app.utils.helpers import validate_phone

auth_bp = Blueprint('auth', __name__, url_prefix='')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('browse.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'customer').strip().lower()

        # Validation
        errors = []
        if not name or len(name) < 2:
            errors.append("Please enter a valid full name.")
        if not email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            errors.append("Please enter a valid email address.")
        if not validate_phone(phone):
            errors.append("Please enter a valid 10 to 14 digit mobile phone number.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if role not in ['customer', 'owner']:
            errors.append("Invalid role selected.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('auth/register.html', name=name, email=email, phone=phone, role=role)

        # Check existing user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email address already exists. Please log in.", "warning")
            return redirect(url_for('auth.login'))

        # Create user
        new_user = User(
            name=name,
            email=email,
            phone=phone,
            role=role,
            status='active'
        )
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()

            # Automatically log in the newly registered user
            session.clear()
            session['user_id'] = new_user.user_id
            session['role'] = new_user.role
            session['name'] = new_user.name

            if role == 'owner':
                flash("Welcome to LocalBizMart! Please set up your business profile to start selling.", "success")
                return redirect(url_for('business.profile_edit'))
            else:
                flash("Registration successful! Welcome to LocalBizMart.", "success")
                return redirect(url_for('browse.index'))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while creating your account. Please try again.", "danger")
            return render_template('auth/register.html', name=name, email=email, phone=phone, role=role)

    return render_template('auth/register.html', role='customer')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        user_role = session.get('role')
        if user_role == 'owner':
            return redirect(url_for('business.dashboard'))
        elif user_role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('browse.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_url = request.args.get('next')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password. Please verify and try again.", "danger")
            return render_template('auth/login.html', email=email)

        # Check account status
        if not user.is_active_account:
            flash("Your account has been deactivated. Please contact the administrator for assistance.", "danger")
            return render_template('auth/login.html', email=email)

        # Successful login
        session.clear()
        session['user_id'] = user.user_id
        session['role'] = user.role
        session['name'] = user.name

        flash(f"Welcome back, {user.name}!", "success")

        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        if user.is_owner:
            # Check if business profile exists
            if not user.business:
                return redirect(url_for('business.profile_edit'))
            return redirect(url_for('business.dashboard'))
        elif user.is_admin:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('browse.index'))

    return render_template('auth/login.html')


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Dedicated administrative login portal."""
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email, role='admin').first()

        if not user or not user.check_password(password):
            flash("Invalid administrator credentials.", "danger")
            return render_template('auth/admin_login.html', email=email)

        if not user.is_active_account:
            flash("Administrator account is inactive.", "danger")
            return render_template('auth/admin_login.html', email=email)

        session.clear()
        session['user_id'] = user.user_id
        session['role'] = 'admin'
        session['name'] = user.name

        flash("Administrator authenticated successfully.", "success")
        return redirect(url_for('admin.dashboard'))

    return render_template('auth/admin_login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('browse.index'))
