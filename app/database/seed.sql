-- Sample data for a demo. National IDs are fake but pass the checksum rule.
-- Demo users (CHANGE THESE PASSWORDS for any real use):
--   admin     / Admin123!       (ADMIN: manages users, departments, reasons, doctors)
--   reception / Reception123!   (RECEPTIONIST: patients and appointments)

INSERT INTO dbo.users (username, full_name, password_hash, role) VALUES
    ('admin', N'System Administrator',
     'scrypt:32768:8:1$esnr2VV44WE3KN8A$64e5e9b006c4a087885f1e71c9959c0b5797c4e642834cd1f58968087497047079ff0a9be0c86d5e05820669475a807de78d9b9e3eaf624a1cccbd37ea6d0c12',
     'ADMIN'),
    ('reception', N'Front Desk',
     'scrypt:32768:8:1$8UutICQI3mrbs37F$97c69e50e650ca6a751282ec7330005b596cdd5593d98a17e6980462f6d7e2902b8e2b8a52b172c69857a0bd86adc231113ea6710ec756ea2dfe755d06369215',
     'RECEPTIONIST');

INSERT INTO dbo.departments (name, description) VALUES
    (N'Cardiology', N'Heart and blood vessel diseases'),
    (N'Dermatology', N'Skin, hair and nail diseases'),
    (N'Internal Medicine', N'General adult medicine'),
    (N'Pediatrics', N'Children and adolescents');

INSERT INTO dbo.doctors (full_name, department_id, phone, email, start_hour, end_hour) VALUES
    (N'Dr. Ayse Yilmaz', 1, '0212 000 0001', 'ayse.yilmaz@clinic.local', 9, 17),
    (N'Dr. Mehmet Kaya', 2, '0212 000 0002', 'mehmet.kaya@clinic.local', 10, 16),
    (N'Dr. Elif Demir',  3, '0212 000 0003', 'elif.demir@clinic.local', 9, 13),
    (N'Dr. Can Arslan',  4, '0212 000 0004', 'can.arslan@clinic.local', 13, 18);

INSERT INTO dbo.appointment_reasons (name, department_id, description) VALUES
    (N'General check-up', NULL, N'Routine examination'),
    (N'Follow-up visit', NULL, N'Control after a previous visit'),
    (N'Test results', NULL, N'Discuss laboratory or imaging results'),
    (N'Chest pain', 1, N'Cardiology complaint'),
    (N'High blood pressure', 1, N'Hypertension control'),
    (N'Skin rash', 2, N'Dermatology complaint'),
    (N'Vaccination', 4, N'Child vaccination');

INSERT INTO dbo.patients (national_id, full_name, birth_date, phone, email) VALUES
    ('10000000146', N'Zeynep Sahin', '1990-04-12', '0555 111 2233', 'zeynep@example.com'),
    ('10000000214', N'Ali Celik',    '1985-11-03', '0555 222 3344', 'ali@example.com'),
    ('10000000382', N'Fatma Ozturk', '2012-06-25', '0555 333 4455', NULL);
GO
