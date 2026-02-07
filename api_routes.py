"""
API for C++ loader: auth (POST) and download (GET).
Compatible with existing loader: login, password, data=uncracked.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from models import db, User, DllFile, ApiToken
from helpers import get_client_ip, get_client_ua, log_injection, create_download_token
import config as app_config

api_bp = Blueprint("api", __name__)


@api_bp.route("/api.php", methods=["POST"])
def auth():
    """
    POST application/x-www-form-urlencoded:
    - login (required) + password  OR  login + hwid
    Returns JSON: success, message, user (id, username, secondary_group_ids, subscription_expires, download_url)
    """
    login = (request.form.get("login") or "").strip()
    password = (request.form.get("password") or "").strip()
    hwid = (request.form.get("hwid") or "").strip()

    out = {"success": False, "message": "Invalid credentials", "user": None}
    if not login:
        return jsonify(out)

    user = User.query.filter_by(username=login).first()
    if not user:
        return jsonify(out)

    if user.is_banned:
        out["message"] = "Account banned. Reason: " + (user.ban_reason or "N/A")
        return jsonify(out)

    import bcrypt
    if password:
        if not bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
            return jsonify(out)
    elif hwid:
        if not user.hwid or user.hwid.strip() != hwid:
            return jsonify(out)
    else:
        return jsonify(out)

    user.last_login = datetime.utcnow()
    db.session.commit()

    group_ids = user.get_group_ids()
    sub_exp = user.subscription_expires
    sub_exp_str = sub_exp.strftime("%Y-%m-%d %H:%M:%S") if sub_exp else None

    scheme = "https" if request.headers.get("X-Forwarded-Proto") == "https" else request.scheme
    base_url = f"{scheme}://{request.host}".rstrip("/")
    token = create_download_token(user.id)
    download_url = f"{base_url}/api/download?token={token}"

    out["success"] = True
    out["message"] = "Authorization success"
    out["user"] = {
        "id": user.id,
        "username": user.username,
        "secondary_group_ids": group_ids,
        "subscription_expires": sub_exp_str,
        "download_url": download_url,
    }
    return jsonify(out)


@api_bp.route("/download", methods=["GET"])
def download():
    """
    GET ?token=... (from auth response) or Basic Auth.
    User-Agent should contain 'inject' for loader. Serves active DLL and logs injection.
    """
    ua = get_client_ua()
    ip = get_client_ip()
    user = None

    token = request.args.get("token", "").strip()
    if token:
        t = ApiToken.query.filter_by(token=token).first()
        if t and (t.expires_at is None or t.expires_at > datetime.utcnow()):
            user = User.query.get(t.user_id)
            if user:
                db.session.delete(t)
                db.session.commit()
    if not user and request.authorization:
        u = User.query.filter_by(username=request.authorization.username).first()
        if u and u.password:
            import bcrypt
            if bcrypt.checkpw((request.authorization.password or "").encode("utf-8"), u.password.encode("utf-8")):
                user = u

    username = user.username if user else "unknown"
    user_id = user.id if user else None

    if not user:
        log_injection(None, username, ip, ua, "blocked", "Not authorized", None, None)
        return jsonify({"success": False, "message": "Forbidden"}), 403

    if user.is_banned:
        log_injection(user_id, username, ip, ua, "blocked", "User banned", None, None)
        return jsonify({"success": False, "message": "Forbidden"}), 403

    if not user.has_subscription():
        log_injection(user_id, username, ip, ua, "blocked", "No valid subscription", None, None)
        return jsonify({"success": False, "message": "Forbidden"}), 403

    dll = DllFile.query.filter_by(is_active=True).order_by(DllFile.uploaded_at.desc()).first()
    if not dll:
        log_injection(user_id, username, ip, ua, "failed", "No DLL available", None, None)
        return jsonify({"success": False, "message": "Not Found"}), 404

    path = app_config.DLL_STORAGE / dll.file_path
    if not path.is_file():
        log_injection(user_id, username, ip, ua, "failed", "DLL file missing", dll.version, None)
        return jsonify({"success": False, "message": "Not Found"}), 404

    csgo_pid = request.args.get("pid", type=int)
    log_injection(user_id, username, ip, ua, "success", None, dll.version, csgo_pid)

    return send_file(
        str(path),
        as_attachment=True,
        download_name="loader.dll",
        mimetype="application/octet-stream",
    )
