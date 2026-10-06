from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import fetch_one, fetch_all, execute_query
from utils.helpers import login_required, customer_required, admin_required

booking_bp = Blueprint('booking', __name__, url_prefix='/bookings')

@booking_bp.route('/book', methods=['GET', 'POST'])
@customer_required
def book_service():
    """Customer service booking appointment form."""
    user_id = session.get('user_id')

    # Fetch customer's vehicles
    vehicles = fetch_all("SELECT * FROM vehicles WHERE customer_id = %s ORDER BY brand ASC", (user_id,))
    if not vehicles:
        flash('You must add at least one vehicle to your garage before booking a service.', 'warning')
        return redirect(url_for('vehicle.add_vehicle'))

    # Fetch active services
    services = fetch_all("SELECT * FROM services WHERE status = 'active' ORDER BY base_price ASC")

    selected_vehicle_id = request.args.get('vehicle_id', type=int)
    selected_service_id = request.args.get('service_id', type=int)

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id', type=int)
        service_id = request.form.get('service_id', type=int)
        booking_date = request.form.get('booking_date', '').strip()
        booking_time = request.form.get('booking_time', '').strip()
        problem_description = request.form.get('problem_description', '').strip()

        # Validation
        if not vehicle_id or not service_id or not booking_date or not booking_time:
            flash('Please select your vehicle, desired service, appointment date, and time slot.', 'danger')
            return render_template(
                'bookings/book.html',
                vehicles=vehicles,
                services=services,
                selected_vehicle_id=vehicle_id,
                selected_service_id=service_id
            )

        # Validate vehicle ownership
        veh_check = fetch_one("SELECT id FROM vehicles WHERE id = %s AND customer_id = %s", (vehicle_id, user_id))
        if not veh_check:
            flash('Invalid vehicle selection.', 'danger')
            return redirect(url_for('booking.book_service'))

        # Validate date is not in the past
        try:
            b_date_obj = datetime.strptime(booking_date, '%Y-%m-%d').date()
            if b_date_obj < date.today():
                flash('Appointment date cannot be in the past.', 'danger')
                return render_template(
                    'bookings/book.html',
                    vehicles=vehicles,
                    services=services,
                    selected_vehicle_id=vehicle_id,
                    selected_service_id=service_id
                )
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('booking.book_service'))

        # Insert booking
        booking_id, _ = execute_query(
            """INSERT INTO bookings (customer_id, vehicle_id, service_id, booking_date, booking_time, problem_description, booking_status)
               VALUES (%s, %s, %s, %s, %s, %s, 'Pending')""",
            (user_id, vehicle_id, service_id, booking_date, booking_time, problem_description)
        )

        flash('Your service booking request has been submitted successfully! Status: Pending Approval.', 'success')
        return redirect(url_for('booking.view_booking', booking_id=booking_id))

    return render_template(
        'bookings/book.html',
        vehicles=vehicles,
        services=services,
        selected_vehicle_id=selected_vehicle_id,
        selected_service_id=selected_service_id
    )


@booking_bp.route('/my-bookings')
@customer_required
def my_bookings():
    """Customer view of all their service bookings."""
    user_id = session.get('user_id')
    status_filter = request.args.get('status', '').strip()

    query = """
        SELECT b.*, v.registration_number, v.brand, v.model, s.service_name, s.base_price,
               r.id as repair_id, r.repair_status,
               bl.id as bill_id, bl.total_amount, bl.payment_status
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN services s ON b.service_id = s.id
        LEFT JOIN repairs r ON b.id = r.booking_id
        LEFT JOIN bills bl ON b.id = bl.booking_id
        WHERE b.customer_id = %s
    """
    params = [user_id]
    if status_filter:
        query += " AND b.booking_status = %s"
        params.append(status_filter)

    query += " ORDER BY b.created_at DESC"
    bookings = fetch_all(query, tuple(params))

    return render_template('bookings/my_bookings.html', bookings=bookings, current_status=status_filter)


@booking_bp.route('/<int:booking_id>')
@login_required
def view_booking(booking_id):
    """View details of a single booking, including repair progress and bill if available."""
    user_id = session.get('user_id')
    role = session.get('role')

    # Fetch booking
    booking = fetch_one(
        """SELECT b.*, u.full_name as customer_name, u.email as customer_email, u.phone as customer_phone,
                  v.registration_number, v.brand, v.model, v.manufacturing_year, v.fuel_type, v.vehicle_color,
                  s.service_name, s.description as service_desc, s.base_price, s.estimated_duration
           FROM bookings b
           JOIN users u ON b.customer_id = u.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           WHERE b.id = %s""",
        (booking_id,)
    )

    if not booking:
        flash('Booking record not found.', 'danger')
        return redirect(url_for('customer.dashboard') if role == 'customer' else url_for('admin.dashboard'))

    # Security: Customer can only view their own booking
    if role == 'customer' and booking['customer_id'] != user_id:
        flash('Unauthorized access to booking.', 'danger')
        return redirect(url_for('customer.dashboard'))

    # Fetch Repair details if exist
    repair = fetch_one("SELECT * FROM repairs WHERE booking_id = %s", (booking_id,))
    repair_parts = []
    if repair:
        repair_parts = fetch_all(
            """SELECT rp.*, sp.part_name, sp.part_number
               FROM repair_parts rp
               JOIN spare_parts sp ON rp.part_id = sp.id
               WHERE rp.repair_id = %s""",
            (repair['id'],)
        )

    # Fetch Bill if exists
    bill = fetch_one("SELECT * FROM bills WHERE booking_id = %s", (booking_id,))
    payment = None
    if bill:
        payment = fetch_one("SELECT * FROM payments WHERE bill_id = %s", (bill['id'],))

    return render_template(
        'bookings/view.html',
        booking=booking,
        repair=repair,
        repair_parts=repair_parts,
        bill=bill,
        payment=payment
    )


@booking_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@customer_required
def cancel_booking(booking_id):
    """Customer can cancel their pending booking."""
    user_id = session.get('user_id')
    booking = fetch_one("SELECT * FROM bookings WHERE id = %s AND customer_id = %s", (booking_id, user_id))

    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('booking.my_bookings'))

    if booking['booking_status'] != 'Pending':
        flash('Only "Pending" bookings can be cancelled. Active or completed work cannot be cancelled.', 'warning')
        return redirect(url_for('booking.view_booking', booking_id=booking_id))

    execute_query("UPDATE bookings SET booking_status = 'Cancelled' WHERE id = %s", (booking_id,))
    flash('Service booking has been cancelled.', 'info')
    return redirect(url_for('booking.my_bookings'))


@booking_bp.route('/admin/all')
@admin_required
def admin_bookings():
    """Admin view of all customer bookings with filter."""
    status_filter = request.args.get('status', '').strip()

    query = """
        SELECT b.*, u.full_name as customer_name, u.phone as customer_phone,
               v.registration_number, v.brand, v.model,
               s.service_name, s.base_price,
               r.id as repair_id, r.repair_status,
               bl.id as bill_id, bl.payment_status
        FROM bookings b
        JOIN users u ON b.customer_id = u.id
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN services s ON b.service_id = s.id
        LEFT JOIN repairs r ON b.id = r.booking_id
        LEFT JOIN bills bl ON b.id = bl.booking_id
    """
    params = []
    if status_filter:
        query += " WHERE b.booking_status = %s"
        params.append(status_filter)

    query += " ORDER BY b.created_at DESC"
    bookings = fetch_all(query, tuple(params))

    return render_template('admin/bookings.html', bookings=bookings, current_status=status_filter)


@booking_bp.route('/admin/<int:booking_id>/status', methods=['POST'])
@admin_required
def update_booking_status(booking_id):
    """Admin updates booking status (Approved, Rejected, In Service, Completed, etc.)."""
    new_status = request.form.get('booking_status', '').strip()
    admin_notes = request.form.get('admin_notes', '').strip()

    valid_statuses = ['Pending', 'Approved', 'Rejected', 'In Service', 'Completed', 'Cancelled']
    if new_status not in valid_statuses:
        flash('Invalid status provided.', 'danger')
        return redirect(url_for('booking.admin_bookings'))

    booking = fetch_one("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('booking.admin_bookings'))

    # Update booking
    execute_query(
        "UPDATE bookings SET booking_status = %s, admin_notes = %s WHERE id = %s",
        (new_status, admin_notes or booking.get('admin_notes', ''), booking_id)
    )

    # Automatically manage associated Repair and Bill records:
    if new_status == 'Approved':
        # Ensure repair record exists
        repair = fetch_one("SELECT id FROM repairs WHERE booking_id = %s", (booking_id,))
        if not repair:
            execute_query(
                """INSERT INTO repairs (booking_id, diagnosis, work_performed, repair_status)
                   VALUES (%s, 'Initial inspection queued upon booking approval.', 'Pending technician assignment.', 'Not Started')""",
                (booking_id,)
            )

    elif new_status == 'In Service':
        repair = fetch_one("SELECT id, start_date FROM repairs WHERE booking_id = %s", (booking_id,))
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not repair:
            execute_query(
                """INSERT INTO repairs (booking_id, diagnosis, work_performed, repair_status, start_date)
                   VALUES (%s, 'Diagnostic inspection in progress.', 'Service underway.', 'In Progress', %s)""",
                (booking_id, now_str)
            )
        else:
            execute_query(
                "UPDATE repairs SET repair_status = 'In Progress', start_date = COALESCE(start_date, %s) WHERE booking_id = %s",
                (now_str, booking_id)
            )

    elif new_status == 'Completed':
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execute_query(
            "UPDATE repairs SET repair_status = 'Completed', completion_date = COALESCE(completion_date, %s) WHERE booking_id = %s",
            (now_str, booking_id)
        )
        # Ensure bill exists with base price
        bill = fetch_one("SELECT id FROM bills WHERE booking_id = %s", (booking_id,))
        if not bill:
            service = fetch_one("SELECT base_price FROM services WHERE id = %s", (booking['service_id'],))
            s_price = service['base_price'] if service else 0.0
            execute_query(
                """INSERT INTO bills (booking_id, service_charge, parts_charge, total_amount, payment_status)
                   VALUES (%s, %s, 0.00, %s, 'Pending')""",
                (booking_id, s_price, s_price)
            )

    flash(f'Booking #{booking_id} status updated to "{new_status}".', 'success')
    return redirect(request.referrer or url_for('booking.admin_bookings'))
