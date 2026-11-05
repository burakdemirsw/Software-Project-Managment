"""Doctor module: list doctors, add and edit doctors and their working hours."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from .db import execute, insert, query_all, query_one

bp = Blueprint("doctors", __name__, url_prefix="/doctors")


def _departments():
    return query_all("SELECT * FROM departments ORDER BY name")


def _form_errors(form):
    errors = []
    if not form.get("full_name", "").strip():
        errors.append("Full name is required.")
    if not form.get("department_id"):
        errors.append("Department is required.")
    try:
        start, end = int(form.get("start_hour", "")), int(form.get("end_hour", ""))
        if not (0 <= start < end <= 24):
            errors.append("Working hours are not valid (start must be before end).")
    except ValueError:
        errors.append("Working hours must be numbers.")
    return errors


def _values(f):
    return (f["full_name"].strip(), int(f["department_id"]), f.get("phone") or None,
            f.get("email") or None, int(f["start_hour"]), int(f["end_hour"]))


@bp.route("/")
def list_doctors():
    rows = query_all(
        "SELECT d.*, dep.name AS department FROM doctors d"
        " JOIN departments dep ON dep.id = d.department_id ORDER BY dep.name, d.full_name"
    )
    return render_template("doctors/list.html", doctors=rows)


@bp.route("/new", methods=("GET", "POST"))
def create():
    if request.method == "POST":
        errors = _form_errors(request.form)
        if not errors:
            insert("INSERT INTO doctors (full_name, department_id, phone, email, start_hour, end_hour)"
                   " OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?, ?)", _values(request.form))
            flash("Doctor saved.", "ok")
            return redirect(url_for("doctors.list_doctors"))
        for e in errors:
            flash(e, "error")
    return render_template("doctors/form.html", doctor=request.form,
                           departments=_departments(), title="New doctor")


@bp.route("/<int:did>/edit", methods=("GET", "POST"))
def edit(did):
    doctor = query_one("SELECT * FROM doctors WHERE id = ?", (did,))
    if doctor is None:
        flash("Doctor not found.", "error")
        return redirect(url_for("doctors.list_doctors"))
    if request.method == "POST":
        errors = _form_errors(request.form)
        if not errors:
            execute("UPDATE doctors SET full_name=?, department_id=?, phone=?, email=?,"
                    " start_hour=?, end_hour=? WHERE id=?", _values(request.form) + (did,))
            flash("Doctor updated.", "ok")
            return redirect(url_for("doctors.list_doctors"))
        for e in errors:
            flash(e, "error")
        doctor = request.form
    return render_template("doctors/form.html", doctor=doctor,
                           departments=_departments(), title="Edit doctor")
