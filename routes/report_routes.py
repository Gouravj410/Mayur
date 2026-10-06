from flask import Blueprint, render_template, request
from database.db import fetch_all
from utils.helpers import admin_required

report_bp = Blueprint('report', __name__, url_prefix='/reports')

@report_bp.route('/')
@admin_required
def reports_dashboard():
    """Centralized reports dashboard with tabbed report tables and print layouts."""
    active_tab = request.args.get('tab', 'bookings')

    # 1. Customer Report
    customers = fetch_all(
        """SELECT u.*,
                  (SELECT COUNT(*) FROM vehicles v WHERE v.customer_id = u.id) as vehicle_count,
                  (SELECT COUNT(*) FROM bookings b WHERE b.customer_id = u.id) as booking_count
           FROM users u
           WHERE u.role = 'customer'
           ORDER BY u.created_at DESC"""
    )

    # 2. Vehicle Report
    vehicles = fetch_all(
        """SELECT v.*, u.full_name as owner_name, u.phone as owner_phone,
                  (SELECT COUNT(*) FROM bookings b WHERE b.vehicle_id = v.id) as total_services
           FROM vehicles v
           JOIN users u ON v.customer_id = u.id
           ORDER BY v.created_at DESC"""
    )

    # 3. Booking Report
    bookings = fetch_all(
        """SELECT b.*, u.full_name as customer_name, v.registration_number, v.brand, v.model,
                  s.service_name, s.base_price, bl.total_amount, bl.payment_status
           FROM bookings b
           JOIN users u ON b.customer_id = u.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           LEFT JOIN bills bl ON b.id = bl.booking_id
           ORDER BY b.booking_date DESC"""
    )

    # 4. Repair Report
    repairs = fetch_all(
        """SELECT r.*, b.booking_date, u.full_name as customer_name, v.registration_number, s.service_name,
                  (SELECT COUNT(*) FROM repair_parts rp WHERE rp.repair_id = r.id) as parts_count
           FROM repairs r
           JOIN bookings b ON r.booking_id = b.id
           JOIN users u ON b.customer_id = u.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           ORDER BY r.created_at DESC"""
    )

    # 5. Spare Parts Usage Report
    spare_parts = fetch_all(
        """SELECT sp.*,
                  COALESCE((SELECT SUM(rp.quantity_used) FROM repair_parts rp WHERE rp.part_id = sp.id), 0) as total_used,
                  COALESCE((SELECT SUM(rp.quantity_used * rp.price_at_time_of_use) FROM repair_parts rp WHERE rp.part_id = sp.id), 0) as revenue_generated
           FROM spare_parts sp
           ORDER BY total_used DESC"""
    )

    # 6. Payment & Billing Report
    payments = fetch_all(
        """SELECT bl.id as bill_id, bl.booking_id, bl.service_charge, bl.parts_charge, bl.total_amount, bl.bill_date, bl.payment_status,
                  u.full_name as customer_name, v.registration_number, s.service_name,
                  p.payment_method, p.payment_date, p.transaction_reference
           FROM bills bl
           JOIN bookings b ON bl.booking_id = b.id
           JOIN users u ON b.customer_id = u.id
           JOIN vehicles v ON b.vehicle_id = v.id
           JOIN services s ON b.service_id = s.id
           LEFT JOIN payments p ON bl.id = p.bill_id
           ORDER BY bl.bill_date DESC"""
    )

    return render_template(
        'reports/index.html',
        active_tab=active_tab,
        customers=customers,
        vehicles=vehicles,
        bookings=bookings,
        repairs=repairs,
        spare_parts=spare_parts,
        payments=payments
    )
