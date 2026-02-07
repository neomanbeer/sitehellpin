<?php
/**
 * Application settings
 */
defined('SITE_ROOT') or define('SITE_ROOT', dirname(__DIR__));
defined('DLL_STORAGE_PATH') or define('DLL_STORAGE_PATH', SITE_ROOT . '/dll_storage');
defined('ADMIN_MAX_LOGIN_ATTEMPTS') or define('ADMIN_MAX_LOGIN_ATTEMPTS', 5);
defined('ADMIN_LOCKOUT_MINUTES') or define('ADMIN_LOCKOUT_MINUTES', 15);
defined('SESSION_LIFETIME') or define('SESSION_LIFETIME', 3600); // 1 hour
defined('API_RATE_LIMIT_REQUESTS') or define('API_RATE_LIMIT_REQUESTS', 30);
defined('API_RATE_LIMIT_WINDOW') or define('API_RATE_LIMIT_WINDOW', 60); // seconds

// Timezone
date_default_timezone_set('UTC');
