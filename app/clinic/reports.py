"""Dashboard and reporting (date range, department / doctor / reason breakdowns, CSV export)."""
import csv
import io
from datetime import date, timedelta

from flask import Blueprint, Response, render_template, request

from .db import query_all, scalar
from .scheduling import day_slots, utilization

bp = Blueprint("reports", __name__, url_prefix="/reports")


def week_range(today=None):
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=4)


def working_days(start, end):
    days, d = 0, start
    while d <= end:
        days += d.weekday() < 5
        d += timedelta(days=1)
    return days


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
        "SELECT TOP 8 a.appt_date, a.appt_time, p.full_name AS patient, d.full_name AS doctor,"
        " r.name AS reason"
        " FROM appointments a JOIN patients p ON p.id = a.patient_id"
        " JOIN doctors d ON d.id = a.doctor_id"
        " LEFT JOIN appointment_reasons r ON r.id = a.reason_id"
        " WHERE a.status = 'BOOKED' AND a.appt_date >= ?"
        " ORDER BY a.appt_date, a.appt_time",
        (today,),
    )
    return render_template("dashboard.html", counts=counts, by_status=by_status,
                           cancel_rate=cancel_rate, doctors=doctors, upcoming=upcoming,
                           monday=monday, friday=friday)


# ------------------------------------------------------------------ reporting
def _filters():
    """Read date range and optional department from the query string."""
    today = date.today()
    try:
        start = date.fromisoformat(request.args.get("from", ""))
    except ValueError:
        start = today.replace(day=1)
    try:
        end = date.fromisoformat(request.args.get("to", ""))
    except ValueError:
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    if end < start:
        start, end = end, start
    dep = request.args.get("department_id", type=int)
    return start, end, dep


def _where(start, end, dep):
    sql = " WHERE a.appt_date BETWEEN ? AND ?"
    params = [start.isoformat(), end.isoformat()]
    if dep:
        sql += " AND d.department_id = ?"
        params.append(dep)
    return sql, params


BASE = (" FROM appointments a JOIN doctors d ON d.id = a.doctor_id"
        " JOIN departments dep ON dep.id = d.department_id"
        " LEFT JOIN appointment_reasons r ON r.id = a.reason_id")
COUNTS = (" COUNT(*) AS total,"
          " SUM(CASE WHEN a.status = 'BOOKED' THEN 1 ELSE 0 END) AS booked,"
          " SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,"
          " SUM(CASE WHEN a.status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled")


def _with_rate(rows):
    for r in rows:
        r["cancel_rate"] = round(100 * r["cancelled"] / r["total"], 1) if r["total"] else 0.0
    return rows


def build_report(start, end, dep):
    where, params = _where(start, end, dep)
    summary = query_all("SELECT" + COUNTS + BASE + where, params)[0]
    summary = {k: (v or 0) for k, v in summary.items()}
    summary["cancel_rate"] = round(100 * summary["cancelled"] / summary["total"], 1) if summary["total"] else 0.0
    by_department = _with_rate(query_all(
        "SELECT dep.name AS label," + COUNTS + BASE + where + " GROUP BY dep.name ORDER BY total DESC", params))
    by_reason = _with_rate(query_all(
        "SELECT COALESCE(r.name, '(no reason)') AS label," + COUNTS + BASE + where
        + " GROUP BY COALESCE(r.name, '(no reason)') ORDER BY total DESC", params))
    doctor_rows = _with_rate(query_all(
        "SELECT d.full_name AS label, dep.name AS department, d.start_hour, d.end_hour," + COUNTS + BASE + where
        + " GROUP BY d.full_name, dep.name, d.start_hour, d.end_hour ORDER BY total DESC", params))
    days = working_days(start, end)
    for r in doctor_rows:
        r["utilization"] = round(100 * utilization(r["total"] - r["cancelled"], r["start_hour"],
                                                   r["end_hour"], days), 1)
        r["capacity"] = len(day_slots(r["start_hour"], r["end_hour"])) * days
    by_weekday = query_all(
        "SELECT DATEPART(weekday, a.appt_date) AS wd, DATENAME(weekday, a.appt_date) AS label,"
        + COUNTS + BASE + where
        + " GROUP BY DATEPART(weekday, a.appt_date), DATENAME(weekday, a.appt_date) ORDER BY wd", params)
    by_hour = query_all(
        "SELECT LEFT(a.appt_time, 2) + ':00' AS label," + COUNTS + BASE + where
        + " GROUP BY LEFT(a.appt_time, 2) ORDER BY label", params)
    return {"summary": summary, "by_department": by_department, "by_reason": by_reason,
            "by_doctor": doctor_rows, "by_weekday": _with_rate(by_weekday), "by_hour": _with_rate(by_hour),
            "working_days": days}


@bp.route("/analytics")
def analytics():
    start, end, dep = _filters()
    data = build_report(start, end, dep)
    departments = query_all("SELECT id, name FROM departments ORDER BY name")
    peak = max((r["total"] for r in data["by_weekday"] + data["by_hour"]), default=0)
    return render_template("reports/analytics.html", start=start, end=end, dep=dep,
                           departments=departments, peak=peak or 1, **data)


@bp.route("/export.csv")
def export_csv():
    """All appointments in the selected range as a CSV file (opens in Excel)."""
    start, end, dep = _filters()
    where, params = _where(start, end, dep)
    rows = query_all(
        "SELECT a.id, a.appt_date, a.appt_time, p.national_id, p.full_name AS patient,"
        " d.full_name AS doctor, dep.name AS department, r.name AS reason, a.notes, a.status,"
        " u.username AS created_by"
        + BASE + " JOIN patients p ON p.id = a.patient_id LEFT JOIN users u ON u.id = a.created_by"
        + where + " ORDER BY a.appt_date, a.appt_time", params)
    buf = io.StringIO()
    buf.write("﻿")  # BOM so Excel shows Turkish characters correctly
    writer = csv.writer(buf, delimiter=";")
    header = ["id", "appt_date", "appt_time", "national_id", "patient", "doctor", "department",
              "reason", "notes", "status", "created_by"]
    writer.writerow(header)
    for r in rows:
        writer.writerow([r[h] if r[h] is not None else "" for h in header])
    name = f"appointments_{start.isoformat()}_{end.isoformat()}.csv"
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={name}"})
