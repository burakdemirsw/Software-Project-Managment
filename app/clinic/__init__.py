"""Clinic Appointment System - Flask application factory."""
import os
from datetime import timedelta

from flask import Flask, redirect, render_template, url_for


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CLINIC_SECRET_KEY", "dev-only-secret-change-me"),
        DB_SERVER=os.environ.get("CLINIC_DB_SERVER", r"(localdb)\MSSQLLocalDB"),
        DB_NAME=os.environ.get("CLINIC_DB_NAME", "ClinicAppointmentDB"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )
    if test_config:
        app.config.update(test_config)

    from . import db
    db.init_app(app)

    from . import auth
    app.before_request(auth.load_user)
    app.before_request(auth.require_login)

    from .appointments import bp as appointments_bp
    from .departments import bp as departments_bp
    from .doctors import bp as doctors_bp
    from .patients import bp as patients_bp
    from .reasons import bp as reasons_bp
    from .reports import bp as reports_bp
    for blueprint in (auth.bp, patients_bp, doctors_bp, departments_bp, reasons_bp,
                      appointments_bp, reports_bp):
        app.register_blueprint(blueprint)

    @app.route("/")
    def index():
        return redirect(url_for("reports.dashboard"))

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403,
                               message="You do not have permission to open this page."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="Page not found."), 404

    return app
