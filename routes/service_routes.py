from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import fetch_one, fetch_all, execute_query
from utils.helpers import admin_required

service_bp = Blueprint('service', __name__, url_prefix='/services')

@service_bp.route('/manage')
@admin_required
def manage_services():
    """Admin service package catalog management."""
    services = fetch_all("SELECT * FROM services ORDER BY created_at DESC")
    return render_template('services/manage.html', services=services)


@service_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_service():
    """Add new service package."""
    if request.method == 'POST':
        name = request.form.get('service_name', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('base_price', '').strip()
        duration = request.form.get('estimated_duration', '').strip()

        if not name or not price_str:
            flash('Service Name and Base Price are required.', 'danger')
            return render_template('services/add.html')

        try:
            price = float(price_str)
            if price < 0:
                flash('Base price must be a positive number.', 'danger')
                return render_template('services/add.html')
        except ValueError:
            flash('Invalid base price format.', 'danger')
            return render_template('services/add.html')

        execute_query(
            """INSERT INTO services (service_name, description, base_price, estimated_duration, status)
               VALUES (%s, %s, %s, %s, 'active')""",
            (name, description, price, duration or '1-2 Hours')
        )
        flash(f'Service package "{name}" created successfully.', 'success')
        return redirect(url_for('service.manage_services'))

    return render_template('services/add.html')


@service_bp.route('/<int:service_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_service(service_id):
    """Edit existing service package."""
    service = fetch_one("SELECT * FROM services WHERE id = %s", (service_id,))
    if not service:
        flash('Service not found.', 'danger')
        return redirect(url_for('service.manage_services'))

    if request.method == 'POST':
        name = request.form.get('service_name', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('base_price', '').strip()
        duration = request.form.get('estimated_duration', '').strip()
        status = request.form.get('status', 'active')

        if not name or not price_str:
            flash('Service Name and Base Price are required.', 'danger')
            return render_template('services/edit.html', service=service)

        try:
            price = float(price_str)
        except ValueError:
            flash('Invalid base price format.', 'danger')
            return render_template('services/edit.html', service=service)

        execute_query(
            """UPDATE services 
               SET service_name = %s, description = %s, base_price = %s, estimated_duration = %s, status = %s
               WHERE id = %s""",
            (name, description, price, duration, status, service_id)
        )
        flash('Service package updated successfully.', 'success')
        return redirect(url_for('service.manage_services'))

    return render_template('services/edit.html', service=service)


@service_bp.route('/<int:service_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_service_status(service_id):
    """Activate or deactivate a service without breaking historical references."""
    service = fetch_one("SELECT status FROM services WHERE id = %s", (service_id,))
    if service:
        new_status = 'inactive' if service['status'] == 'active' else 'active'
        execute_query("UPDATE services SET status = %s WHERE id = %s", (new_status, service_id))
        flash(f'Service status changed to {new_status}.', 'info')
    return redirect(url_for('service.manage_services'))
