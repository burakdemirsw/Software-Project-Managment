"""Appointment module: book, list, cancel and complete appointments."""
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .db import IntegrityError, execute, insert, query_all, query_one
from .scheduling import free_slots, validate_request

bp = Blueprint("appointments", __name__, url_prefix="/appointments")

ACTIVE = "status IN ('BOOKED', 'COMPLETED')"


def _taken_times(doctor_id, appt_date):
    rows = query_all(f"SELECT appt_time FROM appointments WHERE doctor_id = ? AND appt_date = ? AND {ACTIVE}",
                     (doctor_id, appt_date))
    return [r["appt_time"] for r in rows]


def book(patient_id, doctor_id, appt_date, appt_time, reason=None, now=None):
    """Try to book an appointment. Returns (new_id, errors)."""
    doctor = query_one("SELECT * FROM doctors WHERE id = ?", (doctor_id,)) if doctor_id else None
    patient = query_one("SELECT id FROM patients WHERE id = ?", (patient_id,)) if patient_id else None
    if doctor is None or patient is None:
        return None, ["Please select a valid patient and doctor."]

    errors = validate_request(appt_date, appt_time, doctor["start_hour"], doctor["end_hour"], now)
    if errors:
        return None, errors

    if appt_time in _taken_times(doctor_id, appt_date):
        return None, ["The doctor is not free at this time."]
    clash = query_one(f"SELECT 1 AS x FROM appointments WHERE patient_id = ? AND appt_date = ?"
                      f" AND appt_time = ? AND {ACTIVE}", (patient_id, appt_date, appt_time))
    if clash:
        return None, ["The patient already has an appointment at this time."]

    try:
        new_id = insert(
            "INSERT INTO appointments (patient_id, doctor_id, appt_date, appt_time, reason)"
            " OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?)",
            (patient_id, doctor_id, appt_date, appt_time, reason or None),
        )
    except IntegrityError:
        # Two users booked the same slot at the same moment: the unique index stops it.
        return None, ["This slot was just taken. Please choose another time."]
    return new_id, []


@bp.route("/")
def list_appointments():
    day = request.args.get("date", "")
    status = request.args.get("status", "")
    sql = (
        "SELECT a.*, p.full_name AS patient, d.full_name AS doctor, dep.name AS department"
        " FROM appointments a"
        " JOIN patients p ON p.id = a.patient_id"
        " JOIN doctors d ON d.id = a.doctor_id"
        " JOIN departments dep ON dep.id = d.department_id WHERE 1=1"
    )
    params = []
    if day:
        sql += " AND a.appt_date = ?"
        params.append(day)
    if status:
        sql += " AND a.status = ?"
        params.append(status)
    rows = query_all(sql + " ORDER BY a.appt_date, a.appt_time", params)
    return render_template("appointments/list.html", appointments=rows, day=day, status=status)


@bp.route("/new", methods=("GET", "POST"))
def create():
    if request.method == "POST":
        f = request.form
        new_id, errors = book(f.get("patient_id", type=int), f.get("doctor_id", type=int),
                              f.get("appt_date"), f.get("appt_time"), f.get("reason"))
        if not errors:
            flash(f"Appointment #{new_id} booked.", "ok")
            return redirect(url_for("appointments.list_appointments"))
        for e in errors:
            flash(e, "error")
    patients = query_all("SELECT id, full_name, national_id FROM patients ORDER BY full_name")
    doctors = query_all(
        "SELECT d.id, d.full_name, dep.name AS department FROM doctors d"
        " JOIN departments dep ON dep.id = d.department_id ORDER BY d.full_name"
    )
    return render_template("appointments/form.html", patients=patients, doctors=doctors,
                           form=request.form)


@bp.route("/slots")
def slots():
    """JSON list of free slots for a doctor on a day. Used by the booking form."""
    doctor_id = request.args.get("doctor_id", type=int)
    day = request.args.get("date", "")
    doctor = query_one("SELECT * FROM doctors WHERE id = ?", (doctor_id,)) if doctor_id else None
    if doctor is None or not day:
        return jsonify([])
    return jsonify(free_slots(doctor["start_hour"], doctor["end_hour"], _taken_times(doctor["id"], day)))


def _set_status(aid, new_status, message):
    changed = execute("UPDATE appointments SET status = ? WHERE id = ? AND status = 'BOOKED'",
                      (new_status, aid))
    if changed:
        flash(message, "ok")
    else:
        flash("Only booked appointments can be changed.", "error")
    return redirect(url_for("appointments.list_appointments"))


@bp.route("/<int:aid>/cancel", methods=("POST",))
def cancel(aid):
    return _set_status(aid, "CANCELLED", "Appointment cancelled.")


@bp.route("/<int:aid>/complete", methods=("POST",))
def complete(aid):
    return _set_status(aid, "COMPLETED", "Appointment marked as completed.")
