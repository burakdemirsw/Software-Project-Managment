"""Database connection layer (Microsoft SQL Server via pyodbc).

Default target: (localdb)\\MSSQLLocalDB, database "ClinicAppointmentDB".
Change it with the environment variables CLINIC_DB_SERVER and CLINIC_DB_NAME.

Every request opens one connection (stored in flask.g) and closes it at the
end of the request. Rows are returned as Python dicts.
"""
import re
from pathlib import Path

import click
import pyodbc
from flask import current_app, g

DB_DIR = Path(__file__).resolve().parent.parent / "database"
IntegrityError = pyodbc.IntegrityError


def _driver():
    installed = pyodbc.drivers()
    for name in ("ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server", "SQL Server"):
        if name in installed:
            return name
    raise RuntimeError("No SQL Server ODBC driver found. Install 'ODBC Driver 17 for SQL Server'.")


def connection_string(server, database):
    driver = _driver()
    extra = "Encrypt=no;" if driver.endswith("18 for SQL Server") else ""
    return (f"Driver={{{driver}}};Server={server};Database={database};"
            f"Trusted_Connection=yes;{extra}")


def _connect(database=None):
    cfg = current_app.config
    return pyodbc.connect(connection_string(cfg["DB_SERVER"], database or cfg["DB_NAME"]),
                          autocommit=database == "master")


def get_db():
    """Return the connection for the current request (open it if needed)."""
    if "db" not in g:
        g.db = _connect()
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ------------------------------------------------------------------ helpers
def query_all(sql, params=()):
    cur = get_db().cursor().execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def query_one(sql, params=()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def scalar(sql, params=()):
    return get_db().cursor().execute(sql, params).fetchone()[0]


def execute(sql, params=()):
    """Run INSERT/UPDATE/DELETE and commit. Returns the number of changed rows."""
    db = get_db()
    try:
        count = db.cursor().execute(sql, params).rowcount
        db.commit()
        return count
    except pyodbc.Error:
        db.rollback()
        raise


def insert(sql, params=()):
    """Run an INSERT that has 'OUTPUT INSERTED.id'. Returns the new id."""
    db = get_db()
    try:
        new_id = db.cursor().execute(sql, params).fetchone()[0]
        db.commit()
        return new_id
    except pyodbc.Error:
        db.rollback()
        raise


# ------------------------------------------------------------------ setup
def run_script(path):
    """Run a .sql file that uses GO as batch separator."""
    db = get_db()
    text = Path(path).read_text(encoding="utf-8")
    for batch in re.split(r"^\s*GO\s*$", text, flags=re.MULTILINE | re.IGNORECASE):
        if batch.strip():
            db.cursor().execute(batch)
    db.commit()


def _db_name():
    name = current_app.config["DB_NAME"]
    if not re.fullmatch(r"\w+", name):
        raise ValueError("Invalid database name")
    return name


def create_database():
    """Create the database on the server if it does not exist."""
    name = _db_name()
    master = _connect("master")
    master.cursor().execute(f"IF DB_ID('{name}') IS NULL CREATE DATABASE [{name}]")
    master.close()


def drop_database():
    """Delete the database (used by the automated tests)."""
    close_db()
    name = _db_name()
    master = _connect("master")
    master.cursor().execute(
        f"IF DB_ID('{name}') IS NOT NULL BEGIN "
        f"ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
        f"DROP DATABASE [{name}]; END")
    master.close()


def init_db():
    """Create the database and all tables (old data is deleted)."""
    close_db()
    create_database()
    run_script(DB_DIR / "schema.sql")


def seed_db():
    run_script(DB_DIR / "seed.sql")


@click.command("init-db")
@click.option("--seed", is_flag=True, help="Also insert sample data.")
def init_db_command(seed):
    """Create the database tables."""
    init_db()
    cfg = current_app.config
    click.echo(f"Database '{cfg['DB_NAME']}' created on {cfg['DB_SERVER']}.")
    if seed:
        seed_db()
        click.echo("Sample data inserted.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
