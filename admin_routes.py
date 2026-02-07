"""
Admin panel routes - all in English. Session-based auth.
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, url_for, render_template, session, flash
from functools import wraps
from models import (
    db, User, AdminUser, InjectionLog, SystemLog, DllFile, Setting, AdminLoginAttempt,
)
from helpers import get_client_ip, get_setting, set_setting
import config as app_config
import bcrypt
import os
import hashlib

admin_bp = Blueprint("admin", __name__, template_folder="templates")


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin.login", next=request.url))
        return f(*args, **kwargs)
    return wrapped


def admin_full_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin.login", next=request.url))
        if session.get("admin_role") != "admin":
            flash("Admin role required.", "danger")
            return redirect(url_for("admin.index"))
        return f(*args, **kwargs)
    return wrapped


def log_system(action_type, target_user_id=None, details=None):
    db.session.add(SystemLog(
        admin_id=session.get("admin_id"),
        action_type=action_type,
        target_user_id=target_user_id,
        details=details,
        ip_address=get_client_ip(),
    ))
    db.session.commit()


def check_login_attempts():
    ip = get_client_ip()
    minutes = int(get_setting("admin_lockout_minutes", app_config.ADMIN_LOCKOUT_MINUTES))
    max_attempts = int(get_setting("admin_max_login_attempts", app_config.ADMIN_MAX_LOGIN_ATTEMPTS))
    since = datetime.utcnow() - timedelta(minutes=minutes)
    count = AdminLoginAttempt.query.filter(
        AdminLoginAttempt.ip_address == ip,
        AdminLoginAttempt.attempted_at >= since,
    ).count()
    return count < max_attempts


def record_login_attempt():
    db.session.add(AdminLoginAttempt(ip_address=get_client_ip()))
    db.session.commit()


# ---------- Login / Logout ----------
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_id"):
        return redirect(url_for("admin.index"))
    if request.method == "POST":
        if not check_login_attempts():
            flash("Too many login attempts. Try again later.", "danger")
            return render_template("admin/login.html")
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or not password:
            record_login_attempt()
            flash("Invalid username or password.", "danger")
            return render_template("admin/login.html")
        admin = AdminUser.query.filter_by(username=username).first()
        if not admin or not bcrypt.checkpw(password.encode("utf-8"), admin.password.encode("utf-8")):
            record_login_attempt()
            flash("Invalid username or password.", "danger")
            return render_template("admin/login.html")
        admin.last_login = datetime.utcnow()
        db.session.commit()
        session["admin_id"] = admin.id
        session["admin_username"] = admin.username
        session["admin_role"] = admin.role
        next_url = request.args.get("next") or url_for("admin.index")
        return redirect(next_url)
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


# ---------- Dashboard ----------
@admin_bp.route("/")
@admin_required
def index():
    from sqlalchemy import func, and_
    users_total = User.query.count()
    users_banned = User.query.filter_by(is_banned=True).count()
    injections_today = InjectionLog.query.filter(
        func.date(InjectionLog.injection_time) == datetime.utcnow().date()
    ).count()
    injections_week = InjectionLog.query.filter(
        InjectionLog.injection_time >= datetime.utcnow() - timedelta(days=7)
    ).count()
    injections_month = InjectionLog.query.filter(
        InjectionLog.injection_time >= datetime.utcnow() - timedelta(days=30)
    ).count()
    # Active subs: group 6 and not expired
    active_subs = 0
    for u in User.query.filter_by(is_banned=False).all():
        if u.has_subscription():
            active_subs += 1
    last_injections = InjectionLog.query.order_by(InjectionLog.injection_time.desc()).limit(10).all()
    last_logs = db.session.query(SystemLog, AdminUser.username).outerjoin(
        AdminUser, AdminUser.id == SystemLog.admin_id
    ).order_by(SystemLog.created_at.desc()).limit(10).all()
    chart_rows = db.session.query(
        func.date(InjectionLog.injection_time).label("d"),
        func.count(InjectionLog.id).label("c"),
    ).filter(
        InjectionLog.injection_time >= datetime.utcnow() - timedelta(days=14)
    ).group_by(func.date(InjectionLog.injection_time)).order_by("d").all()
    chart_labels = [str(r.d) for r in chart_rows]
    chart_values = [r.c for r in chart_rows]
    top_users = db.session.query(
        InjectionLog.username,
        InjectionLog.user_id,
        func.count(InjectionLog.id).label("cnt"),
    ).filter(InjectionLog.user_id.isnot(None)).group_by(
        InjectionLog.user_id, InjectionLog.username
    ).order_by(func.count(InjectionLog.id).desc()).limit(10).all()
    return render_template(
        "admin/index.html",
        users_total=users_total,
        users_banned=users_banned,
        active_subs=active_subs,
        injections_today=injections_today,
        injections_week=injections_week,
        injections_month=injections_month,
        last_injections=last_injections,
        last_logs=last_logs,
        chart_labels=chart_labels,
        chart_values=chart_values,
        top_users=top_users,
    )


# ---------- Users ----------
@admin_bp.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST" and session.get("admin_role") == "admin":
        action = request.form.get("action")
        uid = request.form.get("user_id", type=int)
        if action == "ban" and uid:
            u = User.query.get(uid)
            if u:
                u.is_banned = True
                u.ban_reason = (request.form.get("ban_reason") or "").strip()
                u.banned_by = session.get("admin_id")
                u.banned_at = datetime.utcnow()
                db.session.commit()
                log_system("user_banned", uid, f'{{"reason":"{u.ban_reason}"}}')
                flash("User banned.", "success")
                return redirect(url_for("admin.users"))
        if action == "unban" and uid:
            u = User.query.get(uid)
            if u:
                u.is_banned = False
                u.ban_reason = None
                u.banned_by = None
                u.banned_at = None
                db.session.commit()
                log_system("user_unbanned", uid, None)
                flash("User unbanned.", "success")
                return redirect(url_for("admin.users"))
        if action == "add_user":
            new_login = (request.form.get("new_username") or "").strip()
            new_pass = request.form.get("new_password") or ""
            new_hwid = (request.form.get("new_hwid") or "").strip()
            if not new_login:
                flash("Username required.", "danger")
            elif User.query.filter_by(username=new_login).first():
                flash("Username already exists.", "danger")
            elif len(new_pass) < 4:
                flash("Password must be at least 4 characters.", "danger")
            else:
                pw_hash = bcrypt.hashpw(new_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                grant_sub = request.form.get("grant_subscription") == "1"
                sub_expires_str = (request.form.get("new_sub_expires") or "").strip()
                u = User(username=new_login, password=pw_hash, secondary_group_ids="[6]" if grant_sub else "[]")
                if grant_sub and sub_expires_str:
                    try:
                        u.subscription_expires = datetime.strptime(sub_expires_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                    except ValueError:
                        u.subscription_expires = None
                elif not grant_sub:
                    u.subscription_expires = None
                if new_hwid:
                    u.hwid = new_hwid
                db.session.add(u)
                db.session.commit()
                log_system("user_created", u.id, f'{{"username":"{new_login}"}}')
                flash("User added.", "success")
                return redirect(url_for("admin.users"))
        if action == "set_hwid" and uid:
            u = User.query.get(uid)
            if u:
                new_hwid = (request.form.get("hwid_value") or "").strip()
                u.hwid = new_hwid if new_hwid else None
                db.session.commit()
                log_system("user_hwid_updated", uid, None)
                flash("HWID updated.", "success")
                return redirect(url_for("admin.users"))
        if action == "set_subscription" and uid:
            u = User.query.get(uid)
            if u:
                expires_str = (request.form.get("sub_expires") or "").strip()
                u.secondary_group_ids = "[6]"
                if expires_str:
                    try:
                        from datetime import datetime as dt
                        u.subscription_expires = dt.strptime(expires_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                    except ValueError:
                        u.subscription_expires = None
                else:
                    u.subscription_expires = None  # lifetime
                db.session.commit()
                log_system("subscription_set", uid, f'{{"expires":"{expires_str or "lifetime"}"}}')
                flash("Subscription updated.", "success")
                return redirect(url_for("admin.users"))
        if action == "remove_subscription" and uid:
            u = User.query.get(uid)
            if u:
                u.secondary_group_ids = "[]"
                u.subscription_expires = None
                db.session.commit()
                log_system("subscription_removed", uid, None)
                flash("Subscription removed.", "success")
                return redirect(url_for("admin.users"))
    search = (request.args.get("search") or "").strip()
    banned_only = request.args.get("banned_only") == "1"
    sub_only = request.args.get("sub_only") == "1"
    page = max(1, request.args.get("p", type=int) or 1)
    per_page = 50
    q = User.query
    if search:
        q = q.filter(User.username.contains(search))
    if banned_only:
        q = q.filter(User.is_banned == True)
    if sub_only:
        all_users = q.order_by(User.id.desc()).all()
        filtered = [u for u in all_users if u.has_subscription()]
        total = len(filtered)
        total_pages = max(1, (total + per_page - 1) // per_page)
        users_list = filtered[(page - 1) * per_page:page * per_page]
    else:
        pagination = q.order_by(User.id.desc()).paginate(page=page, per_page=per_page)
        users_list = pagination.items
        total_pages = pagination.pages
    injection_counts = {}
    for u in users_list:
        injection_counts[u.id] = InjectionLog.query.filter_by(user_id=u.id).count()
    return render_template(
        "admin/users.html",
        users=users_list,
        page=page,
        total_pages=total_pages,
        search=search,
        banned_only=banned_only,
        sub_only=sub_only,
        injection_counts=injection_counts,
        is_full_admin=session.get("admin_role") == "admin",
    )


# ---------- Injections ----------
@admin_bp.route("/injections")
@admin_required
def injections():
    if request.args.get("export") == "csv":
        from flask import Response
        import csv
        import io
        q = InjectionLog.query
        if request.args.get("username"):
            q = q.filter(InjectionLog.username.contains(request.args.get("username")))
        if request.args.get("ip"):
            q = q.filter(InjectionLog.ip_address == request.args.get("ip"))
        if request.args.get("status"):
            q = q.filter(InjectionLog.status == request.args.get("status"))
        if request.args.get("date_from"):
            q = q.filter(InjectionLog.injection_time >= request.args.get("date_from"))
        if request.args.get("date_to"):
            q = q.filter(InjectionLog.injection_time <= request.args.get("date_to") + " 23:59:59")
        rows = q.order_by(InjectionLog.injection_time.desc()).all()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["ID", "Username", "IP", "Time", "Status", "User-Agent", "DLL Version"])
        for r in rows:
            w.writerow([r.id, r.username, r.ip_address, str(r.injection_time), r.status, r.user_agent or "", r.dll_version or ""])
        return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=injections.csv"})
    search_user = (request.args.get("username") or "").strip()
    search_ip = (request.args.get("ip") or "").strip()
    status_filter = (request.args.get("status") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    page = max(1, request.args.get("p", type=int) or 1)
    per_page = 50
    q = InjectionLog.query
    if search_user:
        q = q.filter(InjectionLog.username.contains(search_user))
    if search_ip:
        q = q.filter(InjectionLog.ip_address == search_ip)
    if status_filter:
        q = q.filter(InjectionLog.status == status_filter)
    if date_from:
        q = q.filter(InjectionLog.injection_time >= date_from)
    if date_to:
        q = q.filter(InjectionLog.injection_time <= date_to + " 23:59:59")
    pagination = q.order_by(InjectionLog.injection_time.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        "admin/injections.html",
        logs=pagination.items,
        page=page,
        total_pages=pagination.pages,
        search_user=search_user,
        search_ip=search_ip,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
    )


@admin_bp.route("/injection_details/<int:log_id>")
@admin_required
def injection_details(log_id):
    log = InjectionLog.query.get_or_404(log_id)
    user = User.query.get(log.user_id) if log.user_id else None
    history = InjectionLog.query.filter_by(user_id=log.user_id).order_by(InjectionLog.injection_time.desc()).limit(20).all() if log.user_id else []
    return render_template("admin/injection_details.html", log=log, user=user, history=history)


# ---------- DLL ----------
@admin_bp.route("/dll_management", methods=["GET", "POST"])
@admin_required
def dll_management():
    if request.method == "POST" and session.get("admin_role") == "admin":
        action = request.form.get("action")
        if action == "toggle" and request.form.get("id"):
            d = DllFile.query.get(request.form.get("id", type=int))
            if d:
                d.is_active = not d.is_active
                db.session.commit()
                log_system("dll_toggled", None, f'{{"dll_id":{d.id}}}')
                flash("DLL toggled.", "success")
                return redirect(url_for("admin.dll_management"))
        if action == "delete" and request.form.get("id"):
            d = DllFile.query.get(request.form.get("id", type=int))
            if d:
                path = app_config.DLL_STORAGE / d.file_path
                if path.is_file():
                    path.unlink(missing_ok=True)
                db.session.delete(d)
                db.session.commit()
                log_system("dll_deleted", None, f'{{"dll_id":{d.id}}}')
                flash("DLL deleted.", "success")
                return redirect(url_for("admin.dll_management"))
        if action == "upload" and request.files.get("dll_file"):
            version = (request.form.get("version") or "").strip()
            desc = (request.form.get("description") or "").strip()
            if not version:
                flash("Version is required.", "danger")
            else:
                f = request.files["dll_file"]
                if f.filename and f.filename.lower().endswith(".dll"):
                    data = f.read()
                    size = len(data)
                    md5 = hashlib.md5(data).hexdigest()
                    ext = "dll"
                    fname = f"{version}_{md5[:8]}.{ext}"
                    path = app_config.DLL_STORAGE / fname
                    path.write_bytes(data)
                    DllFile.query.update({DllFile.is_active: False})
                    db.session.add(DllFile(
                        version=version,
                        file_path=fname,
                        file_size=size,
                        md5_hash=md5,
                        is_active=True,
                        uploaded_by=session.get("admin_id"),
                        description=desc or None,
                    ))
                    db.session.commit()
                    log_system("dll_uploaded", None, f'{{"version":"{version}"}}')
                    flash("DLL uploaded.", "success")
                    return redirect(url_for("admin.dll_management"))
                flash("Invalid file.", "danger")
    list_dll = DllFile.query.order_by(DllFile.uploaded_at.desc()).all()
    uploaders = {a.id: a.username for a in AdminUser.query.all()}
    return render_template(
        "admin/dll_management.html",
        list_dll=list_dll,
        uploaders=uploaders,
        is_full_admin=session.get("admin_role") == "admin",
    )


@admin_bp.route("/dll_download/<int:dll_id>")
@admin_required
def dll_download(dll_id):
    d = DllFile.query.get_or_404(dll_id)
    path = app_config.DLL_STORAGE / d.file_path
    if not path.is_file():
        flash("File not found.", "danger")
        return redirect(url_for("admin.dll_management"))
    from flask import send_file
    return send_file(
        str(path),
        as_attachment=True,
        download_name=f"loader_{d.version}.dll",
        mimetype="application/octet-stream",
    )


# ---------- System logs ----------
@admin_bp.route("/system_logs")
@admin_required
def system_logs():
    action_filter = (request.args.get("action_type") or "").strip()
    admin_filter = (request.args.get("admin") or "").strip()
    page = max(1, request.args.get("p", type=int) or 1)
    per_page = 50
    q = db.session.query(SystemLog, AdminUser.username).outerjoin(
        AdminUser, AdminUser.id == SystemLog.admin_id
    )
    if action_filter:
        q = q.filter(SystemLog.action_type == action_filter)
    if admin_filter:
        q = q.filter(AdminUser.username.contains(admin_filter))
    q = q.order_by(SystemLog.created_at.desc())
    total = q.count()
    logs = q.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max(1, (total + per_page - 1) // per_page)
    action_types = db.session.query(SystemLog.action_type).distinct().order_by(SystemLog.action_type).all()
    action_types = [x[0] for x in action_types]
    target_usernames = {}
    if logs:
        ids = list({log.target_user_id for log, _ in logs if log.target_user_id})
        for u in User.query.filter(User.id.in_(ids)).all():
            target_usernames[u.id] = u.username
    return render_template(
        "admin/system_logs.html",
        logs=logs,
        page=page,
        total_pages=total_pages,
        action_filter=action_filter,
        admin_filter=admin_filter,
        action_types=action_types,
        target_usernames=target_usernames,
    )


# ---------- API Documentation ----------
@admin_bp.route("/api_docs")
@admin_required
def api_docs():
    scheme = "https" if request.headers.get("X-Forwarded-Proto") == "https" else request.scheme
    base_url = f"{scheme}://{request.host}".rstrip("/")
    api_base = f"{base_url}/api"
    return render_template("admin/api_docs.html", api_base=api_base, base_url=base_url)


# ---------- Settings ----------
@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_full_required
def settings():
    if request.method == "POST":
        sub = request.form.get("sub")
        if sub == "settings":
            set_setting("dll_download_url", (request.form.get("dll_download_url") or "").strip())
            set_setting("admin_max_login_attempts", str(request.form.get("admin_max_login_attempts", type=int) or 5))
            set_setting("admin_lockout_minutes", str(request.form.get("admin_lockout_minutes", type=int) or 15))
            set_setting("session_lifetime", str(request.form.get("session_lifetime", type=int) or 3600))
            flash("Settings saved.", "success")
            return redirect(url_for("admin.settings"))
        if sub == "password":
            cur = request.form.get("current_password") or ""
            new_p = request.form.get("new_password") or ""
            conf = request.form.get("confirm_password") or ""
            admin = AdminUser.query.get(session["admin_id"])
            if not admin or not bcrypt.checkpw(cur.encode("utf-8"), admin.password.encode("utf-8")):
                flash("Current password is wrong.", "danger")
            elif len(new_p) < 6:
                flash("New password must be at least 6 characters.", "danger")
            elif new_p != conf:
                flash("Passwords do not match.", "danger")
            else:
                admin.password = bcrypt.hashpw(new_p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                db.session.commit()
                log_system("admin_password_changed", None, None)
                flash("Password changed.", "success")
            return redirect(url_for("admin.settings"))
    return render_template(
        "admin/settings.html",
        dll_download_url=get_setting("dll_download_url", ""),
        admin_max_login_attempts=get_setting("admin_max_login_attempts", "5"),
        admin_lockout_minutes=get_setting("admin_lockout_minutes", "15"),
        session_lifetime=get_setting("session_lifetime", "3600"),
    )
