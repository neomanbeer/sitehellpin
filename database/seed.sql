-- Seed data for development
USE loader_site;

-- Default admin and moderator: password = "password" (change via install/set_admin_password.php)
INSERT INTO admin_users (username, password, role) VALUES
('admin', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin'),
('moderator', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'moderator');

-- Test users (password = "password")
INSERT INTO users (username, password, secondary_group_ids, subscription_expires) VALUES
('testuser', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', '[6]', '2025-12-31 23:59:59'),
('demo', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', '[]', NULL);

-- Default settings
INSERT INTO settings (setting_key, setting_value) VALUES
('dll_download_url', ''),
('admin_max_login_attempts', '5'),
('admin_lockout_minutes', '15'),
('session_lifetime', '3600');

-- Hash above = password_hash('password', PASSWORD_BCRYPT). Change admin via install/set_admin_password.php
