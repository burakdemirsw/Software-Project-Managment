-- Run this once in SSMS (connected to (localdb)\MSSQLLocalDB) if you want to
-- create the database by hand. "flask --app clinic init-db" does the same automatically.

IF DB_ID('ClinicAppointmentDB') IS NULL
    CREATE DATABASE ClinicAppointmentDB;
GO
USE ClinicAppointmentDB;
GO
-- Next: run schema.sql, then seed.sql (optional sample data).
