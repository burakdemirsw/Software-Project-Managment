-- =============================================================
-- Clinic Appointment System - database schema (Microsoft SQL Server)
-- Target: (localdb)\MSSQLLocalDB, database ClinicAppointmentDB
-- Run by:  flask --app clinic init-db   (or open in SSMS and execute)
-- WARNING: drops and re-creates all tables (all data is deleted).
-- =============================================================

IF OBJECT_ID('dbo.appointments', 'U')        IS NOT NULL DROP TABLE dbo.appointments;
IF OBJECT_ID('dbo.appointment_reasons', 'U') IS NOT NULL DROP TABLE dbo.appointment_reasons;
IF OBJECT_ID('dbo.patients', 'U')            IS NOT NULL DROP TABLE dbo.patients;
IF OBJECT_ID('dbo.doctors', 'U')             IS NOT NULL DROP TABLE dbo.doctors;
IF OBJECT_ID('dbo.departments', 'U')         IS NOT NULL DROP TABLE dbo.departments;
IF OBJECT_ID('dbo.users', 'U')               IS NOT NULL DROP TABLE dbo.users;
GO

-- Application users (login). Passwords are stored only as salted hashes (werkzeug scrypt).
CREATE TABLE dbo.users (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    username       NVARCHAR(50)  NOT NULL UNIQUE,
    full_name      NVARCHAR(100) NOT NULL,
    password_hash  NVARCHAR(255) NOT NULL,
    role           VARCHAR(20)   NOT NULL DEFAULT 'RECEPTIONIST'
                   CHECK (role IN ('ADMIN', 'RECEPTIONIST')),
    is_active      BIT           NOT NULL DEFAULT 1,
    created_at     DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    last_login_at  DATETIME2     NULL
);

CREATE TABLE dbo.departments (
    id           INT IDENTITY(1,1) PRIMARY KEY,
    name         NVARCHAR(100) NOT NULL UNIQUE,
    description  NVARCHAR(200) NULL,
    is_active    BIT           NOT NULL DEFAULT 1
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

-- Standard reasons for a visit (e.g. "Check-up"). A reason can belong to one department
-- or be general (department_id NULL).
CREATE TABLE dbo.appointment_reasons (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    name           NVARCHAR(100) NOT NULL UNIQUE,
    department_id  INT           NULL REFERENCES dbo.departments(id),
    description    NVARCHAR(200) NULL,
    is_active      BIT           NOT NULL DEFAULT 1
);

CREATE TABLE dbo.appointments (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    patient_id  INT           NOT NULL REFERENCES dbo.patients(id),
    doctor_id   INT           NOT NULL REFERENCES dbo.doctors(id),
    appt_date   DATE          NOT NULL,
    appt_time   CHAR(5)       NOT NULL,          -- HH:MM (30-minute slots)
    reason_id   INT           NULL REFERENCES dbo.appointment_reasons(id),
    notes       NVARCHAR(200) NULL,              -- free text from the receptionist
    status      VARCHAR(10)   NOT NULL DEFAULT 'BOOKED'
                CHECK (status IN ('BOOKED', 'COMPLETED', 'CANCELLED')),
    created_by  INT           NULL REFERENCES dbo.users(id),
    created_at  DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);
GO

-- A doctor cannot have two active appointments in the same slot (filtered unique index).
CREATE UNIQUE INDEX ux_doctor_slot
    ON dbo.appointments (doctor_id, appt_date, appt_time)
    WHERE status IN ('BOOKED', 'COMPLETED');

-- A patient cannot have two active appointments in the same slot.
CREATE UNIQUE INDEX ux_patient_slot
    ON dbo.appointments (patient_id, appt_date, appt_time)
    WHERE status IN ('BOOKED', 'COMPLETED');

CREATE INDEX ix_appointments_date ON dbo.appointments (appt_date);
CREATE INDEX ix_appointments_reason ON dbo.appointments (reason_id);
GO
