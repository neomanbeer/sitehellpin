<?php
/**
 * Shared helper functions for API and admin
 */

function getSetting(PDO $pdo, string $key): ?string {
    $stmt = $pdo->prepare("SELECT setting_value FROM settings WHERE setting_key = ?");
    $stmt->execute([$key]);
    $row = $stmt->fetch();
    return $row ? $row['setting_value'] : null;
}

function setSetting(PDO $pdo, string $key, string $value): void {
    $stmt = $pdo->prepare("INSERT INTO settings (setting_key, setting_value) VALUES (?, ?) ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)");
    $stmt->execute([$key, $value]);
}

/**
 * Log injection attempt
 */
function logInjection(PDO $pdo, ?int $userId, string $username, string $ip, ?string $userAgent, string $status = 'success', ?string $errorMessage = null, ?string $dllVersion = null, ?int $csgoPid = null): void {
    $stmt = $pdo->prepare("INSERT INTO injection_logs (user_id, username, ip_address, user_agent, status, error_message, dll_version, csgo_process_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->execute([
        $userId,
        $username,
        $ip,
        $userAgent ?? '',
        $status,
        $errorMessage,
        $dllVersion,
        $csgoPid
    ]);
}

/**
 * Check if user has subscription (group 6)
 */
function hasSubscription(array $user): bool {
    $ids = $user['secondary_group_ids'] ?? null;
    if (is_string($ids)) {
        $ids = json_decode($ids, true);
    }
    return is_array($ids) && in_array(6, $ids, true);
}

/**
 * Check subscription not expired
 */
function subscriptionValid(array $user): bool {
    $exp = $user['subscription_expires'] ?? null;
    if (!$exp) return false;
    return strtotime($exp) >= time();
}

function jsonResponse(array $data): void {
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
}

function getClientIp(): string {
    return $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['HTTP_CF_CONNECTING_IP'] ?? $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
}

function getClientUserAgent(): ?string {
    $ua = $_SERVER['HTTP_USER_AGENT'] ?? null;
    return $ua ? substr($ua, 0, 500) : null;
}
