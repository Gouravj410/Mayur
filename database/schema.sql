-- =======================================================
-- CAR SERVICES, REPAIR AND MANAGEMENT SYSTEM
-- AutoCareHub Enterprise Database Architecture
-- Database: MySQL Relational Schema
-- =======================================================

CREATE DATABASE IF NOT EXISTS `car_service_db`;
USE `car_service_db`;

-- Drop tables in reverse order of foreign keys (if recreating)
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `payments`;
DROP TABLE IF EXISTS `bills`;
DROP TABLE IF EXISTS `repair_parts`;
DROP TABLE IF EXISTS `repairs`;
DROP TABLE IF EXISTS `spare_parts`;
DROP TABLE IF EXISTS `bookings`;
DROP TABLE IF EXISTS `services`;
DROP TABLE IF EXISTS `vehicles`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Users Table (Customers and Admin)
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `full_name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `phone` VARCHAR(20) NOT NULL,
    `address` TEXT,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('customer', 'admin') NOT NULL DEFAULT 'customer',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Vehicles Table
CREATE TABLE `vehicles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_id` INT NOT NULL,
    `registration_number` VARCHAR(50) NOT NULL UNIQUE,
    `brand` VARCHAR(50) NOT NULL,
    `model` VARCHAR(50) NOT NULL,
    `manufacturing_year` INT NOT NULL,
    `fuel_type` VARCHAR(20) NOT NULL,
    `vehicle_color` VARCHAR(30) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_vehicle_customer` FOREIGN KEY (`customer_id`) 
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Predefined Services Table
CREATE TABLE `services` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `service_name` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `base_price` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `estimated_duration` VARCHAR(50) NOT NULL DEFAULT '1-2 Hours',
    `status` ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Service Bookings Table
CREATE TABLE `bookings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_id` INT NOT NULL,
    `vehicle_id` INT NOT NULL,
    `service_id` INT NOT NULL,
    `booking_date` DATE NOT NULL,
    `booking_time` VARCHAR(20) NOT NULL,
    `problem_description` TEXT,
    `booking_status` ENUM('Pending', 'Approved', 'Rejected', 'In Service', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Pending',
    `admin_notes` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_booking_customer` FOREIGN KEY (`customer_id`) 
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_booking_vehicle` FOREIGN KEY (`vehicle_id`) 
        REFERENCES `vehicles` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_booking_service` FOREIGN KEY (`service_id`) 
        REFERENCES `services` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Repairs & Service Tracking Table
CREATE TABLE `repairs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `booking_id` INT NOT NULL UNIQUE,
    `diagnosis` TEXT,
    `work_performed` TEXT,
    `repair_notes` TEXT,
    `repair_status` ENUM('Not Started', 'In Progress', 'Waiting for Parts', 'Completed') NOT NULL DEFAULT 'Not Started',
    `start_date` DATETIME NULL,
    `completion_date` DATETIME NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_repair_booking` FOREIGN KEY (`booking_id`) 
        REFERENCES `bookings` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Spare Parts Inventory Table
CREATE TABLE `spare_parts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `part_name` VARCHAR(100) NOT NULL,
    `part_number` VARCHAR(50) NOT NULL UNIQUE,
    `quantity` INT NOT NULL DEFAULT 0,
    `unit_price` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `description` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Repair Parts Used (Junction Table)
CREATE TABLE `repair_parts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `repair_id` INT NOT NULL,
    `part_id` INT NOT NULL,
    `quantity_used` INT NOT NULL DEFAULT 1,
    `price_at_time_of_use` DECIMAL(10, 2) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_repairparts_repair` FOREIGN KEY (`repair_id`) 
        REFERENCES `repairs` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_repairparts_part` FOREIGN KEY (`part_id`) 
        REFERENCES `spare_parts` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Billing Table
CREATE TABLE `bills` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `booking_id` INT NOT NULL UNIQUE,
    `service_charge` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `parts_charge` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `total_amount` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `bill_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `payment_status` ENUM('Pending', 'Paid') NOT NULL DEFAULT 'Pending',
    CONSTRAINT `fk_bill_booking` FOREIGN KEY (`booking_id`) 
        REFERENCES `bookings` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Payments Table
CREATE TABLE `payments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `bill_id` INT NOT NULL UNIQUE,
    `amount` DECIMAL(10, 2) NOT NULL,
    `payment_method` ENUM('Cash', 'Card', 'UPI') NOT NULL DEFAULT 'Cash',
    `payment_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `payment_status` ENUM('Paid', 'Pending', 'Failed') NOT NULL DEFAULT 'Paid',
    `transaction_reference` VARCHAR(100) NULL,
    CONSTRAINT `fk_payment_bill` FOREIGN KEY (`bill_id`) 
        REFERENCES `bills` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
