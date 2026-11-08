"""Login system: sign in / sign out, current user, role checks and user management."""
import functools

from flask import (Blueprint, abort, flash, g, redirect, render_template, request, session,
                   url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import IntegrityError, execute, insert, query_all, query_one

bp = Blueprint("auth", __name__)

ROLES = ("ADMIN", "RECEPTIONIST")
PUBLIC_ENDPOINTS = {"auth.login", "static"}
MIN_PASSWORD = 8


def load_user():
    """Runs before every request: put the signed-in user into g.user."""
    uid = session.get("user_id")
    g.user = None
    if uid is not None:
        g.user = query_one("SELECT id, username, full_name, role FROM users WHERE id = ? AND is_active = 1",
                           (uid,))
        if g.user is None:
            session.clear()


def require_login():
    """Every page needs a signed-in user, except the login page and static files."""
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if g.user is None:
        return redirect(url_for("auth.login", next=request.full_path))
    return None


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None or g.user["role"] != "ADMIN":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def _safe_next(target):
    return target if target and target.startswith("/") and not target.startswith("//") else None


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = query_one("SELECT * FROM users WHERE username = ?", (username,))
        if user is None or not user["is_active"] or not check_password_hash(user["password_hash"], password):
            flash("Wrong username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            execute("UPDATE users SET last_login_at = SYSDATETIME() WHERE id = ?", (user["id"],))
            return redirect(_safe_next(request.args.get("next")) or url_for("reports.dashboard"))
    return render_template("auth/login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("You are signed out.", "ok")
    return redirect(url_for("auth.login"))


# ------------------------------------------------------------------ user management (admin)
def _password_error(pw):
    if len(pw) < MIN_PASSWORD or pw.isalpha() or pw.isdigit():
        return f"Password must be at least {MIN_PASSWORD} characters and contain letters and numbers."
    return None


@bp.route("/users/")
@admin_required
def list_users():
    users = query_all("SELECT id, username, full_name, role, is_active, last_login_at FROM users ORDER BY username")
    return render_template("auth/users.html", users=users)


@bp.route("/users/new", methods=("GET", "POST"))
@admin_required
def create_user():
    f = request.form
    if request.method == "POST":
        errors = []
        if not f.get("username", "").strip() or not f.get("full_name", "").strip():
            errors.append("Username and full name are required.")
        if f.get("role") not in ROLES:
            errors.append("Please select a role.")
        pw_error = _password_error(f.get("password", ""))
        if pw_error:
            errors.append(pw_error)
        if not errors:
            try:
                insert("INSERT INTO users (username, full_name, password_hash, role) OUTPUT INSERTED.id"
                       " VALUES (?, ?, ?, ?)",
                       (f["username"].strip(), f["full_name"].strip(),
                        generate_password_hash(f["password"]), f["role"]))
                flash("User created.", "ok")
                return redirect(url_for("auth.list_users"))
            except IntegrityError:
                errors.append("This username is already used.")
        for e in errors:
            flash(e, "error")
    return render_template("auth/user_form.html", form=f, roles=ROLES)


@bp.route("/users/<int:uid>/toggle", methods=("POST",))
@admin_required
def toggle_user(uid):
    if uid == g.user["id"]:
        flash("You cannot deactivate your own account.", "error")
    else:
        execute("UPDATE users SET is_active = 1 - is_active WHERE id = ?", (uid,))
        flash("User status changed.", "ok")
    return redirect(url_for("auth.list_users"))


@bp.route("/account/password", methods=("GET", "POST"))
def change_password():
    if request.method == "POST":
        user = query_one("SELECT password_hash FROM users WHERE id = ?", (g.user["id"],))
        new = request.form.get("new_password", "")
        if not check_password_hash(user["password_hash"], request.form.get("old_password", "")):
            flash("Current password is wrong.", "error")
        elif new != request.form.get("new_password2", ""):
            flash("The new passwords do not match.", "error")
        elif _password_error(new):
            flash(_password_error(new), "error")
        else:
            execute("UPDATE users SET password_hash = ? WHERE id = ?",
                    (generate_password_hash(new), g.user["id"]))
            flash("Password changed.", "ok")
            return redirect(url_for("reports.dashboard"))
    return render_template("auth/password.html")
