-- Sample data for a demo (national IDs are fake but pass the checksum rule)

INSERT INTO dbo.departments (name) VALUES
    (N'Cardiology'), (N'Dermatology'), (N'Internal Medicine'), (N'Pediatrics');

INSERT INTO dbo.doctors (full_name, department_id, phone, email, start_hour, end_hour) VALUES
    (N'Dr. Ayse Yilmaz', 1, '0212 000 0001', 'ayse.yilmaz@clinic.local', 9, 17),
    (N'Dr. Mehmet Kaya', 2, '0212 000 0002', 'mehmet.kaya@clinic.local', 10, 16),
    (N'Dr. Elif Demir',  3, '0212 000 0003', 'elif.demir@clinic.local', 9, 13),
    (N'Dr. Can Arslan',  4, '0212 000 0004', 'can.arslan@clinic.local', 13, 18);

INSERT INTO dbo.patients (national_id, full_name, birth_date, phone, email) VALUES
    ('10000000146', N'Zeynep Sahin', '1990-04-12', '0555 111 2233', 'zeynep@example.com'),
    ('10000000214', N'Ali Celik',    '1985-11-03', '0555 222 3344', 'ali@example.com'),
    ('10000000382', N'Fatma Ozturk', '2012-06-25', '0555 333 4455', NULL);
GO
