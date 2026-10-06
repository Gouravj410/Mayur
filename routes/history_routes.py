from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import fetch_one, fetch_all
from utils.helpers import login_required, customer_required

history_bp = Blueprint('history', __name__, url_prefix='/history')

@history_bp.route('/')
@login_required
def customer_history():
    """Customer overview of service history across all their registered vehicles."""
    user_id = session.get('user_id')
    role = session.get('role')

    if role == 'admin':
        return redirect(url_for('report.reports_dashboard'))

    # Fetch vehicles
    vehicles = fetch_all("SELECT * FROM vehicles WHERE customer_id = %s ORDER BY brand ASC", (user_id,))
    
    selected_vehicle_id = request.args.get('vehicle_id', type=int)

    # Base query for completed or historical service bookings
    query = """
        SELECT b.id as booking_id, b.booking_date, b.booking_time, b.problem_description, b.booking_status, b.created_at,
               v.id as vehicle_id, v.registration_number, v.brand, v.model, v.fuel_type, v.manufacturing_year,
               s.service_name, s.base_price,
               r.id as repair_id, r.diagnosis, r.work_performed, r.repair_notes, r.completion_date,
               bl.id as bill_id, bl.service_charge, bl.parts_charge, bl.total_amount, bl.payment_status,
               p.payment_method, p.payment_date
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN services s ON b.service_id = s.id
        LEFT JOIN repairs r ON b.id = r.booking_id
        LEFT JOIN bills bl ON b.id = bl.booking_id
        LEFT JOIN payments p ON bl.id = p.bill_id
        WHERE b.customer_id = %s AND b.booking_status = 'Completed'
    """
    params = [user_id]

    if selected_vehicle_id:
        query += " AND b.vehicle_id = %s"
        params.append(selected_vehicle_id)

    query += " ORDER BY b.booking_date DESC"
    records = fetch_all(query, tuple(params))

    # For each record, load replaced parts
    for rec in records:
        if rec['repair_id']:
            rec['parts'] = fetch_all(
                """SELECT rp.*, sp.part_name, sp.part_number
                   FROM repair_parts rp
                   JOIN spare_parts sp ON rp.part_id = sp.id
                   WHERE rp.repair_id = %s""",
                (rec['repair_id'],)
            )
        else:
            rec['parts'] = []

    return render_template(
        'history/customer_history.html',
        vehicles=vehicles,
        records=records,
        selected_vehicle_id=selected_vehicle_id
    )


@history_bp.route('/vehicle/<int:vehicle_id>')
@login_required
def vehicle_history(vehicle_id):
    """Detailed lifecycle service history for a specific vehicle."""
    user_id = session.get('user_id')
    role = session.get('role')

    vehicle = fetch_one("SELECT * FROM vehicles WHERE id = %s", (vehicle_id,))
    if not vehicle:
        flash('Vehicle not found.', 'danger')
        return redirect(url_for('customer.dashboard') if role == 'customer' else url_for('admin.dashboard'))

    # Security check for customers
    if role == 'customer' and vehicle['customer_id'] != user_id:
        flash('Unauthorized vehicle history access.', 'danger')
        return redirect(url_for('customer.dashboard'))

    # Owner details if viewed by admin
    owner = fetch_one("SELECT full_name, email, phone FROM users WHERE id = %s", (vehicle['customer_id'],))

    # Fetch completed services
    records = fetch_all(
        """SELECT b.id as booking_id, b.booking_date, b.booking_time, b.problem_description, b.booking_status,
                  s.service_name, s.base_price,
                  r.id as repair_id, r.diagnosis, r.work_performed, r.repair_notes, r.completion_date,
                  bl.id as bill_id, bl.service_charge, bl.parts_charge, bl.total_amount, bl.payment_status,
                  p.payment_method, p.payment_date
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           LEFT JOIN repairs r ON b.id = r.booking_id
           LEFT JOIN bills bl ON b.id = bl.booking_id
           LEFT JOIN payments p ON bl.id = p.bill_id
           WHERE b.vehicle_id = %s AND b.booking_status = 'Completed'
           ORDER BY b.booking_date DESC""",
        (vehicle_id,)
    )

    for rec in records:
        if rec['repair_id']:
            rec['parts'] = fetch_all(
                """SELECT rp.*, sp.part_name, sp.part_number
                   FROM repair_parts rp
                   JOIN spare_parts sp ON rp.part_id = sp.id
                   WHERE rp.repair_id = %s""",
                (rec['repair_id'],)
            )
        else:
            rec['parts'] = []

    total_expenditure = sum([float(r['total_amount']) for r in records if r['total_amount']])

    return render_template(
        'history/vehicle_history.html',
        vehicle=vehicle,
        owner=owner,
        records=records,
        total_expenditure=total_expenditure
    )
