from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import fetch_one, fetch_all, execute_query
from utils.helpers import admin_required

parts_bp = Blueprint('parts', __name__, url_prefix='/parts')

@parts_bp.route('/')
@admin_required
def list_parts():
    """List all spare parts in inventory with stock levels and usage stats."""
    search = request.args.get('search', '').strip()

    query = """
        SELECT sp.*,
               COALESCE((SELECT SUM(rp.quantity_used) FROM repair_parts rp WHERE rp.part_id = sp.id), 0) as total_used
        FROM spare_parts sp
    """
    params = []
    if search:
        query += " WHERE sp.part_name LIKE %s OR sp.part_number LIKE %s"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY sp.part_name ASC"
    parts = fetch_all(query, tuple(params))

    # Calculate inventory totals
    total_items = len(parts)
    low_stock_count = len([p for p in parts if p['quantity'] <= 5])
    total_valuation = sum([float(p['quantity']) * float(p['unit_price']) for p in parts])

    return render_template(
        'parts/list.html',
        parts=parts,
        search=search,
        total_items=total_items,
        low_stock_count=low_stock_count,
        total_valuation=total_valuation
    )


@parts_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_part():
    """Add a new spare part to inventory."""
    if request.method == 'POST':
        part_name = request.form.get('part_name', '').strip()
        part_number = request.form.get('part_number', '').strip().upper()
        quantity_str = request.form.get('quantity', '').strip()
        price_str = request.form.get('unit_price', '').strip()
        description = request.form.get('description', '').strip()

        if not part_name or not part_number or not quantity_str or not price_str:
            flash('Part Name, Part Number, Stock Quantity, and Unit Price are required.', 'danger')
            return render_template('parts/add.html', form=request.form)

        try:
            quantity = int(quantity_str)
            unit_price = float(price_str)
            if quantity < 0 or unit_price < 0:
                flash('Quantity and Unit Price must be non-negative values.', 'danger')
                return render_template('parts/add.html', form=request.form)
        except ValueError:
            flash('Invalid format for quantity or price.', 'danger')
            return render_template('parts/add.html', form=request.form)

        # Unique part number check
        existing = fetch_one("SELECT id FROM spare_parts WHERE UPPER(part_number) = %s", (part_number,))
        if existing:
            flash(f'A part with part number "{part_number}" already exists in inventory.', 'warning')
            return render_template('parts/add.html', form=request.form)

        execute_query(
            """INSERT INTO spare_parts (part_name, part_number, quantity, unit_price, description)
               VALUES (%s, %s, %s, %s, %s)""",
            (part_name, part_number, quantity, unit_price, description)
        )
        flash(f'Spare part "{part_name}" ({part_number}) registered in inventory.', 'success')
        return redirect(url_for('parts.list_parts'))

    return render_template('parts/add.html', form={})


@parts_bp.route('/<int:part_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_part(part_id):
    """Edit spare part details and stock."""
    part = fetch_one("SELECT * FROM spare_parts WHERE id = %s", (part_id,))
    if not part:
        flash('Spare part not found.', 'danger')
        return redirect(url_for('parts.list_parts'))

    if request.method == 'POST':
        part_name = request.form.get('part_name', '').strip()
        part_number = request.form.get('part_number', '').strip().upper()
        quantity_str = request.form.get('quantity', '').strip()
        price_str = request.form.get('unit_price', '').strip()
        description = request.form.get('description', '').strip()

        if not part_name or not part_number or not quantity_str or not price_str:
            flash('All primary fields are required.', 'danger')
            return render_template('parts/edit.html', part=part)

        try:
            quantity = int(quantity_str)
            unit_price = float(price_str)
            if quantity < 0 or unit_price < 0:
                flash('Quantity and Unit Price must be non-negative.', 'danger')
                return render_template('parts/edit.html', part=part)
        except ValueError:
            flash('Invalid numeric format for quantity or price.', 'danger')
            return render_template('parts/edit.html', part=part)

        # Duplicate part number check
        existing = fetch_one("SELECT id FROM spare_parts WHERE UPPER(part_number) = %s AND id != %s", (part_number, part_id))
        if existing:
            flash(f'Part number "{part_number}" is already used by another item.', 'warning')
            return render_template('parts/edit.html', part=part)

        execute_query(
            """UPDATE spare_parts 
               SET part_name = %s, part_number = %s, quantity = %s, unit_price = %s, description = %s
               WHERE id = %s""",
            (part_name, part_number, quantity, unit_price, description, part_id)
        )
        flash('Spare part updated successfully.', 'success')
        return redirect(url_for('parts.list_parts'))

    return render_template('parts/edit.html', part=part)


@parts_bp.route('/<int:part_id>/delete', methods=['POST'])
@admin_required
def delete_part(part_id):
    """Delete a spare part from inventory if not referenced in historical repairs."""
    used_check = fetch_one("SELECT id FROM repair_parts WHERE part_id = %s LIMIT 1", (part_id,))
    if used_check:
        flash('Cannot delete this spare part because it is referenced in past vehicle repairs. Set quantity to 0 instead.', 'warning')
        return redirect(url_for('parts.list_parts'))

    execute_query("DELETE FROM spare_parts WHERE id = %s", (part_id,))
    flash('Spare part removed from inventory.', 'info')
    return redirect(url_for('parts.list_parts'))
