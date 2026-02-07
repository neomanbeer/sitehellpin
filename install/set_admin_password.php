<?php
/**
 * One-time script: set admin password. Run from CLI: php set_admin_password.php
 * Or open in browser once to set password for 'admin' to 'admin123'.
 */
require_once dirname(__DIR__) . '/config/db.php';

$newPassword = $argv[1] ?? 'admin123';
$hash = password_hash($newPassword, PASSWORD_BCRYPT);
$pdo = getDb();
$stmt = $pdo->prepare("UPDATE admin_users SET password = ? WHERE username = 'admin'");
$stmt->execute([$hash]);
echo "Password for 'admin' updated.\n";
