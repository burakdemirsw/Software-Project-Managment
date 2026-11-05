"""Dashboard and simple statistics."""
from datetime import date, timedelta

from flask import Blueprint, render_template

from .db import query_all, scalar
from .scheduling import utilization

bp = Blueprint("reports", __name__, url_prefix="/reports")


def week_range(today=None):
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=4)


@bp.route("/")
def dashboard():
    today = date.today().isoformat()
    monday, friday = week_range()
    counts = {
        "patients": scalar("SELECT COUNT(*) FROM patients"),
        "doctors": scalar("SELECT COUNT(*) FROM doctors"),
        "today": scalar("SELECT COUNT(*) FROM appointments WHERE appt_date = ? AND status <> 'CANCELLED'",
                        (today,)),
    }
    by_status = query_all("SELECT status, COUNT(*) AS n FROM appointments GROUP BY status ORDER BY status")
    total = sum(r["n"] for r in by_status)
    cancelled = next((r["n"] for r in by_status if r["status"] == "CANCELLED"), 0)
    cancel_rate = round(100 * cancelled / total, 1) if total else 0.0

    doctor_rows = query_all(
        "SELECT d.id, d.full_name, d.start_hour, d.end_hour, dep.name AS department,"
        " (SELECT COUNT(*) FROM appointments a WHERE a.doctor_id = d.id"
        "   AND a.status <> 'CANCELLED' AND a.appt_date BETWEEN ? AND ?) AS booked"
        " FROM doctors d JOIN departments dep ON dep.id = d.department_id ORDER BY d.full_name",
        (monday.isoformat(), friday.isoformat()),
    )
    doctors = [
        dict(r, utilization=round(100 * utilization(r["booked"], r["start_hour"], r["end_hour"], 5), 1))
        for r in doctor_rows
    ]
    upcoming = query_all(
        "SELECT TOP 10 a.appt_date, a.appt_time, p.full_name AS patient, d.full_name AS doctor"
        " FROM appointments a JOIN patients p ON p.id = a.patient_id"
        " JOIN doctors d ON d.id = a.doctor_id"
        " WHERE a.status = 'BOOKED' AND a.appt_date >= ?"
        " ORDER BY a.appt_date, a.appt_time",
        (today,),
    )
    return render_template("dashboard.html", counts=counts, by_status=by_status,
                           cancel_rate=cancel_rate, doctors=doctors, upcoming=upcoming,
                           monday=monday, friday=friday)
