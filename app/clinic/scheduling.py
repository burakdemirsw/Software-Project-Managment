"""Business rules for booking appointments.

These functions do not use Flask or the database, so they are easy to unit test.
"""
from datetime import date, datetime, timedelta

SLOT_MINUTES = 30


def day_slots(start_hour, end_hour, slot_minutes=SLOT_MINUTES):
    """All slot start times of a working day, e.g. ['09:00', '09:30', ...]."""
    slots = []
    t = datetime(2000, 1, 1, start_hour, 0)
    end = datetime(2000, 1, 1, 0, 0) + timedelta(hours=end_hour)
    while t + timedelta(minutes=slot_minutes) <= end:
        slots.append(t.strftime("%H:%M"))
        t += timedelta(minutes=slot_minutes)
    return slots


def validate_request(appt_date, appt_time, start_hour, end_hour, now=None):
    """Check the date and time of a new appointment.

    Returns a list of error messages. An empty list means the request is valid.
    """
    now = now or datetime.now()
    errors = []
    try:
        d = date.fromisoformat(appt_date)
    except (TypeError, ValueError):
        return ["Date must be in YYYY-MM-DD format."]
    if appt_time not in day_slots(start_hour, end_hour):
        errors.append(
            f"Time must be a {SLOT_MINUTES}-minute slot between "
            f"{start_hour:02d}:00 and {end_hour:02d}:00."
        )
        return errors
    if d.weekday() >= 5:
        errors.append("The clinic is closed on weekends.")
    start = datetime.combine(d, datetime.strptime(appt_time, "%H:%M").time())
    if start <= now:
        errors.append("You cannot book an appointment in the past.")
    if d > (now.date() + timedelta(days=90)):
        errors.append("Appointments can be booked at most 90 days ahead.")
    return errors


def free_slots(start_hour, end_hour, taken_times):
    """Slots of the day that are not in taken_times."""
    taken = set(taken_times)
    return [s for s in day_slots(start_hour, end_hour) if s not in taken]


def utilization(booked_count, start_hour, end_hour, working_days):
    """Share of available slots that are booked (0.0 - 1.0)."""
    capacity = len(day_slots(start_hour, end_hour)) * working_days
    return 0.0 if capacity == 0 else round(booked_count / capacity, 3)


def is_valid_national_id(value):
    """Turkish national ID (TC Kimlik No) checksum algorithm."""
    if not value or len(value) != 11 or not value.isdigit() or value[0] == "0":
        return False
    d = [int(c) for c in value]
    tenth = ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10
    eleventh = sum(d[:10]) % 10
    return d[9] == tenth and d[10] == eleventh
