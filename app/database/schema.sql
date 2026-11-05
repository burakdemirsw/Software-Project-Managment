-- =============================================================
-- Clinic Appointment System - database schema (Microsoft SQL Server)
-- Target: (localdb)\MSSQLLocalDB, database ClinicAppointmentDB
-- Run by:  flask --app clinic init-db   (or open in SSMS and execute)
-- =============================================================

IF OBJECT_ID('dbo.appointments', 'U') IS NOT NULL DROP TABLE dbo.appointments;
IF OBJECT_ID('dbo.patients', 'U')     IS NOT NULL DROP TABLE dbo.patients;
IF OBJECT_ID('dbo.doctors', 'U')      IS NOT NULL DROP TABLE dbo.doctors;
IF OBJECT_ID('dbo.departments', 'U')  IS NOT NULL DROP TABLE dbo.departments;
GO

CREATE TABLE dbo.departments (
    id    INT IDENTITY(1,1) PRIMARY KEY,
    name  NVARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE dbo.doctors (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    full_name      NVARCHAR(100) NOT NULL,
    department_id  INT NOT NULL REFERENCES dbo.departments(id),
    phone          NVARCHAR(20)  NULL,
    email          NVARCHAR(100) NULL,
    start_hour     INT NOT NULL DEFAULT 9  CHECK (start_hour BETWEEN 0 AND 23),
    end_hour       INT NOT NULL DEFAULT 17 CHECK (end_hour BETWEEN 1 AND 24),
    CONSTRAINT ck_doctor_hours CHECK (end_hour > start_hour)
);

CREATE TABLE dbo.patients (
    id           INT IDENTITY(1,1) PRIMARY KEY,
    national_id  CHAR(11)      NOT NULL UNIQUE CHECK (LEN(national_id) = 11),
    full_name    NVARCHAR(100) NOT NULL,
    birth_date   DATE          NOT NULL,
    phone        NVARCHAR(20)  NULL,
    email        NVARCHAR(100) NULL,
    created_at   DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);

CREATE TABLE dbo.appointments (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    patient_id  INT           NOT NULL REFERENCES dbo.patients(id),
    doctor_id   INT           NOT NULL REFERENCES dbo.doctors(id),
    appt_date   DATE          NOT NULL,
    appt_time   CHAR(5)       NOT NULL,          -- HH:MM (30-minute slots)
    reason      NVARCHAR(200) NULL,
    status      VARCHAR(10)   NOT NULL DEFAULT 'BOOKED'
                CHECK (status IN ('BOOKED', 'COMPLETED', 'CANCELLED')),
    created_at  DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);
GO

CREATE INDEX ix_appointments_date ON dbo.appointments (appt_date);
GO
