<?php
/**
 * Database configuration - copy to database.local.php and set your credentials
 */
defined('DB_HOST') or define('DB_HOST', 'localhost');
defined('DB_NAME') or define('DB_NAME', 'loader_site');
defined('DB_USER') or define('DB_USER', 'root');
defined('DB_PASS') or define('DB_PASS', '');
defined('DB_CHARSET') or define('DB_CHARSET', 'utf8mb4');

if (file_exists(__DIR__ . '/database.local.php')) {
    require __DIR__ . '/database.local.php';
}
