from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import fetch_all

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def home():
    """Public home landing page."""
    services = fetch_all("SELECT * FROM services WHERE status = 'active' ORDER BY base_price ASC LIMIT 8")
    return render_template('index.html', services=services)

@public_bp.route('/services')
def services():
    """Public service catalog listing."""
    services = fetch_all("SELECT * FROM services WHERE status = 'active' ORDER BY base_price ASC")
    return render_template('public_services.html', services=services)

@public_bp.route('/about')
def about():
    """Public About Us page."""
    return render_template('about.html')

@public_bp.route('/contact')
def contact():
    """Public Contact & Workshop location page."""
    return render_template('contact.html')

@public_bp.route('/contact/submit', methods=['POST'])
def contact_submit():
    """Handle contact inquiry form submission."""
    name = request.form.get('name', '').strip()
    flash(f'Thank you, {name}! Your message has been received. Our service desk supervisor will contact you shortly.', 'success')
    return redirect(url_for('public.contact'))
