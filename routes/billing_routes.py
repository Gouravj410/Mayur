from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import fetch_one, fetch_all, execute_query
from utils.helpers import login_required, customer_required, admin_required

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/admin')
@admin_required
def admin_billing():
    """Admin view of all bills and revenue summaries."""
    status_filter = request.args.get('status', '').strip()

    query = """
        SELECT bl.*, b.booking_date, b.booking_status,
               u.full_name as customer_name, u.phone as customer_phone,
               v.registration_number, v.brand, v.model,
               s.service_name,
               p.payment_method, p.payment_date, p.transaction_reference
        FROM bills bl
        JOIN bookings b ON bl.booking_id = b.id
        JOIN users u ON b.customer_id = u.id
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN services s ON b.service_id = s.id
        LEFT JOIN payments p ON bl.id = p.bill_id
    """
    params = []
    if status_filter:
        query += " WHERE bl.payment_status = %s"
        params.append(status_filter)

    query += " ORDER BY bl.bill_date DESC"
    bills = fetch_all(query, tuple(params))

    # Revenue metrics
    total_billed = sum([float(b['total_amount']) for b in bills])
    total_collected = sum([float(b['total_amount']) for b in bills if b['payment_status'] == 'Paid'])
    total_pending = sum([float(b['total_amount']) for b in bills if b['payment_status'] == 'Pending'])

    return render_template(
        'billing/admin_bills.html',
        bills=bills,
        current_status=status_filter,
        total_billed=total_billed,
        total_collected=total_collected,
        total_pending=total_pending
    )


@billing_bp.route('/my-bills')
@customer_required
def customer_bills():
    """Customer view of their invoices."""
    user_id = session.get('user_id')

    bills = fetch_all(
        """SELECT bl.*, b.booking_date, b.booking_status,
                  v.registration_number, v.brand, v.model,
                  s.service_name,
                  p.payment_method, p.payment_date
           FROM bills bl
           JOIN bookings b ON bl.booking_id = b.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           LEFT JOIN payments p ON bl.id = p.bill_id
           WHERE b.customer_id = %s
           ORDER BY bl.bill_date DESC""",
        (user_id,)
    )

    return render_template('billing/customer_bills.html', bills=bills)


@billing_bp.route('/<int:bill_id>')
@login_required
def view_bill(bill_id):
    """View / Print official invoice."""
    user_id = session.get('user_id')
    role = session.get('role')

    bill = fetch_one(
        """SELECT bl.*, b.booking_date, b.booking_time, b.problem_description, b.admin_notes, b.customer_id,
                  u.full_name as customer_name, u.email as customer_email, u.phone as customer_phone, u.address as customer_address,
                  v.registration_number, v.brand, v.model, v.manufacturing_year, v.fuel_type, v.vehicle_color,
                  s.service_name, s.description as service_desc,
                  r.id as repair_id, r.diagnosis, r.work_performed, r.repair_status, r.start_date, r.completion_date,
                  p.amount as paid_amount, p.payment_method, p.payment_date, p.payment_status as p_status, p.transaction_reference
           FROM bills bl
           JOIN bookings b ON bl.booking_id = b.id
           JOIN users u ON b.customer_id = u.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           LEFT JOIN repairs r ON b.id = r.booking_id
           LEFT JOIN payments p ON bl.id = p.bill_id
           WHERE bl.id = %s""",
        (bill_id,)
    )

    if not bill:
        flash('Bill record not found.', 'danger')
        return redirect(url_for('customer.dashboard') if role == 'customer' else url_for('billing.admin_billing'))

    # Security check: customer cannot view another customer's bill
    if role == 'customer' and bill['customer_id'] != user_id:
        flash('Unauthorized invoice access.', 'danger')
        return redirect(url_for('customer.dashboard'))

    # Fetch parts used
    parts_used = []
    if bill.get('repair_id'):
        parts_used = fetch_all(
            """SELECT rp.*, sp.part_name, sp.part_number
               FROM repair_parts rp
               JOIN spare_parts sp ON rp.part_id = sp.id
               WHERE rp.repair_id = %s""",
            (bill['repair_id'],)
        )

    return render_template('billing/view_bill.html', bill=bill, parts_used=parts_used)


@billing_bp.route('/<int:bill_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_bill(bill_id):
    """Admin can adjust service labor charges."""
    bill = fetch_one(
        """SELECT bl.*, u.full_name as customer_name, v.registration_number, s.service_name
           FROM bills bl
           JOIN bookings b ON bl.booking_id = b.id
           JOIN users u ON b.customer_id = u.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           WHERE bl.id = %s""",
        (bill_id,)
    )

    if not bill:
        flash('Bill not found.', 'danger')
        return redirect(url_for('billing.admin_billing'))

    if request.method == 'POST':
        service_charge = float(request.form.get('service_charge', 0.0))
        parts_charge = float(bill['parts_charge'])
        total_amount = service_charge + parts_charge
        payment_status = request.form.get('payment_status', bill['payment_status'])

        execute_query(
            """UPDATE bills 
               SET service_charge = %s, total_amount = %s, payment_status = %s
               WHERE id = %s""",
            (service_charge, total_amount, payment_status, bill_id)
        )
        flash('Bill updated successfully.', 'success')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))

    return render_template('billing/edit_bill.html', bill=bill)


@billing_bp.route('/<int:bill_id>/pay', methods=['GET', 'POST'])
@admin_required
def record_payment(bill_id):
    """Record receipt of payment for a bill."""
    bill = fetch_one(
        """SELECT bl.*, u.full_name as customer_name, v.registration_number, s.service_name
           FROM bills bl
           JOIN bookings b ON bl.booking_id = b.id
           JOIN users u ON b.customer_id = u.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           WHERE bl.id = %s""",
        (bill_id,)
    )

    if not bill:
        flash('Bill not found.', 'danger')
        return redirect(url_for('billing.admin_billing'))

    if bill['payment_status'] == 'Paid':
        flash('Payment has already been marked as Paid for this invoice.', 'info')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))

    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'Cash')
        amount = float(request.form.get('amount', bill['total_amount']))
        tx_ref = request.form.get('transaction_reference', '').strip()

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Check existing payment row
        existing_p = fetch_one("SELECT id FROM payments WHERE bill_id = %s", (bill_id,))
        if existing_p:
            execute_query(
                """UPDATE payments 
                   SET amount = %s, payment_method = %s, payment_date = %s, payment_status = 'Paid', transaction_reference = %s
                   WHERE bill_id = %s""",
                (amount, payment_method, now_str, tx_ref, bill_id)
            )
        else:
            execute_query(
                """INSERT INTO payments (bill_id, amount, payment_method, payment_date, payment_status, transaction_reference)
                   VALUES (%s, %s, %s, %s, 'Paid', %s)""",
                (bill_id, amount, payment_method, now_str, tx_ref)
            )

        # Update bill status
        execute_query("UPDATE bills SET payment_status = 'Paid' WHERE id = %s", (bill_id,))

        flash(f'Payment of ₹{amount:,.2f} recorded via {payment_method}.', 'success')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))

    return render_template('billing/record_payment.html', bill=bill)
