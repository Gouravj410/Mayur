import os
import sys
from werkzeug.security import generate_password_hash

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_connection, execute_query, fetch_one, get_backend_name
from config import Config

def init_database():
    """
    Initializes tables and seeds initial demo data.
    """
    conn, backend = get_connection()
    cursor = conn.cursor()
    print(f"[*] Initializing database using backend: {backend.upper()}")

    try:
        if backend == 'mysql':
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            with open(schema_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Execute commands separated by semicolon
            commands = sql_content.split(';')
            for cmd in commands:
                cmd_clean = cmd.strip()
                if cmd_clean and not cmd_clean.startswith('--'):
                    cursor.execute(cmd_clean)
            conn.commit()

        else:
            # SQLite Table definitions
            tables = [
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT NOT NULL,
                    address TEXT,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'customer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    registration_number TEXT NOT NULL UNIQUE,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    manufacturing_year INTEGER NOT NULL,
                    fuel_type TEXT NOT NULL,
                    vehicle_color TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES users (id) ON DELETE CASCADE
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    description TEXT,
                    base_price NUMERIC NOT NULL DEFAULT 0.00,
                    estimated_duration TEXT NOT NULL DEFAULT '1-2 Hours',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    vehicle_id INTEGER NOT NULL,
                    service_id INTEGER NOT NULL,
                    booking_date TEXT NOT NULL,
                    booking_time TEXT NOT NULL,
                    problem_description TEXT,
                    booking_status TEXT NOT NULL DEFAULT 'Pending',
                    admin_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles (id) ON DELETE CASCADE,
                    FOREIGN KEY (service_id) REFERENCES services (id) ON DELETE RESTRICT
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS repairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_id INTEGER NOT NULL UNIQUE,
                    diagnosis TEXT,
                    work_performed TEXT,
                    repair_notes TEXT,
                    repair_status TEXT NOT NULL DEFAULT 'Not Started',
                    start_date TIMESTAMP NULL,
                    completion_date TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS spare_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    part_name TEXT NOT NULL,
                    part_number TEXT NOT NULL UNIQUE,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    unit_price NUMERIC NOT NULL DEFAULT 0.00,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS repair_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repair_id INTEGER NOT NULL,
                    part_id INTEGER NOT NULL,
                    quantity_used INTEGER NOT NULL DEFAULT 1,
                    price_at_time_of_use NUMERIC NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repair_id) REFERENCES repairs (id) ON DELETE CASCADE,
                    FOREIGN KEY (part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS bills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_id INTEGER NOT NULL UNIQUE,
                    service_charge NUMERIC NOT NULL DEFAULT 0.00,
                    parts_charge NUMERIC NOT NULL DEFAULT 0.00,
                    total_amount NUMERIC NOT NULL DEFAULT 0.00,
                    bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_status TEXT NOT NULL DEFAULT 'Pending',
                    FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id INTEGER NOT NULL UNIQUE,
                    amount NUMERIC NOT NULL,
                    payment_method TEXT NOT NULL DEFAULT 'Cash',
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_status TEXT NOT NULL DEFAULT 'Paid',
                    transaction_reference TEXT NULL,
                    FOREIGN KEY (bill_id) REFERENCES bills (id) ON DELETE CASCADE
                );
                """
            ]
            for statement in tables:
                cursor.execute(statement)
            conn.commit()

        print("[+] Tables initialized successfully.")

    finally:
        cursor.close()
        conn.close()

    # Seed Default Data
    seed_demo_data()


def seed_demo_data():
    """
    Seeds initial Admin, Demo Customer, Services, and Spare Parts.
    """
    print("[*] Checking demo seeds...")

    # 1. Admin Account
    admin = fetch_one("SELECT id FROM users WHERE email = %s", ('admin@carservice.com',))
    if not admin:
        admin_pass = generate_password_hash("admin123")
        execute_query(
            """INSERT INTO users (full_name, email, phone, address, password_hash, role)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            ('Service Center Admin', 'admin@carservice.com', '9876543210', '101 Auto Hub, Central Road', admin_pass, 'admin')
        )
        print("[+] Admin user created: admin@carservice.com / admin123")

    # 2. Demo Customer Account
    customer = fetch_one("SELECT id FROM users WHERE email = %s", ('customer@carservice.com',))
    customer_id = None
    if not customer:
        cust_pass = generate_password_hash("customer123")
        customer_id, _ = execute_query(
            """INSERT INTO users (full_name, email, phone, address, password_hash, role)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            ('John Doe', 'customer@carservice.com', '9123456780', '42 Park Avenue, Metro City', cust_pass, 'customer')
        )
        print("[+] Demo customer created: customer@carservice.com / customer123")
    else:
        customer_id = customer['id']

    # 3. Demo Vehicle for Customer
    if customer_id:
        existing_vehicle = fetch_one("SELECT id FROM vehicles WHERE registration_number = %s", ('MH-12-AB-1234',))
        if not existing_vehicle:
            execute_query(
                """INSERT INTO vehicles (customer_id, registration_number, brand, model, manufacturing_year, fuel_type, vehicle_color)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (customer_id, 'MH-12-AB-1234', 'Honda', 'City', 2021, 'Petrol', 'Metallic Silver')
            )
            print("[+] Sample vehicle added: MH-12-AB-1234")

    # 4. Predefined Services
    predefined_services = [
        ('General Service', 'Complete 30-point inspection, fluid top-up, filter clean, spark plug check and wash.', 1500.00, '2-3 Hours'),
        ('Oil Change', 'Engine oil drainage, synthetic engine oil refill, and new oil filter installation.', 800.00, '45 Mins'),
        ('Brake Service', 'Brake pad inspection, disc caliper cleaning, rotor check and fluid bleeding.', 1200.00, '1-2 Hours'),
        ('AC Service', 'Cabin filter cleaning, refrigerant gas top-up, cooling coil inspection & duct disinfection.', 1800.00, '2 Hours'),
        ('Engine Check', 'Computerized OBD-II diagnostics, sensor checking, ignition timing, and fuel trim check.', 2200.00, '3 Hours'),
        ('Wheel Alignment', 'Computerized 3D laser wheel alignment and high-speed tire balancing.', 600.00, '30 Mins'),
        ('Battery Check', 'Battery voltage, cold cranking amps test, terminal cleaning and charging circuit test.', 400.00, '30 Mins'),
        ('Full Car Service', 'Comprehensive bumper-to-bumper service with engine tuning, brakes, AC & deep interior cleaning.', 4500.00, '4-5 Hours')
    ]

    for s_name, desc, price, duration in predefined_services:
        exist = fetch_one("SELECT id FROM services WHERE service_name = %s", (s_name,))
        if not exist:
            execute_query(
                """INSERT INTO services (service_name, description, base_price, estimated_duration, status)
                   VALUES (%s, %s, %s, %s, 'active')""",
                (s_name, desc, price, duration)
            )
    print("[+] Predefined services verified.")

    # 5. Predefined Spare Parts
    predefined_parts = [
        ('Synthetic Engine Oil 5W-30', 'ENG-OIL-5W30', 25, 1400.00, 'High-grade fully synthetic 3.5L engine oil canister'),
        ('Front Ceramic Brake Pads', 'BRK-PAD-FR01', 18, 950.00, 'Premium ceramic disc brake pads set'),
        ('OEM Spin-on Oil Filter', 'FLT-OIL-OF02', 30, 350.00, 'High-efficiency micronic oil filter element'),
        ('Engine Air Filter Element', 'FLT-AIR-AF03', 20, 450.00, 'Multi-layer particulate engine air filter'),
        ('Maintenance-Free Battery 12V 45Ah', 'BAT-12V-EX04', 8, 3800.00, 'Heavy-duty lead-acid 12V starter battery'),
        ('Cabin Activated Carbon AC Filter', 'FLT-AC-CF05', 15, 550.00, 'Allergen and odor removing cabin filter'),
        ('Iridium Spark Plug (Set of 4)', 'SPK-NGK-SP06', 40, 250.00, 'High-performance laser iridium spark plug'),
        ('Premixed Engine Coolant 1L', 'CLN-RAD-CL07', 16, 400.00, 'Long-life ethylene glycol anti-freeze radiator coolant')
    ]

    for p_name, p_num, qty, price, p_desc in predefined_parts:
        exist = fetch_one("SELECT id FROM spare_parts WHERE part_number = %s", (p_num,))
        if not exist:
            execute_query(
                """INSERT INTO spare_parts (part_name, part_number, quantity, unit_price, description)
                   VALUES (%s, %s, %s, %s, %s)""",
                (p_name, p_num, qty, price, p_desc)
            )
    print("[OK] Database initialized and seeded successfully.")

if __name__ == '__main__':
    init_database()
