"""
Flask app - Loader API + Admin panel.
Run locally: flask run  or  python run_local.py
Render: gunicorn app:app
"""
import os
from flask import Flask, request
import config as app_config
from models import db, init_db

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = app_config.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = app_config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB for DLL uploads
    init_db(app)
    with app.app_context():
        # Add hwid column to users if missing (existing DBs)
        from sqlalchemy import text
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN hwid VARCHAR(255)"))
            db.session.commit()
        except Exception:
            db.session.rollback()
        # Auto-seed default admin if empty (for Render / first deploy)
        from models import AdminUser, Setting
        if AdminUser.query.count() == 0:
            import bcrypt
            pw = bcrypt.hashpw(b"password", bcrypt.gensalt()).decode("utf-8")
            db.session.add(AdminUser(username="admin", password=pw, role="admin"))
            for key, val in [("dll_download_url", ""), ("admin_max_login_attempts", "5"), ("admin_lockout_minutes", "15"), ("session_lifetime", "3600")]:
                if Setting.query.filter_by(setting_key=key).first() is None:
                    db.session.add(Setting(setting_key=key, setting_value=val))
            db.session.commit()
    return app


app = create_app()


@app.route("/")
def index():
    from flask import redirect
    return redirect("/admin/login")


# Register blueprints
from api_routes import api_bp
from admin_routes import admin_bp
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(admin_bp, url_prefix="/admin")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=app_config.DEBUG)
