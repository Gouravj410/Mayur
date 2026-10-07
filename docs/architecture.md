# AutoCareHub — Technical Architecture & System Specification

This document details the engineering specifications, data architecture, security posture, and domain workflows for the **AutoCareHub Vehicle Service, Diagnostics & Management Platform**.

---

## 1. Domain Architecture & Separation of Concerns

AutoCareHub is designed with a **Modular Blueprint Pattern** in Python Flask, enforcing clean boundary separation across domain responsibilities:

```
                      +------------------------------+
                      |       Web Client Layer       |
                      |  (Bootstrap 5 + ES6 Engine)  |
                      +--------------+---------------+
                                     |  HTTP / JSON
                                     v
                      +------------------------------+
                      |      Flask WSGI Server       |
                      +--------------+---------------+
                                     |
    +---------------+----------------+---------------+---------------+
    |               |                |               |               |
    v               v                v               v               v
[auth_bp]    [customer_bp]     [vehicle_bp]    [booking_bp]     [repair_bp]
Auth & Role   Profile & Jobs   Fleet Registry  Scheduling Engine Mechanic Bay
    |               |                |               |               |
    +---------------+----------------+---------------+---------------+
                                     |
                                     v
                      +------------------------------+
                      |   Domain Data Service Layer  |
                      |  (Parameterized SQL Queries) |
                      +--------------+---------------+
                                     |
             +-----------------------+-----------------------+
             |                                               |
             v                                               v
     [MySQL Database]                              [SQLite Database]
(Primary Production Cluster)                  (Resilient Offline Engine)
```

### Module Responsibilities
1. **`auth_bp`**: Session-based user authentication, role differentiation (`admin` vs `customer`), PBKDF2 password hashing.
2. **`customer_bp`**: Customer dashboard, active service tracking, and profile updates.
3. **`vehicle_bp`**: Garage CRUD operations, plate uniqueness validation, ownership isolation.
4. **`booking_bp`**: Service scheduling, package selection, appointment conflict checking, and queue management.
5. **`repair_bp`**: Technician diagnostic job cards, bay allocation, and spare parts issuance.
6. **`parts_bp`**: Spare parts inventory ledger, minimum reorder thresholds, and unit rate management.
7. **`billing_bp`**: Deterministic synchronized tax invoicing (Labor + Spares + 18% GST).
8. **`history_bp`**: Permanent immutable vehicle maintenance log per chassis number.

---

## 2. Relational Database Schema Design (3NF)

The database consists of 8 normalized relational entities with enforced foreign key referential integrity:

### 1. `users`
- `id` INTEGER PRIMARY KEY AUTO_INCREMENT
- `full_name` VARCHAR(100) NOT NULL
- `email` VARCHAR(100) NOT NULL UNIQUE
- `phone` VARCHAR(20) NOT NULL
- `address` TEXT
- `password_hash` VARCHAR(255) NOT NULL
- `role` ENUM('admin', 'customer') DEFAULT 'customer'
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 2. `vehicles`
- `id` INTEGER PRIMARY KEY AUTO_INCREMENT
- `customer_id` INTEGER NOT NULL (FK -> `users.id` ON DELETE CASCADE)
- `registration_number` VARCHAR(20) NOT NULL UNIQUE
- `brand` VARCHAR(50) NOT NULL
- `model` VARCHAR(50) NOT NULL
- `manufacturing_year` INTEGER NOT NULL
- `fuel_type` VARCHAR(20) NOT NULL
- `vehicle_color` VARCHAR(30) NOT NULL
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 3. `services`
- `id` INTEGER PRIMARY KEY AUTO_INCREMENT
- `service_name` VARCHAR(100) NOT NULL
- `description` TEXT
- `base_charge` DECIMAL(10, 2) NOT NULL
- `estimated_duration` VARCHAR(50)
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 4. `bookings`
- `id` INTEGER PRIMARY KEY AUTO_INCREMENT
- `customer_id` INTEGER NOT NULL (FK -> `users.id` ON DELETE CASCADE)
- `vehicle_id` INTEGER NOT NULL (FK -> `vehicles.id` ON DELETE CASCADE)
- `service_id` INTEGER NOT NULL (FK -> `services.id`)
- `booking_date` DATE NOT NULL
- `time_slot` VARCHAR(20) NOT NULL
- `customer_notes` TEXT
- `status` ENUM('pending', 'approved', 'in_progress', 'completed', 'cancelled') DEFAULT 'pending'
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 5. `repairs`
- `id` INTEGER PRIMARY KEY AUTO_INCREMENT
- `booking_id` INTEGER NOT NULL UNIQUE (FK -> `bookings.id` ON DELETE CASCADE)
- `technician_name` VARCHAR(100)
- `bay_number` VARCHAR(20)
- `diagnostic_details` TEXT
- `work_performed` TEXT
- `labor_charge` DECIMAL(10, 2) DEFAULT 0.00
- `repair_status` ENUM('diagnosing', 'waiting_parts', 'repairing', 'tested', 'finished') DEFAULT 'diagnosing'
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 6. `spare_parts`
- `id` INTEGER PRIMARY KEY AUTO_INCREMENT
- `part_name` VARCHAR(100) NOT NULL
- `part_number` VARCHAR(50) NOT NULL UNIQUE
- `stock_quantity` INTEGER NOT NULL DEFAULT 0
- `unit_price` DECIMAL(10, 2) NOT NULL
- `minimum_threshold` INTEGER DEFAULT 5
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 7. `repair_parts` (Junction Entity)
- `id` INTEGER PRIMARY KEY AUTO_INCREMENT
- `repair_id` INTEGER NOT NULL (FK -> `repairs.id` ON DELETE CASCADE)
- `part_id` INTEGER NOT NULL (FK -> `spare_parts.id`)
- `quantity_used` INTEGER NOT NULL
- `unit_price_at_repair` DECIMAL(10, 2) NOT NULL
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 8. `bills`
- `id` INTEGER PRIMARY KEY AUTO_INCREMENT
- `invoice_number` VARCHAR(50) NOT NULL UNIQUE
- `booking_id` INTEGER NOT NULL UNIQUE (FK -> `bookings.id` ON DELETE CASCADE)
- `customer_id` INTEGER NOT NULL (FK -> `users.id`)
- `total_service_charge` DECIMAL(10, 2) NOT NULL
- `total_parts_charge` DECIMAL(10, 2) NOT NULL
- `tax_amount` DECIMAL(10, 2) NOT NULL
- `grand_total` DECIMAL(10, 2) NOT NULL
- `payment_status` ENUM('unpaid', 'paid') DEFAULT 'unpaid'
- `payment_method` VARCHAR(30)
- `transaction_reference` VARCHAR(100)
- `payment_date` TIMESTAMP NULL
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

---

## 3. Transaction Atomicity & Concurrency Controls

### Parts Allocation & Stock Decrement
When replacement spare parts are assigned to a vehicle job card, the transaction executes atomically:

```sql
START TRANSACTION;

-- 1. Check current inventory stock
SELECT stock_quantity FROM spare_parts WHERE id = :part_id FOR UPDATE;

-- 2. Validate stock_quantity >= :qty_requested
-- If insufficient, ROLLBACK immediately and abort.

-- 3. Insert into junction entity capturing historical unit rate
INSERT INTO repair_parts (repair_id, part_id, quantity_used, unit_price_at_repair)
VALUES (:repair_id, :part_id, :qty_requested, :current_unit_price);

-- 4. Decrement inventory atomically
UPDATE spare_parts 
SET stock_quantity = stock_quantity - :qty_requested 
WHERE id = :part_id;

COMMIT;
```

---

## 4. Financial Calculation & Tax Invoicing

Invoices use a deterministic formula with frozen historical unit rates:

$$\text{Subtotal} = \text{Service Labor Base} + \sum_{i=1}^{n} (\text{Quantity}_i \times \text{Unit Price At Time of Repair}_i)$$

$$\text{Statutory GST} = \text{Subtotal} \times 0.18$$

$$\text{Grand Total} = \text{Subtotal} + \text{Statutory GST}$$

Because `repair_parts` captures `unit_price_at_repair` at issuance time, past invoices remain immutable and audit-compliant even if future supplier inventory prices change.

---

## 5. Security & OWASP Controls

1. **SQL Injection Defense**: 100% of queries use parameterized prepared statements (`?` for SQLite, `%s` for PyMySQL).
2. **Credential Cryptography**: Passwords undergo salted PBKDF2-SHA256 hashing using `werkzeug.security.generate_password_hash`. Plaintext passwords are never logged or stored.
3. **Insecure Direct Object Reference (IDOR) Mitigation**: All user-facing routes check session ownership:
   ```python
   if vehicle['customer_id'] != session['user_id']:
       abort(403)
   ```
4. **Session Cookie Security**: Flask sessions use signed cryptographic cookies with `HTTPOnly=True` and `SameSite='Lax'`.
