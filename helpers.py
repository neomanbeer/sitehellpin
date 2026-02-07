"""
Shared helpers for API and admin.
"""
from flask import request
from models import db, Setting, InjectionLog, ApiToken
from datetime import datetime, timedelta
import secrets


def get_client_ip():
    return request.headers.get("X-Forwarded-For", request.headers.get("X-Real-IP", request.remote_addr or "0.0.0.0"))


def get_client_ua():
    ua = request.headers.get("User-Agent")
    return (ua[:500] if ua else None) or ""


def get_setting(key, default=None):
    row = Setting.query.filter_by(setting_key=key).first()
    return (row.setting_value if row else None) or default


def set_setting(key, value):
    row = Setting.query.filter_by(setting_key=key).first()
    if row:
        row.setting_value = value
    else:
        db.session.add(Setting(setting_key=key, setting_value=value))
    db.session.commit()


def log_injection(user_id, username, ip, user_agent, status="success", error_message=None, dll_version=None, csgo_pid=None):
    db.session.add(InjectionLog(
        user_id=user_id,
        username=username,
        ip_address=ip,
        user_agent=user_agent or "",
        status=status,
        error_message=error_message,
        dll_version=dll_version,
        csgo_process_id=csgo_pid,
    ))
    db.session.commit()


def create_download_token(user_id):
    token = secrets.token_hex(32)
    expires = datetime.utcnow() + timedelta(minutes=5)
    db.session.add(ApiToken(user_id=user_id, token=token, expires_at=expires))
    db.session.commit()
    return token
