"""Patient module: list, search, add, edit, delete patients."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from .db import IntegrityError, execute, insert, query_all, query_one, scalar
from .scheduling import is_valid_national_id

bp = Blueprint("patients", __name__, url_prefix="/patients")


def _form_errors(form):
    errors = []
    if not form.get("full_name", "").strip():
        errors.append("Full name is required.")
    if not is_valid_national_id(form.get("national_id", "").strip()):
        errors.append("National ID is not valid (11 digits, checksum).")
    if not form.get("birth_date"):
        errors.append("Birth date is required.")
    return errors


def _values(f):
    return (f["national_id"].strip(), f["full_name"].strip(), f["birth_date"],
            f.get("phone") or None, f.get("email") or None)


@bp.route("/")
def list_patients():
    q = request.args.get("q", "").strip()
    if q:
        rows = query_all("SELECT * FROM patients WHERE full_name LIKE ? OR national_id LIKE ?"
                         " ORDER BY full_name", (f"%{q}%", f"%{q}%"))
    else:
        rows = query_all("SELECT * FROM patients ORDER BY full_name")
    return render_template("patients/list.html", patients=rows, q=q)


@bp.route("/new", methods=("GET", "POST"))
def create():
    if request.method == "POST":
        errors = _form_errors(request.form)
        if not errors:
            try:
                insert("INSERT INTO patients (national_id, full_name, birth_date, phone, email)"
                       " OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?)", _values(request.form))
                flash("Patient saved.", "ok")
                return redirect(url_for("patients.list_patients"))
            except IntegrityError:
                errors.append("A patient with this national ID already exists.")
        for e in errors:
            flash(e, "error")
    return render_template("patients/form.html", patient=request.form, title="New patient")


@bp.route("/<int:pid>/edit", methods=("GET", "POST"))
def edit(pid):
    patient = query_one("SELECT * FROM patients WHERE id = ?", (pid,))
    if patient is None:
        flash("Patient not found.", "error")
        return redirect(url_for("patients.list_patients"))
    if request.method == "POST":
        errors = _form_errors(request.form)
        if not errors:
            try:
                execute("UPDATE patients SET national_id=?, full_name=?, birth_date=?, phone=?, email=?"
                        " WHERE id=?", _values(request.form) + (pid,))
                flash("Patient updated.", "ok")
                return redirect(url_for("patients.list_patients"))
            except IntegrityError:
                errors.append("A patient with this national ID already exists.")
        for e in errors:
            flash(e, "error")
        patient = request.form
    return render_template("patients/form.html", patient=patient, title="Edit patient")


@bp.route("/<int:pid>/delete", methods=("POST",))
def delete(pid):
    if scalar("SELECT COUNT(*) FROM appointments WHERE patient_id = ?", (pid,)):
        flash("This patient has appointments and cannot be deleted.", "error")
    else:
        execute("DELETE FROM patients WHERE id = ?", (pid,))
        flash("Patient deleted.", "ok")
    return redirect(url_for("patients.list_patients"))
