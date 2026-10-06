from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import fetch_one, fetch_all, execute_query
from utils.helpers import admin_required

repair_bp = Blueprint('repair', __name__, url_prefix='/repairs')

def sync_repair_bill(booking_id):
    """
    Helper function to calculate parts charge and update/create bill.
    total_amount = service_charge + parts_charge
    """
    # 1. Fetch booking & service base price
    booking = fetch_one(
        """SELECT b.id, s.base_price, r.id as repair_id
           FROM bookings b
           JOIN services s ON b.service_id = s.id
           LEFT JOIN repairs r ON b.id = r.booking_id
           WHERE b.id = %s""",
        (booking_id,)
    )
    if not booking:
        return

    service_charge = float(booking['base_price']) if booking['base_price'] else 0.0

    # 2. Calculate sum of parts used
    parts_charge = 0.0
    if booking['repair_id']:
        parts_sum_row = fetch_one(
            """SELECT SUM(quantity_used * price_at_time_of_use) as total_parts
               FROM repair_parts
               WHERE repair_id = %s""",
            (booking['repair_id'],)
        )
        if parts_sum_row and parts_sum_row['total_parts']:
            parts_charge = float(parts_sum_row['total_parts'])

    total_amount = service_charge + parts_charge

    # 3. Insert or update bill
    existing_bill = fetch_one("SELECT id FROM bills WHERE booking_id = %s", (booking_id,))
    if existing_bill:
        execute_query(
            """UPDATE bills 
               SET service_charge = %s, parts_charge = %s, total_amount = %s
               WHERE id = %s""",
            (service_charge, parts_charge, total_amount, existing_bill['id'])
        )
    else:
        execute_query(
            """INSERT INTO bills (booking_id, service_charge, parts_charge, total_amount, payment_status)
               VALUES (%s, %s, %s, %s, 'Pending')""",
            (booking_id, service_charge, parts_charge, total_amount)
        )


@repair_bp.route('/admin')
@admin_required
def admin_repairs():
    """Admin view of all repair jobs."""
    status_filter = request.args.get('status', '').strip()

    query = """
        SELECT r.*, b.booking_date, b.booking_time, b.booking_status,
               u.full_name as customer_name,
               v.registration_number, v.brand, v.model,
               s.service_name
        FROM repairs r
        JOIN bookings b ON r.booking_id = b.id
        JOIN users u ON b.customer_id = u.id
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN services s ON b.service_id = s.id
    """
    params = []
    if status_filter:
        query += " WHERE r.repair_status = %s"
        params.append(status_filter)

    query += " ORDER BY r.created_at DESC"
    repairs = fetch_all(query, tuple(params))

    return render_template('repairs/admin_repairs.html', repairs=repairs, current_status=status_filter)


@repair_bp.route('/<int:repair_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_repair(repair_id):
    """View and update repair job card, technicians notes, diagnosis, status, and parts used."""
    repair = fetch_one(
        """SELECT r.*, b.id as booking_id, b.booking_date, b.booking_time, b.booking_status, b.problem_description,
                  u.full_name as customer_name, u.phone as customer_phone,
                  v.registration_number, v.brand, v.model, v.fuel_type,
                  s.service_name, s.base_price
           FROM repairs r
           JOIN bookings b ON r.booking_id = b.id
           JOIN users u ON b.customer_id = u.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           WHERE r.id = %s""",
        (repair_id,)
    )

    if not repair:
        flash('Repair job not found.', 'danger')
        return redirect(url_for('repair.admin_repairs'))

    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis', '').strip()
        work_performed = request.form.get('work_performed', '').strip()
        repair_notes = request.form.get('repair_notes', '').strip()
        repair_status = request.form.get('repair_status', '').strip()

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Logic for dates and matching booking status
        start_date = repair['start_date']
        completion_date = repair['completion_date']

        if repair_status in ('In Progress', 'Waiting for Parts') and not start_date:
            start_date = now_str
            execute_query("UPDATE bookings SET booking_status = 'In Service' WHERE id = %s", (repair['booking_id'],))

        if repair_status == 'Completed':
            if not start_date:
                start_date = now_str
            completion_date = now_str
            execute_query("UPDATE bookings SET booking_status = 'Completed' WHERE id = %s", (repair['booking_id'],))

        execute_query(
            """UPDATE repairs 
               SET diagnosis = %s, work_performed = %s, repair_notes = %s, repair_status = %s,
                   start_date = %s, completion_date = %s
               WHERE id = %s""",
            (diagnosis, work_performed, repair_notes, repair_status, start_date, completion_date, repair_id)
        )

        # Sync invoice calculation
        sync_repair_bill(repair['booking_id'])

        flash('Repair job record updated successfully.', 'success')
        return redirect(url_for('repair.edit_repair', repair_id=repair_id))

    # Fetch parts used in this repair
    parts_used = fetch_all(
        """SELECT rp.*, sp.part_name, sp.part_number, sp.quantity as available_stock
           FROM repair_parts rp
           JOIN spare_parts sp ON rp.part_id = sp.id
           WHERE rp.repair_id = %s""",
        (repair_id,)
    )

    # Fetch available parts for adding
    available_parts = fetch_all("SELECT * FROM spare_parts WHERE quantity > 0 ORDER BY part_name ASC")

    # Fetch bill summary
    bill = fetch_one("SELECT * FROM bills WHERE booking_id = %s", (repair['booking_id'],))

    return render_template(
        'repairs/edit_repair.html',
        repair=repair,
        parts_used=parts_used,
        available_parts=available_parts,
        bill=bill
    )


@repair_bp.route('/<int:repair_id>/add-part', methods=['POST'])
@admin_required
def add_part_to_repair(repair_id):
    """Add a spare part to repair and automatically deduct inventory stock."""
    part_id = request.form.get('part_id', type=int)
    quantity_used = request.form.get('quantity_used', type=int)

    if not part_id or not quantity_used or quantity_used <= 0:
        flash('Please select a valid part and positive quantity.', 'danger')
        return redirect(url_for('repair.edit_repair', repair_id=repair_id))

    repair = fetch_one("SELECT booking_id FROM repairs WHERE id = %s", (repair_id,))
    if not repair:
        flash('Repair not found.', 'danger')
        return redirect(url_for('repair.admin_repairs'))

    part = fetch_one("SELECT * FROM spare_parts WHERE id = %s", (part_id,))
    if not part:
        flash('Spare part not found.', 'danger')
        return redirect(url_for('repair.edit_repair', repair_id=repair_id))

    if part['quantity'] < quantity_used:
        flash(f'Insufficient inventory for "{part["part_name"]}". Available stock: {part["quantity"]}.', 'danger')
        return redirect(url_for('repair.edit_repair', repair_id=repair_id))

    # Check if part already used in this repair
    existing_rp = fetch_one("SELECT * FROM repair_parts WHERE repair_id = %s AND part_id = %s", (repair_id, part_id))
    if existing_rp:
        # Increase quantity used
        execute_query(
            "UPDATE repair_parts SET quantity_used = quantity_used + %s WHERE id = %s",
            (quantity_used, existing_rp['id'])
        )
    else:
        # Insert new repair_parts record
        execute_query(
            """INSERT INTO repair_parts (repair_id, part_id, quantity_used, price_at_time_of_use)
               VALUES (%s, %s, %s, %s)""",
            (repair_id, part_id, quantity_used, part['unit_price'])
        )

    # Deduct stock from spare_parts
    execute_query("UPDATE spare_parts SET quantity = quantity - %s WHERE id = %s", (quantity_used, part_id))

    # Recalculate bill
    sync_repair_bill(repair['booking_id'])

    flash(f'Added {quantity_used}x "{part["part_name"]}" to repair job. Inventory stock updated.', 'success')
    return redirect(url_for('repair.edit_repair', repair_id=repair_id))


@repair_bp.route('/<int:repair_id>/remove-part/<int:repair_part_id>', methods=['POST'])
@admin_required
def remove_part_from_repair(repair_id, repair_part_id):
    """Remove a spare part from repair and return quantity to stock."""
    rp = fetch_one("SELECT * FROM repair_parts WHERE id = %s AND repair_id = %s", (repair_part_id, repair_id))
    if not rp:
        flash('Part record not found in this repair.', 'danger')
        return redirect(url_for('repair.edit_repair', repair_id=repair_id))

    repair = fetch_one("SELECT booking_id FROM repairs WHERE id = %s", (repair_id,))

    # Return stock to inventory
    execute_query(
        "UPDATE spare_parts SET quantity = quantity + %s WHERE id = %s",
        (rp['quantity_used'], rp['part_id'])
    )

    # Delete repair_parts row
    execute_query("DELETE FROM repair_parts WHERE id = %s", (repair_part_id,))

    # Recalculate bill
    if repair:
        sync_repair_bill(repair['booking_id'])

    flash('Part removed from repair and returned to inventory stock.', 'info')
    return redirect(url_for('repair.edit_repair', repair_id=repair_id))
