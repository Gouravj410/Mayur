import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import fetch_one, execute_query

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Customer self-registration with server-side validation."""
    if session.get('user_id'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server-side validation
        if not full_name or not email or not phone or not password:
            flash('All mandatory fields must be completed.', 'danger')
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone, address=address)

        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone, address=address)

        if len(phone) < 10 or not phone.replace('+', '').replace('-', '').isdigit():
            flash('Please enter a valid 10-digit mobile phone number.', 'danger')
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone, address=address)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone, address=address)

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter carefully.', 'danger')
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone, address=address)

        # Check for duplicate email
        existing_user = fetch_one("SELECT id FROM users WHERE email = %s", (email,))
        if existing_user:
            flash('An account with this email address is already registered. Please log in.', 'warning')
            return redirect(url_for('auth.login'))

        # Insert customer into database
        hashed_password = generate_password_hash(password)
        try:
            execute_query(
                """INSERT INTO users (full_name, email, phone, address, password_hash, role)
                   VALUES (%s, %s, %s, %s, %s, 'customer')""",
                (full_name, email, phone, address, hashed_password)
            )
            flash('Registration successful! You may now log in to your account.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Registration could not be completed: {str(e)}', 'danger')

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Customer Login portal."""
    if session.get('user_id'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        user = fetch_one("SELECT * FROM users WHERE email = %s", (email,))

        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('auth/login.html', email=email)

        # Check if user is customer
        if user['role'] != 'customer':
            flash('This portal is for customers. Administrators should log in via Admin Portal.', 'warning')
            return redirect(url_for('auth.admin_login'))

        # Set Session
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['user_email'] = user['email']
        session['role'] = 'customer'

        flash(f'Welcome back, {user["full_name"]}!', 'success')
        return redirect(url_for('customer.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Administrator Login portal."""
    if session.get('user_id') and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/admin_login.html')

        user = fetch_one("SELECT * FROM users WHERE email = %s", (email,))

        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid admin credentials.', 'danger')
            return render_template('auth/admin_login.html', email=email)

        if user['role'] != 'admin':
            flash('Access denied. Administrator privileges required.', 'danger')
            return render_template('auth/admin_login.html')

        # Set Admin Session
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['user_email'] = user['email']
        session['role'] = 'admin'

        flash('Logged in successfully as Administrator.', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('auth/admin_login.html')


@auth_bp.route('/logout')
def logout():
    """Clears user session and logs out."""
    session.clear()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('auth.login'))
