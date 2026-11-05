"""Clinic Appointment System - Flask application factory."""
import os

from flask import Flask, redirect, url_for


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CLINIC_SECRET_KEY", "dev-only-secret"),
        DB_SERVER=os.environ.get("CLINIC_DB_SERVER", r"(localdb)\MSSQLLocalDB"),
        DB_NAME=os.environ.get("CLINIC_DB_NAME", "ClinicAppointmentDB"),
    )
    if test_config:
        app.config.update(test_config)

    from . import db
    db.init_app(app)

    from .patients import bp as patients_bp
    app.register_blueprint(patients_bp)

    return app
