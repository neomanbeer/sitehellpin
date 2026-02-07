"""
App config - uses env vars for Render.com, defaults for local dev.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DLL_STORAGE = BASE_DIR / "dll_storage"
DLL_STORAGE.mkdir(exist_ok=True)

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

# Database: Render sets DATABASE_URL (PostgreSQL). Local: SQLite.
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///" + str(BASE_DIR / "local.db")

# Admin
ADMIN_MAX_LOGIN_ATTEMPTS = int(os.environ.get("ADMIN_MAX_LOGIN_ATTEMPTS", "5"))
ADMIN_LOCKOUT_MINUTES = int(os.environ.get("ADMIN_LOCKOUT_MINUTES", "15"))
SESSION_LIFETIME_SECONDS = int(os.environ.get("SESSION_LIFETIME", "3600"))
