"""Department module (admin): list, add, edit, activate/deactivate departments."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from .auth import admin_required
from .db import IntegrityError, execute, insert, query_all, query_one

bp = Blueprint("departments", __name__, url_prefix="/departments")


@bp.route("/")
@admin_required
def list_departments():
    rows = query_all(
        "SELECT dep.*,"
        " (SELECT COUNT(*) FROM doctors d WHERE d.department_id = dep.id) AS doctor_count,"
        " (SELECT COUNT(*) FROM appointment_reasons r WHERE r.department_id = dep.id) AS reason_count"
        " FROM departments dep ORDER BY dep.name")
    return render_template("departments/list.html", departments=rows)


def _save(dep_id=None):
    f = request.form
    name = f.get("name", "").strip()
    if not name:
        flash("Department name is required.", "error")
        return None
    values = (name, f.get("description", "").strip() or None, 1 if f.get("is_active") else 0)
    try:
        if dep_id is None:
            insert("INSERT INTO departments (name, description, is_active) OUTPUT INSERTED.id"
                   " VALUES (?, ?, ?)", values)
        else:
            execute("UPDATE departments SET name = ?, description = ?, is_active = ? WHERE id = ?",
                    values + (dep_id,))
    except IntegrityError:
        flash("A department with this name already exists.", "error")
        return None
    flash("Department saved.", "ok")
    return redirect(url_for("departments.list_departments"))


@bp.route("/new", methods=("GET", "POST"))
@admin_required
def create():
    if request.method == "POST":
        done = _save()
        if done:
            return done
    return render_template("departments/form.html", dep=request.form or {"is_active": True},
                           title="New department")


@bp.route("/<int:dep_id>/edit", methods=("GET", "POST"))
@admin_required
def edit(dep_id):
    dep = query_one("SELECT * FROM departments WHERE id = ?", (dep_id,))
    if dep is None:
        flash("Department not found.", "error")
        return redirect(url_for("departments.list_departments"))
    if request.method == "POST":
        done = _save(dep_id)
        if done:
            return done
        dep = request.form
    return render_template("departments/form.html", dep=dep, title="Edit department")
