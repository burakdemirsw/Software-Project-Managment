"""Unit and integration tests.

Run from the app folder:   python -m unittest discover -s tests -v

The database tests create a separate SQL Server database
(ClinicAppointmentDB_Test on (localdb)\\MSSQLLocalDB) and delete it at the end.
"""
import os
import sys
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clinic import create_app  # noqa: E402
from clinic.appointments import book  # noqa: E402
from clinic.db import (IntegrityError, close_db, drop_database, execute,  # noqa: E402
                       init_db, query_one, scalar, seed_db)
from clinic.scheduling import (day_slots, free_slots, is_valid_national_id,  # noqa: E402
                               utilization, validate_request)

NOW = datetime(2026, 11, 2, 8, 0)      # Monday morning
MONDAY = "2026-11-02"
TEST_CONFIG = {"TESTING": True, "DB_NAME": "ClinicAppointmentDB_Test"}
ADMIN = ("admin", "Admin123!")


def next_weekday():
    d = date.today() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()

RECEPTION = ("reception", "Reception123!")


class SchedulingRulesTest(unittest.TestCase):
    """Pure business rules - no database needed."""

    def test_day_slots(self):
        self.assertEqual(day_slots(9, 11), ["09:00", "09:30", "10:00", "10:30"])

    def test_valid_request(self):
        self.assertEqual(validate_request(MONDAY, "10:00", 9, 17, NOW), [])

    def test_past_time_rejected(self):
        self.assertTrue(validate_request("2026-10-30", "10:00", 9, 17, NOW))

    def test_weekend_rejected(self):
        self.assertIn("The clinic is closed on weekends.",
                      validate_request("2026-11-07", "10:00", 9, 17, NOW))

    def test_outside_working_hours_rejected(self):
        self.assertTrue(validate_request(MONDAY, "17:00", 9, 17, NOW))
        self.assertTrue(validate_request(MONDAY, "10:15", 9, 17, NOW))

    def test_bad_date_format(self):
        self.assertTrue(validate_request("02/11/2026", "10:00", 9, 17, NOW))

    def test_free_slots(self):
        self.assertEqual(free_slots(9, 10, ["09:00"]), ["09:30"])

    def test_utilization(self):
        self.assertEqual(utilization(8, 9, 17, 1), 0.5)
        self.assertEqual(utilization(0, 9, 9, 5), 0.0)

    def test_national_id(self):
        self.assertTrue(is_valid_national_id("10000000146"))
        self.assertFalse(is_valid_national_id("10000000147"))
        self.assertFalse(is_valid_national_id("01234567890"))


class DatabaseTestCase(unittest.TestCase):
    """Creates a fresh test database with sample data for every test."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TEST_CONFIG)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            drop_database()

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        init_db()
        seed_db()

    def tearDown(self):
        close_db()
        self.ctx.pop()

    def client_as(self, user=ADMIN):
        client = self.app.test_client()
        res = client.post("/login", data={"username": user[0], "password": user[1]})
        self.assertEqual(res.status_code, 302, "login failed")
        return client


class BookingTest(DatabaseTestCase):
    def test_book_ok(self):
        new_id, errors = book(1, 1, MONDAY, "09:00", reason_id=4, notes="Check-up", now=NOW)
        self.assertEqual(errors, [])
        self.assertIsNotNone(new_id)

    def test_doctor_double_booking_rejected(self):
        book(1, 1, MONDAY, "09:00", now=NOW)
        _, errors = book(2, 1, MONDAY, "09:00", now=NOW)
        self.assertEqual(errors, ["The doctor is not free at this time."])

    def test_patient_double_booking_rejected(self):
        book(1, 1, MONDAY, "10:00", now=NOW)
        _, errors = book(1, 2, MONDAY, "10:00", now=NOW)
        self.assertEqual(errors, ["The patient already has an appointment at this time."])

    def test_cancelled_slot_can_be_booked_again(self):
        aid, _ = book(1, 1, MONDAY, "11:00", now=NOW)
        execute("UPDATE appointments SET status='CANCELLED' WHERE id=?", (aid,))
        _, errors = book(2, 1, MONDAY, "11:00", now=NOW)
        self.assertEqual(errors, [])

    def test_unique_index_protects_database(self):
        book(1, 1, MONDAY, "12:00", now=NOW)
        with self.assertRaises(IntegrityError):
            execute("INSERT INTO appointments (patient_id, doctor_id, appt_date, appt_time)"
                    " VALUES (2, 1, ?, '12:00')", (MONDAY,))

    def test_foreign_key_enforced(self):
        with self.assertRaises(IntegrityError):
            execute("INSERT INTO appointments (patient_id, doctor_id, appt_date, appt_time)"
                    " VALUES (999, 1, ?, '13:00')", (MONDAY,))

    def test_reason_of_other_department_rejected(self):
        # reason 6 = Skin rash (Dermatology); doctor 1 = Cardiology
        _, errors = book(1, 1, MONDAY, "14:00", reason_id=6, now=NOW)
        self.assertEqual(errors, ["This appointment reason is not valid for the selected doctor."])

    def test_general_reason_allowed_for_any_doctor(self):
        _, errors = book(1, 2, MONDAY, "14:00", reason_id=1, now=NOW)
        self.assertEqual(errors, [])


class AuthTest(DatabaseTestCase):
    def test_pages_need_login(self):
        res = self.app.test_client().get("/appointments/")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

    def test_wrong_password(self):
        res = self.app.test_client().post("/login", data={"username": "admin", "password": "nope"})
        self.assertIn(b"Wrong username or password", res.data)

    def test_passwords_are_hashed(self):
        stored = scalar("SELECT password_hash FROM users WHERE username = 'admin'")
        self.assertNotIn("Admin123!", stored)
        self.assertTrue(stored.startswith("scrypt:"))

    def test_receptionist_cannot_open_admin_pages(self):
        client = self.client_as(RECEPTION)
        for url in ["/users/", "/departments/", "/reasons/", "/doctors/new"]:
            self.assertEqual(client.get(url).status_code, 403, url)

    def test_inactive_user_cannot_login(self):
        execute("UPDATE users SET is_active = 0 WHERE username = 'reception'")
        res = self.app.test_client().post("/login", data={"username": "reception", "password": "Reception123!"})
        self.assertEqual(res.status_code, 200)

    def test_admin_creates_user_with_weak_password_rejected(self):
        client = self.client_as()
        res = client.post("/users/new", data={"username": "x", "full_name": "X", "role": "RECEPTIONIST",
                                              "password": "short"}, follow_redirects=True)
        self.assertIn(b"at least 8 characters", res.data)

    def test_logout(self):
        client = self.client_as()
        client.post("/logout")
        self.assertEqual(client.get("/patients/").status_code, 302)


class MasterDataTest(DatabaseTestCase):
    def test_create_department_and_reason(self):
        client = self.client_as()
        client.post("/departments/new", data={"name": "Neurology", "description": "Brain", "is_active": "1"})
        dep = query_one("SELECT id FROM departments WHERE name = 'Neurology'")
        self.assertIsNotNone(dep)
        client.post("/reasons/new", data={"name": "Headache", "department_id": dep["id"], "is_active": "1"})
        self.assertIsNotNone(query_one("SELECT id FROM appointment_reasons WHERE name = 'Headache'"))

    def test_duplicate_department_rejected(self):
        res = self.client_as().post("/departments/new", data={"name": "Cardiology", "is_active": "1"},
                                    follow_redirects=True)
        self.assertIn(b"already exists", res.data)

    def test_reasons_for_doctor_api(self):
        names = [r["name"] for r in self.client_as(RECEPTION).get("/reasons/for-doctor?doctor_id=1").get_json()]
        self.assertIn("Chest pain", names)
        self.assertIn("General check-up", names)
        self.assertNotIn("Skin rash", names)


class WebPagesTest(DatabaseTestCase):
    def test_pages_load(self):
        client = self.client_as()
        for url in ["/reports/", "/reports/analytics", "/patients/", "/doctors/", "/appointments/",
                    "/appointments/new", "/patients/new", "/doctors/new", "/patients/1/edit",
                    "/departments/", "/departments/new", "/reasons/", "/reasons/new", "/users/",
                    "/users/new", "/account/password"]:
            self.assertEqual(client.get(url).status_code, 200, url)

    def test_add_patient_with_bad_id(self):
        res = self.client_as(RECEPTION).post("/patients/new", data={
            "national_id": "12345678901", "full_name": "Test", "birth_date": "2000-01-01"},
            follow_redirects=True)
        self.assertIn(b"National ID is not valid", res.data)

    def test_add_patient_ok(self):
        res = self.client_as(RECEPTION).post("/patients/new", data={
            "national_id": "12345678950", "full_name": "New Patient", "birth_date": "2000-01-01"},
            follow_redirects=True)
        self.assertIn(b"Patient saved.", res.data)
        self.assertIn(b"New Patient", res.data)

    def test_booking_records_user(self):
        client = self.client_as(RECEPTION)
        client.post("/appointments/new", data={"patient_id": 1, "doctor_id": 3, "appt_date": next_weekday(),
                                               "appt_time": "09:00", "reason_id": 1})
        row = query_one("SELECT u.username FROM appointments a JOIN users u ON u.id = a.created_by")
        self.assertEqual(row["username"], "reception")

    def test_slots_api(self):
        res = self.client_as().get("/appointments/slots?doctor_id=3&date=2030-01-07")
        self.assertEqual(res.get_json()[:2], ["09:00", "09:30"])


class ReportsTest(DatabaseTestCase):
    def test_report_counts_and_csv(self):
        book(1, 1, MONDAY, "09:00", reason_id=4, now=NOW)
        aid, _ = book(2, 1, MONDAY, "09:30", reason_id=4, now=NOW)
        execute("UPDATE appointments SET status = 'CANCELLED' WHERE id = ?", (aid,))
        client = self.client_as()
        page = client.get(f"/reports/analytics?from={MONDAY}&to={MONDAY}")
        self.assertIn(b"Chest pain", page.data)
        self.assertIn(b"50.0%", page.data)      # 1 of 2 cancelled
        csv = client.get(f"/reports/export.csv?from={MONDAY}&to={MONDAY}")
        self.assertEqual(csv.mimetype, "text/csv")
        self.assertEqual(csv.get_data(as_text=True).count("\n"), 3)  # header + 2 rows


if __name__ == "__main__":
    unittest.main()
