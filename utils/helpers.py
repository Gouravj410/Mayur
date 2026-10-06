from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Admin authentication required.', 'warning')
            return redirect(url_for('auth.admin_login'))
        if session.get('role') != 'admin':
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('customer.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access your customer portal.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'customer':
            flash('Admin accounts cannot access customer booking portal.', 'info')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def format_currency(value):
    """Formats float/decimal into Indian Rupee format."""
    try:
        val = float(value)
        return f"₹{val:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"

def get_status_badge(status):
    """Returns CSS badge class for status display."""
    badges = {
        'Pending': 'badge bg-warning text-dark',
        'Approved': 'badge bg-info text-dark',
        'In Service': 'badge bg-primary',
        'Completed': 'badge bg-success',
        'Cancelled': 'badge bg-secondary',
        'Rejected': 'badge bg-danger',
        'Not Started': 'badge bg-secondary',
        'In Progress': 'badge bg-primary',
        'Waiting for Parts': 'badge bg-warning text-dark',
        'Paid': 'badge bg-success',
        'Unpaid': 'badge bg-danger',
        'active': 'badge bg-success',
        'inactive': 'badge bg-secondary'
    }
    return badges.get(status, 'badge bg-secondary')
