from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from database.db import fetch_one, fetch_all, execute_query
from utils.helpers import customer_required

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.route('/dashboard')
@customer_required
def dashboard():
    """Customer overview dashboard with stats, vehicles, and recent service bookings."""
    user_id = session.get('user_id')
    
    # 1. Fetch Customer info
    customer = fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))
    
    # 2. Fetch Customer vehicles
    vehicles = fetch_all("SELECT * FROM vehicles WHERE customer_id = %s ORDER BY created_at DESC", (user_id,))
    
    # 3. Fetch Bookings count & list
    bookings = fetch_all(
        """SELECT b.*, v.registration_number, v.brand, v.model, s.service_name, s.base_price,
                  r.repair_status
           FROM bookings b
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           LEFT JOIN repairs r ON b.id = r.booking_id
           WHERE b.customer_id = %s
           ORDER BY b.created_at DESC LIMIT 5""",
        (user_id,)
    )
    
    # 4. Metrics
    vehicle_count = len(vehicles)
    active_bookings = len([b for b in bookings if b['booking_status'] in ('Pending', 'Approved', 'In Service')])
    completed_bookings = len([b for b in bookings if b['booking_status'] == 'Completed'])
    
    # Total spent
    total_spent_row = fetch_one(
        """SELECT SUM(b.total_amount) as total
           FROM bills b
           JOIN bookings bk ON b.booking_id = bk.id
           WHERE bk.customer_id = %s AND b.payment_status = 'Paid'""",
        (user_id,)
    )
    total_spent = total_spent_row['total'] if total_spent_row and total_spent_row['total'] else 0.0

    return render_template(
        'customer/dashboard.html',
        customer=customer,
        vehicles=vehicles,
        bookings=bookings,
        vehicle_count=vehicle_count,
        active_bookings=active_bookings,
        completed_bookings=completed_bookings,
        total_spent=total_spent
    )


@customer_bp.route('/profile', methods=['GET', 'POST'])
@customer_required
def profile():
    """View and update customer profile."""
    user_id = session.get('user_id')

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        new_password = request.form.get('new_password', '').strip()

        if not full_name or not phone:
            flash('Name and Phone number are required.', 'danger')
            return redirect(url_for('customer.profile'))

        if len(phone) < 10:
            flash('Please enter a valid 10-digit mobile number.', 'danger')
            return redirect(url_for('customer.profile'))

        if new_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
                return redirect(url_for('customer.profile'))
            new_hash = generate_password_hash(new_password)
            execute_query(
                """UPDATE users SET full_name = %s, phone = %s, address = %s, password_hash = %s
                   WHERE id = %s""",
                (full_name, phone, address, new_hash, user_id)
            )
        else:
            execute_query(
                """UPDATE users SET full_name = %s, phone = %s, address = %s
                   WHERE id = %s""",
                (full_name, phone, address, user_id)
            )

        session['user_name'] = full_name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('customer.profile'))

    customer = fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))
    return render_template('customer/profile.html', customer=customer)
