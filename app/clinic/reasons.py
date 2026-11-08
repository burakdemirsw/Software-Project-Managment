"""Appointment reason module (admin): standard reasons for a visit, general or per department."""
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .auth import admin_required
from .db import IntegrityError, execute, insert, query_all, query_one

bp = Blueprint("reasons", __name__, url_prefix="/reasons")


def active_reasons_for_doctor(doctor_id):
    """Reasons that fit the doctor's department, plus general reasons."""
    return query_all(
        "SELECT r.id, r.name FROM appointment_reasons r"
        " WHERE r.is_active = 1 AND (r.department_id IS NULL OR r.department_id ="
        "   (SELECT department_id FROM doctors WHERE id = ?))"
        " ORDER BY CASE WHEN r.department_id IS NULL THEN 1 ELSE 0 END, r.name",
        (doctor_id,))


@bp.route("/")
@admin_required
def list_reasons():
    rows = query_all(
        "SELECT r.*, dep.name AS department,"
        " (SELECT COUNT(*) FROM appointments a WHERE a.reason_id = r.id) AS used"
        " FROM appointment_reasons r LEFT JOIN departments dep ON dep.id = r.department_id"
        " ORDER BY dep.name, r.name")
    return render_template("reasons/list.html", reasons=rows)


def _departments():
    return query_all("SELECT id, name FROM departments WHERE is_active = 1 ORDER BY name")


def _save(reason_id=None):
    f = request.form
    name = f.get("name", "").strip()
    if not name:
        flash("Reason name is required.", "error")
        return None
    values = (name, f.get("department_id", type=int) or None,
              f.get("description", "").strip() or None, 1 if f.get("is_active") else 0)
    try:
        if reason_id is None:
            insert("INSERT INTO appointment_reasons (name, department_id, description, is_active)"
                   " OUTPUT INSERTED.id VALUES (?, ?, ?, ?)", values)
        else:
            execute("UPDATE appointment_reasons SET name = ?, department_id = ?, description = ?,"
                    " is_active = ? WHERE id = ?", values + (reason_id,))
    except IntegrityError:
        flash("A reason with this name already exists.", "error")
        return None
    flash("Reason saved.", "ok")
    return redirect(url_for("reasons.list_reasons"))


@bp.route("/new", methods=("GET", "POST"))
@admin_required
def create():
    if request.method == "POST":
        done = _save()
        if done:
            return done
    return render_template("reasons/form.html", reason=request.form or {"is_active": True},
                           departments=_departments(), title="New appointment reason")


@bp.route("/<int:reason_id>/edit", methods=("GET", "POST"))
@admin_required
def edit(reason_id):
    reason = query_one("SELECT * FROM appointment_reasons WHERE id = ?", (reason_id,))
    if reason is None:
        flash("Reason not found.", "error")
        return redirect(url_for("reasons.list_reasons"))
    if request.method == "POST":
        done = _save(reason_id)
        if done:
            return done
        reason = request.form
    return render_template("reasons/form.html", reason=reason, departments=_departments(),
                           title="Edit appointment reason")


@bp.route("/for-doctor")
def for_doctor():
    """JSON list of reasons for the booking form (any signed-in user)."""
    doctor_id = request.args.get("doctor_id", type=int)
    return jsonify(active_reasons_for_doctor(doctor_id) if doctor_id else [])
