from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import fetch_one, fetch_all, execute_query
from utils.helpers import login_required, customer_required

vehicle_bp = Blueprint('vehicle', __name__, url_prefix='/vehicles')

@vehicle_bp.route('/')
@login_required
def list_vehicles():
    """Lists vehicles. If customer, lists own vehicles; if admin, redirects to admin vehicle view."""
    user_id = session.get('user_id')
    role = session.get('role')

    if role == 'admin':
        return redirect(url_for('admin.list_all_vehicles'))

    vehicles = fetch_all(
        """SELECT v.*, 
                  (SELECT COUNT(*) FROM bookings b WHERE b.vehicle_id = v.id) as booking_count,
                  (SELECT COUNT(*) FROM bookings b WHERE b.vehicle_id = v.id AND b.booking_status = 'Completed') as completed_count
           FROM vehicles v
           WHERE v.customer_id = %s
           ORDER BY v.created_at DESC""",
        (user_id,)
    )
    return render_template('vehicles/list.html', vehicles=vehicles)


@vehicle_bp.route('/add', methods=['GET', 'POST'])
@customer_required
def add_vehicle():
    """Add a new vehicle for the authenticated customer."""
    user_id = session.get('user_id')

    if request.method == 'POST':
        reg_number = request.form.get('registration_number', '').strip().upper()
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        year_str = request.form.get('manufacturing_year', '').strip()
        fuel_type = request.form.get('fuel_type', '').strip()
        color = request.form.get('vehicle_color', '').strip()

        # Validation
        if not reg_number or not brand or not model or not year_str or not fuel_type or not color:
            flash('All vehicle fields are mandatory.', 'danger')
            return render_template('vehicles/add.html', form=request.form)

        try:
            year = int(year_str)
            current_year = datetime.now().year
            if year < 1980 or year > current_year + 1:
                flash(f'Please enter a realistic manufacturing year (1980 - {current_year + 1}).', 'danger')
                return render_template('vehicles/add.html', form=request.form)
        except ValueError:
            flash('Manufacturing year must be a 4-digit number.', 'danger')
            return render_template('vehicles/add.html', form=request.form)

        # Check duplicate registration number
        existing = fetch_one("SELECT id FROM vehicles WHERE UPPER(registration_number) = %s", (reg_number,))
        if existing:
            flash(f'A vehicle with registration number "{reg_number}" is already registered.', 'warning')
            return render_template('vehicles/add.html', form=request.form)

        # Insert vehicle
        try:
            execute_query(
                """INSERT INTO vehicles (customer_id, registration_number, brand, model, manufacturing_year, fuel_type, vehicle_color)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (user_id, reg_number, brand, model, year, fuel_type, color)
            )
            flash(f'Vehicle {brand} {model} ({reg_number}) registered successfully!', 'success')
            return redirect(url_for('vehicle.list_vehicles'))
        except Exception as e:
            flash(f'Error adding vehicle: {str(e)}', 'danger')

    return render_template('vehicles/add.html', form={})


@vehicle_bp.route('/<int:vehicle_id>/edit', methods=['GET', 'POST'])
@customer_required
def edit_vehicle(vehicle_id):
    """Edit vehicle details (only owner can edit)."""
    user_id = session.get('user_id')

    # Security check: ensure vehicle belongs to logged-in customer
    vehicle = fetch_one("SELECT * FROM vehicles WHERE id = %s AND customer_id = %s", (vehicle_id, user_id))
    if not vehicle:
        flash('Vehicle not found or you do not have permission to modify it.', 'danger')
        return redirect(url_for('vehicle.list_vehicles'))

    if request.method == 'POST':
        reg_number = request.form.get('registration_number', '').strip().upper()
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        year_str = request.form.get('manufacturing_year', '').strip()
        fuel_type = request.form.get('fuel_type', '').strip()
        color = request.form.get('vehicle_color', '').strip()

        if not reg_number or not brand or not model or not year_str or not fuel_type or not color:
            flash('All vehicle fields are mandatory.', 'danger')
            return render_template('vehicles/edit.html', vehicle=vehicle)

        try:
            year = int(year_str)
        except ValueError:
            flash('Invalid manufacturing year.', 'danger')
            return render_template('vehicles/edit.html', vehicle=vehicle)

        # Check duplicate registration on other vehicles
        existing = fetch_one("SELECT id FROM vehicles WHERE UPPER(registration_number) = %s AND id != %s", (reg_number, vehicle_id))
        if existing:
            flash(f'Another vehicle is already registered with {reg_number}.', 'warning')
            return render_template('vehicles/edit.html', vehicle=vehicle)

        execute_query(
            """UPDATE vehicles 
               SET registration_number = %s, brand = %s, model = %s, manufacturing_year = %s, fuel_type = %s, vehicle_color = %s
               WHERE id = %s AND customer_id = %s""",
            (reg_number, brand, model, year, fuel_type, color, vehicle_id, user_id)
        )
        flash('Vehicle details updated successfully.', 'success')
        return redirect(url_for('vehicle.list_vehicles'))

    return render_template('vehicles/edit.html', vehicle=vehicle)


@vehicle_bp.route('/<int:vehicle_id>/delete', methods=['POST'])
@customer_required
def delete_vehicle(vehicle_id):
    """Delete a vehicle owned by the customer."""
    user_id = session.get('user_id')

    vehicle = fetch_one("SELECT * FROM vehicles WHERE id = %s AND customer_id = %s", (vehicle_id, user_id))
    if not vehicle:
        flash('Vehicle not found or unauthorized access.', 'danger')
        return redirect(url_for('vehicle.list_vehicles'))

    # Check if there are active bookings
    active_b = fetch_one(
        """SELECT id FROM bookings 
           WHERE vehicle_id = %s AND booking_status IN ('Pending', 'Approved', 'In Service')""",
        (vehicle_id,)
    )
    if active_b:
        flash('Cannot delete vehicle while an active service booking is pending or in progress.', 'warning')
        return redirect(url_for('vehicle.list_vehicles'))

    execute_query("DELETE FROM vehicles WHERE id = %s AND customer_id = %s", (vehicle_id, user_id))
    flash(f'Vehicle {vehicle["registration_number"]} was removed successfully.', 'success')
    return redirect(url_for('vehicle.list_vehicles'))
