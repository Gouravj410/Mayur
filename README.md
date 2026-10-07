# 🚗 Car Services, Repair and Management System (AutoCareHub)

A comprehensive, production-grade automotive service center, garage operations, and fleet maintenance platform.  
Built with **Python (Flask)**, **MySQL / SQLite**, **Bootstrap 5**, and **JavaScript**.

---

## 🌐 Live Deployment & Online Showcase

- 🚀 **Live GitHub Pages Interactive Portal:** [https://gouravj410.github.io/Mayur/](https://gouravj410.github.io/Mayur/)
- 📦 **GitHub Repository:** [https://github.com/Gouravj410/Mayur](https://github.com/Gouravj410/Mayur)
- ☁️ **1-Click Cloud Deployment:** Pre-configured with `render.yaml` for Render, `Dockerfile` & `docker-compose.yml` for containers, and `Procfile` + `wsgi.py` for Gunicorn WSGI.
- 📖 **Technical Architecture & System Specification:** See [docs/architecture.md](docs/architecture.md) for complete 8-table relational schemas, ER design, and concurrency controls.

---

## 📌 1. Project Overview & Purpose

The **Car Services, Repair and Management System** digitizes workshop operations and bridges communication between vehicle owners and service center administrators:
- **Customers** can register, manage their automobiles, schedule maintenance slots, track repair job cards in real-time, inspect itemized invoices, and review permanent vehicle service histories.
- **Service Center Administrators** can manage customer records, approve bookings, supervise mechanic bay diagnostics, issue spare parts from inventory (with automatic stock deduction), generate synchronized tax invoices, record counter payments (Cash/UPI/Card), and view institutional reports.

---

## 🛠️ 2. Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6), Bootstrap 5.3, Bootstrap Icons, Chart.js |
| **Backend** | Python 3.12, Flask 2.3+ |
| **Database** | MySQL (with seamless local SQLite fallback for offline demonstrations) |
| **Security** | Session-based authentication, Werkzeug password hashing, parameterized SQL |
| **Styling** | Automotive professional design system with responsive layouts & print support |

---

## 🌟 3. Key Modules & Features

### 👤 Customer Portal
1. **Authentication & Profile:** Secure registration, login, session management, profile & password updates.
2. **Garage (Vehicle Management):** Add, view, edit, and delete vehicles with registration plate uniqueness validation.
3. **Service Booking:** Choose from predefined packages (General Service, Oil Change, Brake Service, AC Service, etc.), pick appointment dates & times, and describe specific concerns.
4. **Live Job Card Tracking:** Step-by-step lifecycle visual indicator (*Requested &rarr; Approved &rarr; In Bay &rarr; Completed &rarr; Paid*).
5. **Itemized Tax Invoices:** Official printable invoices itemizing labor and replaced spare parts.
6. **Vehicle Service History:** Permanent maintenance log per automobile including past diagnostics, dates, and replaced parts.

### 🛡️ Admin Portal
1. **Operations Dashboard:** 8 real-time KPI cards (Customers, Vehicles, Bay Jobs, Revenue, Receivables) + interactive Chart.js service demand chart.
2. **Service Bookings Management:** Filterable booking requests with instant approval, bay queuing, and rejection.
3. **Workshop Repairs & Diagnostics:** Dedicated technician job cards for diagnostic root cause, operations performed, and notes.
4. **Spare Parts Inventory:** Stock quantities, SKU numbers, unit prices, low-stock warnings, and automatic stock deduction when assigned to a repair.
5. **Billing & Revenue:** Automatic invoice formula:  
   $$\text{Total Bill} = \text{Service Labor Charge} + \sum(\text{Quantity Used} \times \text{Unit Price})$$
6. **Payment Recording:** Record payments via Cash, UPI, or Card with transaction references.
7. **Institutional Reports:** Tabular printable reports for Bookings, Customers, Vehicles, Repairs, Spare Parts, and Payments.

---

## 🔑 4. Default Demonstration & Testing Credentials

| Role | Email Address | Password | Features / Access |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@carservice.com` | `admin123` | Full workshop control, bay management, inventory, reports |
| **Customer** | `customer@carservice.com` | `customer123` | Garage management, booking slots, invoices, service history |

*(Tip: Both login pages feature a **Quick Fill** button to populate demo credentials with a single click for rapid system testing and functional walkthroughs).*

---

## 📂 5. Project Directory Structure

```text
Mayur/
├── app.py                      # Flask Application Entry Point & Blueprints
├── config.py                   # Environment & Database Configuration
├── requirements.txt            # Python Dependencies
├── .env.example                # Environment Variable Template
├── .env                        # Local Environment Settings
├── README.md                   # Project Documentation & Architecture Guide
├── test_workflow.py            # Automated End-to-End Workflow Test Suite
│
├── database/
│   ├── db.py                   # Resilient MySQL Connection Pool & Query Executor
│   ├── schema.sql              # Relational MySQL DDL Schema
│   └── init_db.py              # Database Initialization & Seed Script
│
├── routes/
│   ├── public_routes.py        # Landing page, Services catalog, About, Contact
│   ├── auth_routes.py          # Customer & Admin login, registration, logout
│   ├── customer_routes.py      # Customer dashboard and profile management
│   ├── vehicle_routes.py       # Customer garage (Add, Edit, Delete vehicles)
│   ├── service_routes.py       # Admin service package catalog
│   ├── booking_routes.py       # Service appointment scheduling & approvals
│   ├── repair_routes.py        # Workshop job cards & parts allocation
│   ├── parts_routes.py         # Spare parts inventory & stock tracking
│   ├── billing_routes.py       # Invoices, total calculations, payment recording
│   ├── history_routes.py       # Vehicle service history timeline logs
│   ├── admin_routes.py         # Admin dashboard, customers, and vehicles
│   └── report_routes.py        # Master reporting tabs & print layouts
│
├── templates/
│   ├── base.html               # Base layout (Navbar, Footer, Flash alerts)
│   ├── index.html              # Landing page with hero & packages
│   ├── about.html              # About Us & platform capabilities
│   ├── contact.html            # Workshop address & inquiry form
│   ├── public_services.html    # Public service catalog
│   ├── auth/                   # Login, Register, Admin login
│   ├── customer/               # Customer dashboard & profile
│   ├── vehicles/               # Vehicle garage list, add, edit
│   ├── bookings/               # Appointment booking, list, details view
│   ├── services/               # Admin catalog management
│   ├── repairs/                # Workshop job card management
│   ├── parts/                  # Spare parts inventory
│   ├── billing/                # Invoice views & payment forms
│   ├── history/                # Vehicle maintenance history logs
│   ├── admin/                  # Admin dashboard & customer directories
│   └── reports/                # Master printable system reports
│
└── static/
    ├── css/
    │   └── style.css           # Automotive styling & print stylesheets
    └── js/
        └── script.js           # Live calculations & client scripts
```

---

## ⚙️ 6. Installation & Setup Guide

### Step 1: Clone or Open Workspace
```bash
cd Mayur
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment (`.env`)
The file `.env` is pre-configured. If using MySQL Server (e.g. XAMPP or MySQL Workbench):
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=car_service_db
DB_TYPE=auto
```
> **Note on Portability & Resilience:** `DB_TYPE=auto` connects to MySQL when a dedicated MySQL server is running. If MySQL is offline or during standalone on-premise deployments, the application automatically uses the local SQLite database (`car_service.db`) so your services operate without interruption!

### Step 4: Initialize Database (Optional - Done Automatically on Startup)
```bash
python database/init_db.py
```

### Step 5: Run the Application
```bash
python app.py
```
Open your web browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

---

## 🧪 7. Running the Automated Workflow Test

You can run the end-to-end integration test suite anytime:
```bash
python test_workflow.py
```
This automatically verifies:
- Registration & Login
- Vehicle registration
- Appointment booking
- Admin approval & Bay job creation
- Spare parts allocation & stock deduction
- Bill generation formula check
- Payment recording
- Customer invoice and vehicle history verification

---

## 🏛️ 8. Core Technical Architecture & Engineering FAQs

**Q1: How are primary keys and foreign keys implemented?**  
*Answer:* Every table has an auto-incrementing integer `id` as primary key. For example, `vehicles.customer_id` references `users.id`, `bookings.vehicle_id` references `vehicles.id`, and `repair_parts` acts as an associative junction table linking `repairs` to `spare_parts`.

**Q2: How does the system prevent stock discrepancies?**  
*Answer:* In `routes/repair_routes.py`, when a spare part is assigned to a job card, the system validates that `spare_parts.quantity >= quantity_used`. It then deducts the quantity atomically and recalculates the total invoice.

**Q3: How are passwords secured?**  
*Answer:* Passwords are never stored in plain text. They are hashed using `werkzeug.security.generate_password_hash` (PBKDF2-SHA256) and verified using `check_password_hash`.

**Q4: Can a customer access another customer's vehicle or invoice?**  
*Answer:* No. All vehicle, booking, and invoice routes enforce ownership checks (`customer_id == session['user_id']`), preventing Insecure Direct Object References (IDOR).
