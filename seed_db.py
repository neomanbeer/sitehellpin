"""
Seed database: create default admin and settings if empty.
Run once after deploy: python seed_db.py
Or the app will auto-seed on first run if no admin exists.
"""
import bcrypt
from app import app
from models import db, AdminUser, User, Setting

with app.app_context():
    db.create_all()
    if AdminUser.query.count() == 0:
        pw = bcrypt.hashpw(b"password", bcrypt.gensalt()).decode("utf-8")
        db.session.add(AdminUser(username="admin", password=pw, role="admin"))
        db.session.add(AdminUser(username="moderator", password=pw, role="moderator"))
        print("Created admin and moderator (password: password)")
    if User.query.count() == 0:
        pw = bcrypt.hashpw(b"password", bcrypt.gensalt()).decode("utf-8")
        from datetime import datetime, timedelta
        db.session.add(User(
            username="testuser",
            password=pw,
            secondary_group_ids="[6]",
            subscription_expires=datetime.utcnow() + timedelta(days=365),
        ))
        print("Created testuser (password: password)")
    for key, val in [("dll_download_url", ""), ("admin_max_login_attempts", "5"), ("admin_lockout_minutes", "15"), ("session_lifetime", "3600")]:
        if Setting.query.filter_by(setting_key=key).first() is None:
            db.session.add(Setting(setting_key=key, setting_value=val))
    db.session.commit()
    print("Seed done.")
