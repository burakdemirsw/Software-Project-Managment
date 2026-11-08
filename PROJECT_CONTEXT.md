# PROJECT CONTEXT: read this first

> **For AI assistants (ChatGPT, Copilot, Claude, Cursor, etc.) and team members.**
> This file explains what was built, why, and how everything is connected.
> Read it before you change code or documents, so the work stays consistent.
> Last update: 5 November 2026 (course Week 6).

## Türkçe kısa özet

Bu klasör, Haliç Üniversitesi **SEN4100 Yazılım Proje Yönetimi** dersinin 4 kişilik dönem projesidir:
**Klinik Randevu Sistemi** (Python + Flask + SQL Server LocalDB). Kod çalışıyor, 19 otomatik test geçiyor.
**Milestone 1** ve **Milestone 2** belgeleri hazır (Markdown + Word). **Milestone 3 henüz başlamadı**
(Hafta 13'te teslim). Tüm sayısal değerler (PERT, CPM, COCOMO, risk) `tools/pm_calculations.py`
tarafından hesaplanır. Belgeleri değiştirince Word dosyalarını `tools/build_docx.py` ile yeniden üretin.
Belgeler basit İngilizce ile yazılır.

---

## 1. Course and team

| Item | Value |
|---|---|
| University | Haliç University, Faculty of Engineering, Department of Software Engineering |
| Course | SEN4100 Software Project Management |
| Instructor | Asst. Prof. M. Fatih Mintaş |
| Project | Clinic Appointment System (CAS) |
| Repository | https://github.com/burakdemirsw/Software-Project-Managment |

| Member | Student No | Role |
|---|---|---|
| Burak Demir | 20091000008 | Project Manager, backend (appointment module) |
| Davut Ayfer | 20091000054 | Database designer, doctor module |
| Enes Küçükkaya | 22091000275 | UI design, patient module, dashboard |
| Alper Keskin | 24352525053 | Testing / quality, documentation |

Milestones required by the course (syllabus, Week 1 notes section 6):

| Milestone | Due | Content | Status |
|---|---|---|---|
| M1 (5%) | Week 4 (23 Oct 2026) | Concept proposal & stakeholder analysis, project charter, scope & assumptions/constraints | **Done** |
| M2 (5%) | Week 7 (13 Nov 2026) | WBS + dictionary, CPM/PERT network & critical path, baseline Gantt & algorithmic effort estimation, risk register (qualitative matrix) | **Done** |
| M3 (10%) | Week 13 (25 Dec 2026) | SCM audit (Git branch tree), EVM report, final IEEE documentation, oral defense & retrospective | **Not started (on purpose)** |

The instructor's lecture notes (`Week 1..6 Lecture Notes*.docx`) are in the project folder on Burak's
computer, but they are **git-ignored** (instructor material). The documents follow what those notes ask
for (for example TELOS feasibility, NPV/ROI, Mendelow grid, 100% rule, 8/80 rule, Function Points,
COCOMO, RE = P x I, Mitigate/Avoid/Transfer/Accept).

## 2. The product

A web application for a small clinic: patients, doctors (with departments and working hours) and
appointment booking.

Business rules (in `app/clinic/scheduling.py` and `app/clinic/appointments.py`):

- Appointments use **30-minute slots** inside the doctor's working hours (`start_hour`..`end_hour`).
- Only **free slots** are offered (`/appointments/slots` JSON API used by the booking form).
- **No double booking** for a doctor or a patient. This is checked in the code **and** enforced by two
  **filtered UNIQUE indexes** in SQL Server (`WHERE status IN ('BOOKED','COMPLETED')`), so a cancelled
  slot can be booked again.
- No booking in the past, on weekends, or more than 90 days ahead.
- Turkish national ID (TC Kimlik No) is validated with its checksum algorithm.
- Status: `BOOKED` -> `COMPLETED` or `CANCELLED` (only BOOKED can change).
- Dashboard: patient count, appointments today, cancellation rate, doctor utilization
  (= booked slots / available slots this week).

Not in scope (see M1 scope statement): login/roles, online self-booking, SMS/e-mail, payments, medical
records, mobile app, cloud hosting.

## 3. Technology and how to run

| Part | Choice |
|---|---|
| Language / web | Python 3 (tested on 3.14) + Flask 3 (Jinja2 templates, blueprints) |
| Database | Microsoft SQL Server **LocalDB** `(localdb)\MSSQLLocalDB`, database `ClinicAppointmentDB` |
| DB driver | `pyodbc` with "ODBC Driver 17 for SQL Server" (falls back to 18 / "SQL Server") |
| Tests | Python `unittest`, 19 tests |
| Editor | VS Code (`.vscode/launch.json`, `tasks.json`, `settings.json` are included) |

History of the stack decision: first SQLite was used, then Burak asked for SQL Server LocalDB on his
computer. Burak briefly asked for C#, then decided to stay with Python because Python can use SQL
Server. **Do not switch the stack without asking the team.**

Run (from the `app` folder):

```bash
pip install -r requirements.txt
flask --app clinic init-db --seed     # creates ClinicAppointmentDB + tables + sample data (deletes old data!)
flask --app clinic run                # http://127.0.0.1:5000
python -m unittest discover -s tests -v
```

In VS Code: Run and Debug -> "Run Clinic web app (Flask)", "Create database (init-db --seed)",
"Run tests". In SSMS: server `(localdb)\MSSQLLocalDB`, Windows Authentication.

Configuration (environment variables, see `app/clinic/__init__.py`): `CLINIC_DB_SERVER`,
`CLINIC_DB_NAME`, `CLINIC_SECRET_KEY`.

Tests create and **drop** a separate database `ClinicAppointmentDB_Test`. They never touch
`ClinicAppointmentDB`.

## 4. Code map

```
app/
  clinic/__init__.py      create_app(): config, registers blueprints, "/" -> dashboard
  clinic/db.py            pyodbc connection per request; helpers query_all / query_one / scalar /
                          execute / insert (INSERT ... OUTPUT INSERTED.id); init-db CLI; runs .sql
                          files split on GO; create_database / drop_database
  clinic/scheduling.py    pure rules (no Flask, no DB): day_slots, validate_request, free_slots,
                          utilization, is_valid_national_id
  clinic/patients.py      /patients  list, search, new, edit, delete (blocked if it has appointments)
  clinic/doctors.py       /doctors   list, new, edit (working hours)
  clinic/appointments.py  /appointments  book(), list + filter, new, slots API, cancel, complete
  clinic/reports.py       /reports   dashboard
  clinic/templates/       base.html + one folder per module; static/style.css
  database/               create_database.sql, schema.sql (tables, constraints, indexes), seed.sql
  tests/test_clinic.py    SchedulingRulesTest (9), BookingTest (6), WebPagesTest (4)
```

Database tables: `departments`, `doctors`, `patients`, `appointments` (see `app/database/schema.sql`).
Rows are returned as Python dicts. SQL uses `?` parameters (no string formatting with user input).

## 5. Project management numbers (single source of truth)

**All numbers in the documents come from `tools/pm_calculations.py`.** It writes
`docs/figures/results.md` (all tables) and the charts in `docs/figures/`.
If a number must change, change the input data in that script, run it again, then update the
Markdown documents and rebuild the Word files. **Never type a new number only into a document.**

Key values (current baseline):

| Topic | Value |
|---|---|
| Project start | Monday 28 Sep 2026 = Week 1 (so 5 Nov 2026 is Week 6) |
| Lifecycle model | Hybrid "Water-Scrum-Fall": predictive planning + 3 two-week sprints |
| CPM activities | A..L, all Finish-to-Start (A initiation ... L retrospective & presentation) |
| Critical path | A -> B -> D -> F -> H -> J -> K -> L |
| Expected duration (PERT) | 55.17 working days; deadline 60 working days (18 Dec 2026, end of Week 12) |
| P(finish on time) | Z = 1.67 -> 95.3% |
| WBS | 22 work packages, 560 person-hours (100% rule), all within 8/80 rule |
| Function Points | UFP 89, TDI 35, VAF 1.00, FP 89; 20 LOC/FP -> 1.78 KLOC |
| Basic COCOMO (organic) | 4.40 PM = 668 person-hours, 4.39 months |
| Intermediate COCOMO | EAF 0.618 -> 3.62 PM = 551 person-hours |
| Team capacity | 4 x 12 weeks x ~12 h = 576 person-hours |
| Budget | 560 h x 150 TL = BAC 84,000 TL (notional), reserve 10% (56 h) |
| Business case | NPV +30,343 TL (3 years, r = 10%), ROI 59.6%, payback 1.88 years |
| Risks | 11 risks, RE = P x I, P in {0.1, 0.3, 0.5, 0.7, 0.9}, I in 1..5; Red >= 2.0, Yellow 1.0-1.9, Green < 1.0 |
| Measured code size | 920 non-blank lines (Python 468, HTML 226, CSS 40, SQL 76, tests 110) |

Values that were **assumed** while writing (the team should confirm or change them): KPI targets
SPI/CPI >= 0.90, effort ceiling 616 h, PM can approve changes up to 8 person-hours alone, project
code "SEN4100-CAS", sprint demos at the end of Weeks 6, 8 and 10, risk owners and responses,
NPV/ROI cash-flow assumptions (benefit 60,000 TL/year, maintenance 10,000 TL/year).

## 6. Documents

```
docs/
  M1_Milestone1/   1.1 Concept proposal & stakeholder analysis, 1.2 Project charter,
                   1.3 Scope statement, assumptions & constraints (+ WBS, 3-package dictionary)
  M2_Milestone2/   2.1 WBS & dictionary, 2.2 CPM/PERT & critical path,
                   2.3 Baseline Gantt & effort estimation (FP + COCOMO), 2.4 Risk register
  figures/         wbs.png, cpm_network.png, gantt_baseline.png, risk_matrix.png,
                   screen_*.png (app screenshots), results.md (all calculation tables)
  Word/            .docx versions of every Markdown document (generated, do not edit by hand)
```

Writing rules (asked by Burak):

- **Simple English**, short sentences. Explain each PM term in one sentence the first time.
- Every document starts with the same header table (Project, Course, Instructor, Milestone,
  Version / Date, Team). Images are linked as `../figures/<name>.png`.
- **Edit the Markdown, then run `python tools/build_docx.py`** to regenerate `docs/Word/`.
  The Word files get a cover page (university, course, instructor, team table) automatically.
- Do not automate Microsoft Word through COM (PDF export / field update hung on Burak's computer).
  Make PDFs by opening the .docx in Word and "Save As PDF" by hand.

## 7. Git and branching (input for the M3 SCM audit)

- Model: GitFlow-light. `main` = baselines/releases, `develop` = integration, work on
  `feature/*`, `bugfix/*`, `test/*`, `chore/*`, merged with `--no-ff`.
- Branches now: `feature/m1-docs`, `feature/database`, `feature/patient-module`,
  `feature/doctor-module`, `feature/appointment-booking`, `bugfix/double-booking-index`,
  `feature/dashboard`, `test/unit-tests`, `feature/m2-docs`, `chore/word-export`, `develop`, `main`.
- Tags: `m1-baseline`, `m2-baseline`.
- Commit messages: Conventional Commits style, e.g. `feat(appointments): ...`, `fix(db): ...`,
  `docs(m2): ...`, `test: ...`, `chore(tools): ...`.
- One real merge conflict happened (`app/clinic/__init__.py` when the patient and doctor branches
  were merged) and was resolved. The bugfix branch adds the filtered unique indexes.
- **Honest note:** this history was created on 5 Nov 2026 in one session from the finished code. Each
  commit is attributed to the member who owns that work package. Commit dates are all 5 Nov 2026.
  Davut, Enes and Alper commits use placeholder e-mails (`<name>@team.local`), so GitHub does not
  link them to their accounts. From now on, **every member should commit with their own Git
  identity** (`git config user.name / user.email`) so the M3 audit shows real work.
- Workflow from now on: `git checkout develop && git pull`, create `feature/<topic>`, commit,
  push, open a Pull Request into `develop`. Merge `develop` into `main` at each milestone and tag it
  (`m3-baseline`, `v1.0.0`).

## 8. Next steps (Milestone 3, due Week 13)

Do these only when the team decides to start M3:

1. **EVM report** (status date: end of Week 10 = working day 50, 4 Dec 2026).
   `tools/pm_calculations.py` already has EVM code: run `python tools/pm_calculations.py --evm`.
   The `STATUS` dictionary in that script holds **sample** percent-complete and actual hours.
   **Replace them with the team's real timesheet hours before using the report.**
2. **SCM audit:** configuration items, branching model, branch tree from
   `git log --graph --all --decorate --oneline`, commits per member (`git shortlog -sn --all`),
   audit checklist, findings.
3. **Final IEEE documentation** (IEEE 1058 SPMP + IEEE 830/29148 SRS structure): requirements,
   design (4 tables), implementation, tests, planned vs actual (estimated 1.78 KLOC vs measured size),
   installation guide, screenshots in `docs/figures/`.
4. **Retrospective & oral defense:** went well / not well / lessons / actions, demo script,
   presentation split between the 4 members.

Put M3 files in `docs/M3_Milestone3/` with names `3.1_...md`, `3.2_...md`, etc., then run
`python tools/build_docx.py`.

## 9. Rules for anyone (human or AI) changing this project

1. Keep code, documents and numbers in sync. If you change a feature, update the scope / WBS /
   requirements text that mentions it.
2. Run the tests before every commit: `cd app && python -m unittest discover -s tests -v`.
3. Do not run `init-db` on a database with real data: it deletes all tables.
4. Do not commit the lecture notes, passwords or real patient data (KVKK). Sample data is fake.
5. Work on a branch, never directly on `main`.
6. Update this file (`PROJECT_CONTEXT.md`) when you make a decision that the next person must know.
