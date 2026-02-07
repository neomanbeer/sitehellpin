-- Loader site database schema
-- MySQL/MariaDB

CREATE DATABASE IF NOT EXISTS loader_site CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE loader_site;

-- Users (loader clients)
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    secondary_group_ids JSON,
    is_banned BOOLEAN DEFAULT FALSE,
    ban_reason TEXT NULL,
    banned_by INT NULL,
    banned_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    subscription_expires DATETIME NULL,
    INDEX idx_username (username),
    INDEX idx_is_banned (is_banned),
    INDEX idx_subscription (subscription_expires)
) ENGINE=InnoDB;

-- Injection logs
CREATE TABLE injection_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NULL,
    username VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    user_agent VARCHAR(500) NULL,
    injection_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'failed', 'blocked') DEFAULT 'success',
    error_message TEXT NULL,
    dll_version VARCHAR(50) NULL,
    csgo_process_id INT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_username (username),
    INDEX idx_ip (ip_address),
    INDEX idx_injection_time (injection_time),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- Admin users
CREATE TABLE admin_users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'moderator') DEFAULT 'moderator',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    INDEX idx_username (username)
) ENGINE=InnoDB;

-- System logs (admin actions)
CREATE TABLE system_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    admin_id INT NULL,
    action_type VARCHAR(100) NOT NULL,
    target_user_id INT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admin_users(id) ON DELETE SET NULL,
    INDEX idx_admin_id (admin_id),
    INDEX idx_action_type (action_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- DLL files
CREATE TABLE dll_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    version VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    md5_hash VARCHAR(32) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    uploaded_by INT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT NULL,
    FOREIGN KEY (uploaded_by) REFERENCES admin_users(id) ON DELETE SET NULL,
    INDEX idx_is_active (is_active),
    UNIQUE KEY uk_version (version)
) ENGINE=InnoDB;

-- Settings (key-value)
CREATE TABLE settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Login attempts (brute force protection)
CREATE TABLE admin_login_attempts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ip_address VARCHAR(45) NOT NULL,
    attempted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ip_time (ip_address, attempted_at)
) ENGINE=InnoDB;

-- API auth tokens (optional: for download by token)
CREATE TABLE api_tokens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    token VARCHAR(64) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_token (token)
) ENGINE=InnoDB;
