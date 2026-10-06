from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import fetch_one, fetch_all, execute_query
from utils.helpers import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin centralized management dashboard with statistics and recent activity."""
    # 1. Total Customers
    cust_row = fetch_one("SELECT COUNT(*) as cnt FROM users WHERE role = 'customer'")
    total_customers = cust_row['cnt'] if cust_row else 0

    # 2. Total Vehicles
    veh_row = fetch_one("SELECT COUNT(*) as cnt FROM vehicles")
    total_vehicles = veh_row['cnt'] if veh_row else 0

    # 3. Pending Bookings
    pend_row = fetch_one("SELECT COUNT(*) as cnt FROM bookings WHERE booking_status = 'Pending'")
    pending_bookings = pend_row['cnt'] if pend_row else 0

    # 4. Active Services in Progress
    active_row = fetch_one("SELECT COUNT(*) as cnt FROM bookings WHERE booking_status IN ('Approved', 'In Service')")
    active_services = active_row['cnt'] if active_row else 0

    # 5. Completed Services
    comp_row = fetch_one("SELECT COUNT(*) as cnt FROM bookings WHERE booking_status = 'Completed'")
    completed_services = comp_row['cnt'] if comp_row else 0

    # 6. Total Distinct Spare Parts in stock
    parts_row = fetch_one("SELECT COUNT(*) as cnt, SUM(quantity) as total_qty FROM spare_parts")
    total_spare_parts = parts_row['cnt'] if parts_row else 0
    total_parts_stock = parts_row['total_qty'] if parts_row and parts_row['total_qty'] else 0

    # 7. Revenue & Pending Payments
    rev_row = fetch_one(
        """SELECT 
               COALESCE(SUM(total_amount), 0) as total_billed,
               COALESCE(SUM(CASE WHEN payment_status = 'Paid' THEN total_amount ELSE 0 END), 0) as total_revenue,
               COALESCE(SUM(CASE WHEN payment_status = 'Pending' THEN total_amount ELSE 0 END), 0) as pending_amount,
               COUNT(CASE WHEN payment_status = 'Pending' THEN 1 END) as pending_bills_count
           FROM bills"""
    )
    total_revenue = rev_row['total_revenue'] if rev_row else 0.0
    pending_amount = rev_row['pending_amount'] if rev_row else 0.0
    pending_payments_count = rev_row['pending_bills_count'] if rev_row else 0

    # Recent 6 Bookings
    recent_bookings = fetch_all(
        """SELECT b.*, u.full_name as customer_name, u.phone as customer_phone,
                  v.registration_number, v.brand, v.model,
                  s.service_name, s.base_price,
                  r.repair_status
           FROM bookings b
           JOIN users u ON b.customer_id = u.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           LEFT JOIN repairs r ON b.id = r.booking_id
           ORDER BY b.created_at DESC LIMIT 6"""
    )

    # Service breakdown for Chart.js
    service_stats = fetch_all(
        """SELECT s.service_name, COUNT(b.id) as booking_count
           FROM services s
           LEFT JOIN bookings b ON s.id = b.service_id
           GROUP BY s.id, s.service_name
           ORDER BY booking_count DESC"""
    )
    chart_labels = [s['service_name'] for s in service_stats]
    chart_data = [s['booking_count'] for s in service_stats]

    return render_template(
        'admin/dashboard.html',
        total_customers=total_customers,
        total_vehicles=total_vehicles,
        pending_bookings=pending_bookings,
        active_services=active_services,
        completed_services=completed_services,
        total_spare_parts=total_spare_parts,
        total_parts_stock=total_parts_stock,
        total_revenue=total_revenue,
        pending_amount=pending_amount,
        pending_payments_count=pending_payments_count,
        recent_bookings=recent_bookings,
        chart_labels=chart_labels,
        chart_data=chart_data
    )


@admin_bp.route('/customers')
@admin_required
def list_customers():
    """Admin view of all registered customers."""
    customers = fetch_all(
        """SELECT u.*,
                  (SELECT COUNT(*) FROM vehicles v WHERE v.customer_id = u.id) as vehicle_count,
                  (SELECT COUNT(*) FROM bookings b WHERE b.customer_id = u.id) as booking_count,
                  (SELECT COALESCE(SUM(bl.total_amount), 0) FROM bills bl JOIN bookings bk ON bl.booking_id = bk.id WHERE bk.customer_id = u.id AND bl.payment_status = 'Paid') as total_spend
           FROM users u
           WHERE u.role = 'customer'
           ORDER BY u.created_at DESC"""
    )
    return render_template('admin/customers.html', customers=customers)


@admin_bp.route('/customers/<int:customer_id>')
@admin_required
def customer_details(customer_id):
    """Admin inspection of customer profile, vehicles, and history."""
    customer = fetch_one("SELECT * FROM users WHERE id = %s AND role = 'customer'", (customer_id,))
    if not customer:
        flash('Customer not found.', 'danger')
        return redirect(url_for('admin.list_customers'))

    vehicles = fetch_all("SELECT * FROM vehicles WHERE customer_id = %s ORDER BY created_at DESC", (customer_id,))
    bookings = fetch_all(
        """SELECT b.*, v.registration_number, v.brand, v.model, s.service_name, bl.total_amount, bl.payment_status
           FROM bookings b
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           LEFT JOIN bills bl ON b.id = bl.booking_id
           WHERE b.customer_id = %s
           ORDER BY b.created_at DESC""",
        (customer_id,)
    )

    return render_template('admin/customer_details.html', customer=customer, vehicles=vehicles, bookings=bookings)


@admin_bp.route('/vehicles')
@admin_required
def list_all_vehicles():
    """Admin view of all vehicles across all customers."""
    vehicles = fetch_all(
        """SELECT v.*, u.full_name as owner_name, u.phone as owner_phone, u.email as owner_email,
                  (SELECT COUNT(*) FROM bookings b WHERE b.vehicle_id = v.id) as booking_count
           FROM vehicles v
           JOIN users u ON v.customer_id = u.id
           ORDER BY v.created_at DESC"""
    )
    return render_template('admin/vehicles.html', vehicles=vehicles)
