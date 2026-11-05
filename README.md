# Clinic Appointment System (CAS)

SEN4100 Software Project Management team project, Haliç University.

| Name | Student No | Role |
|---|---|---|
| Burak Demir | 20091000008 | Project Manager, backend |
| Davut Ayfer | 20091000054 | Database, doctor module |
| Enes Küçükkaya | 22091000275 | UI, patient module, dashboard |
| Alper Keskin | 24352525053 | Testing, documentation |

A web application for a small clinic: patients, doctors, and appointment booking
in 30-minute slots with **no double booking**. Built with **Python + Flask** and
**Microsoft SQL Server (LocalDB)**.

## Folder structure

```
app/                  Source code
  clinic/             Flask application (modules, templates, CSS)
  database/           SQL Server scripts (create_database.sql, schema.sql, seed.sql)
  tests/              19 automated tests (unittest)
docs/
  M1_Milestone1/      Concept & stakeholders, charter, scope        (Week 4)
  M2_Milestone2/      WBS, CPM/PERT, Gantt & estimation, risks      (Week 7)
  (M3_Milestone3/     SCM audit, EVM, final IEEE document, retro    (Week 13) - later)
  figures/            Charts and screenshots (+ results.md with all calculations)
  Word/               The same documents as .docx (with cover page)
tools/
  pm_calculations.py  PERT, CPM, Function Points, COCOMO, risk matrix (+ EVM with --evm) -> figures
  build_docx.py       Markdown -> Word converter
```

## How to run

Requirements: Python 3.10+, SQL Server LocalDB (comes with Visual Studio / SSMS),
"ODBC Driver 17 (or 18) for SQL Server".

```bash
cd app
pip install -r requirements.txt
flask --app clinic init-db --seed     # creates database ClinicAppointmentDB on (localdb)\MSSQLLocalDB
flask --app clinic run                # open http://127.0.0.1:5000
```

Open the database in SSMS with server name `(localdb)\MSSQLLocalDB` (Windows Authentication).
Another server: set `CLINIC_DB_SERVER` and `CLINIC_DB_NAME` environment variables.

## Tests

```bash
cd app
python -m unittest discover -s tests -v
```

The database tests create and delete a separate database `ClinicAppointmentDB_Test`.

## Re-create the PM figures and Word files

```bash
pip install matplotlib python-docx
python tools/pm_calculations.py
python tools/build_docx.py
```
