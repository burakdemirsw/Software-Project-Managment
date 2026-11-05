"""Unit and integration tests.

Run from the app folder:   python -m unittest discover -s tests -v

The database tests create a separate SQL Server database
(ClinicAppointmentDB_Test on (localdb)\\MSSQLLocalDB) and delete it at the end.
"""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clinic import create_app  # noqa: E402
from clinic.appointments import book  # noqa: E402
from clinic.db import (IntegrityError, close_db, drop_database, execute,  # noqa: E402
                       init_db, seed_db)
from clinic.scheduling import (day_slots, free_slots, is_valid_national_id,  # noqa: E402
                               utilization, validate_request)

NOW = datetime(2026, 11, 2, 8, 0)      # Monday morning
MONDAY = "2026-11-02"
TEST_CONFIG = {"TESTING": True, "DB_NAME": "ClinicAppointmentDB_Test"}


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


class BookingTest(DatabaseTestCase):
    def test_book_ok(self):
        new_id, errors = book(1, 1, MONDAY, "09:00", "Check-up", NOW)
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


class WebPagesTest(DatabaseTestCase):
    def test_pages_load(self):
        client = self.app.test_client()
        for url in ["/reports/", "/patients/", "/doctors/", "/appointments/",
                    "/appointments/new", "/patients/new", "/doctors/new", "/patients/1/edit"]:
            self.assertEqual(client.get(url).status_code, 200, url)

    def test_add_patient_with_bad_id(self):
        res = self.app.test_client().post("/patients/new", data={
            "national_id": "12345678901", "full_name": "Test", "birth_date": "2000-01-01"},
            follow_redirects=True)
        self.assertIn(b"National ID is not valid", res.data)

    def test_add_patient_ok(self):
        res = self.app.test_client().post("/patients/new", data={
            "national_id": "12345678950", "full_name": "New Patient", "birth_date": "2000-01-01"},
            follow_redirects=True)
        self.assertIn(b"Patient saved.", res.data)
        self.assertIn(b"New Patient", res.data)

    def test_slots_api(self):
        res = self.app.test_client().get("/appointments/slots?doctor_id=3&date=2030-01-07")
        self.assertEqual(res.get_json()[:2], ["09:00", "09:30"])


if __name__ == "__main__":
    unittest.main()
