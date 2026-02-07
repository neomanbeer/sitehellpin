"""
SQLAlchemy models - compatible with SQLite (local) and PostgreSQL (Render).
"""
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

db = SQLAlchemy()


def init_db(app: Flask):
    db.init_app(app)
    with app.app_context():
        db.create_all()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    secondary_group_ids = db.Column(db.Text, default="[]")  # JSON array as string
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.Text)
    banned_by = db.Column(db.Integer)
    banned_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    subscription_expires = db.Column(db.DateTime)
    hwid = db.Column(db.String(255), nullable=True)  # loader sends this; admin binds to user

    def get_group_ids(self):
        try:
            return json.loads(self.secondary_group_ids or "[]")
        except Exception:
            return []

    def has_subscription(self):
        ids = self.get_group_ids()
        if 6 not in ids:
            return False
        if self.subscription_expires and self.subscription_expires < datetime.utcnow():
            return False
        return True


class InjectionLog(db.Model):
    __tablename__ = "injection_logs"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    username = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(500))
    injection_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="success")  # success, failed, blocked
    error_message = db.Column(db.Text)
    dll_version = db.Column(db.String(50))
    csgo_process_id = db.Column(db.Integer)


class AdminUser(db.Model):
    __tablename__ = "admin_users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="moderator")  # admin, moderator
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)


class SystemLog(db.Model):
    __tablename__ = "system_logs"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin_users.id", ondelete="SET NULL"))
    action_type = db.Column(db.String(100), nullable=False)
    target_user_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DllFile(db.Model):
    __tablename__ = "dll_files"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    version = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    md5_hash = db.Column(db.String(32), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("admin_users.id", ondelete="SET NULL"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)


class Setting(db.Model):
    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdminLoginAttempt(db.Model):
    __tablename__ = "admin_login_attempts"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip_address = db.Column(db.String(45), nullable=False)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)


class ApiToken(db.Model):
    __tablename__ = "api_tokens"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
