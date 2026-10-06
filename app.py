import os
from flask import Flask, render_template
from config import Config
from database.init_db import init_database
from utils.helpers import format_currency, get_status_badge

# Import Blueprints
from routes.public_routes import public_bp
from routes.auth_routes import auth_bp
from routes.customer_routes import customer_bp
from routes.vehicle_routes import vehicle_bp
from routes.service_routes import service_bp
from routes.booking_routes import booking_bp
from routes.repair_routes import repair_bp
from routes.parts_routes import parts_bp
from routes.billing_routes import billing_bp
from routes.history_routes import history_bp
from routes.admin_routes import admin_bp
from routes.report_routes import report_bp

def create_app():
    """Application Factory Pattern."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure Database Tables and Demo Seeds are initialized
    with app.app_context():
        try:
            init_database()
        except Exception as e:
            print(f"[!] Database init notice: {e}")

    # Register Blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(vehicle_bp)
    app.register_blueprint(service_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(repair_bp)
    app.register_blueprint(parts_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(report_bp)

    # Register Template Context Processors & Filters
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['status_badge'] = get_status_badge

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', not_found=True), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('base.html', server_error=True), 500

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1')
    print(f"[INFO] AutoCareHub Server starting at http://127.0.0.1:{port} (Debug: {debug_mode})")
    app.run(host='127.0.0.1', port=port, debug=debug_mode)
