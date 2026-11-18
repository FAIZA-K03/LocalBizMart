-- ==============================================================
-- LocalBizMart: Online Marketplace for Local and Home-Based Businesses
-- Database Schema for MySQL (XAMPP)
-- ==============================================================

CREATE DATABASE IF NOT EXISTS `localbizmart` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `localbizmart`;

-- 1. Users Table (Customer, Owner, Admin)
CREATE TABLE IF NOT EXISTS `users` (
    `user_id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `phone` VARCHAR(20) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('customer', 'owner', 'admin') NOT NULL DEFAULT 'customer',
    `status` ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`),
    INDEX `idx_users_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Categories Table
CREATE TABLE IF NOT EXISTS `categories` (
    `category_id` INT AUTO_INCREMENT PRIMARY KEY,
    `category_name` VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Businesses Table (1 per Owner)
CREATE TABLE IF NOT EXISTS `businesses` (
    `business_id` INT AUTO_INCREMENT PRIMARY KEY,
    `owner_id` INT NOT NULL UNIQUE,
    `name` VARCHAR(150) NOT NULL,
    `description` TEXT,
    `category_id` INT NOT NULL,
    `address` TEXT NOT NULL,
    `whatsapp_number` VARCHAR(20) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    INDEX `idx_business_category` (`category_id`),
    INDEX `idx_business_status` (`status`),
    CONSTRAINT `fk_business_owner` FOREIGN KEY (`owner_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_business_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Products Table
CREATE TABLE IF NOT EXISTS `products` (
    `product_id` INT AUTO_INCREMENT PRIMARY KEY,
    `business_id` INT NOT NULL,
    `name` VARCHAR(150) NOT NULL,
    `description` TEXT,
    `price` DECIMAL(10, 2) NOT NULL,
    `image_path` VARCHAR(255) DEFAULT NULL,
    `is_available` BOOLEAN NOT NULL DEFAULT TRUE,
    `is_disabled_by_admin` BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX `idx_product_business` (`business_id`),
    INDEX `idx_product_availability` (`is_available`, `is_disabled_by_admin`),
    CONSTRAINT `fk_product_business` FOREIGN KEY (`business_id`) REFERENCES `businesses` (`business_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Cart Items Table
CREATE TABLE IF NOT EXISTS `cart_items` (
    `cart_item_id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_id` INT NOT NULL,
    `product_id` INT NOT NULL,
    `quantity` INT NOT NULL DEFAULT 1,
    UNIQUE KEY `unique_customer_product` (`customer_id`, `product_id`),
    INDEX `idx_cart_customer` (`customer_id`),
    CONSTRAINT `fk_cart_customer` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cart_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Orders Table
CREATE TABLE IF NOT EXISTS `orders` (
    `order_id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_id` INT NOT NULL,
    `business_id` INT NOT NULL,
    `total_amount` DECIMAL(10, 2) NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'Pending',
    `delivery_address` TEXT NOT NULL,
    `notes` TEXT DEFAULT NULL,
    `cancel_reason` TEXT DEFAULT NULL,
    `placed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_order_customer` (`customer_id`),
    INDEX `idx_order_business` (`business_id`),
    INDEX `idx_order_status` (`status`),
    CONSTRAINT `fk_order_customer` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_order_business` FOREIGN KEY (`business_id`) REFERENCES `businesses` (`business_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Order Items Table (Snapshot of product details; product_id NULLABLE ON DELETE SET NULL)
CREATE TABLE IF NOT EXISTS `order_items` (
    `order_item_id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_id` INT NOT NULL,
    `product_id` INT DEFAULT NULL,
    `product_name` VARCHAR(150) NOT NULL,
    `quantity` INT NOT NULL,
    `unit_price` DECIMAL(10, 2) NOT NULL,
    INDEX `idx_order_items_order` (`order_id`),
    CONSTRAINT `fk_order_items_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_order_items_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Order Status History Table
CREATE TABLE IF NOT EXISTS `order_status_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_id` INT NOT NULL,
    `status` VARCHAR(30) NOT NULL,
    `changed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `reason` TEXT DEFAULT NULL,
    INDEX `idx_status_history_order` (`order_id`),
    CONSTRAINT `fk_status_history_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Business Payment Settings Table
CREATE TABLE IF NOT EXISTS `business_payment_settings` (
    `business_id` INT PRIMARY KEY,
    `accepts_upi` BOOLEAN NOT NULL DEFAULT FALSE,
    `upi_id` VARCHAR(100) DEFAULT NULL,
    `accepts_cod` BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT `fk_payment_settings_business` FOREIGN KEY (`business_id`) REFERENCES `businesses` (`business_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Payments Table (1-to-1 with Orders)
CREATE TABLE IF NOT EXISTS `payments` (
    `payment_id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_id` INT NOT NULL UNIQUE,
    `payment_method` VARCHAR(20) NOT NULL,
    `payment_status` VARCHAR(30) NOT NULL DEFAULT 'Pending',
    `screenshot_path` VARCHAR(255) DEFAULT NULL,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_payments_order` (`order_id`),
    INDEX `idx_payments_status` (`payment_status`),
    CONSTRAINT `fk_payment_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
