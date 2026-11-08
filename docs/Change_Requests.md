# Change Request Log

| | |
|---|---|
| **Project** | Clinic Appointment System (CAS) |
| **Course** | SEN4100 Software Project Management, Haliç University |
| **Instructor** | Asst. Prof. M. Fatih Mintaş |
| **Milestone** | Between Milestone 2 and Milestone 3 (Week 6-7) |
| **Version / Date** | 1.0 / 8 November 2026 |
| **Team** | Burak Demir (20091000008), Davut Ayfer (20091000054), Enes Küçükkaya (22091000275), Alper Keskin (24352525053) |

A **change request (CR)** is a written request to change the approved scope. We follow the change
control process in the Scope Statement (M1, section 9): the request is written down, its impact is
checked, the Change Control Board (CCB) decides, and then the baselines are updated.

The scope, schedule and cost **baselines of Milestone 1 and Milestone 2 are not changed silently**.
The extra effort of approved changes is taken from the **management reserve (56 hours)**. This keeps
the M2 baseline (560 person-hours) valid for the Earned Value report in Milestone 3.

## 1. Summary

| ID | Change | Requested by | Date | Extra effort | Decision |
|---|---|---|---|---|---|
| CR-001 | Corporate user interface and a project logo | Burak Demir (PM, for the clinic manager) | 5 Nov 2026 | 12 h | Approved |
| CR-002 | Login system with user roles | Burak Demir | 5 Nov 2026 | 16 h | Approved |
| CR-003 | Master data screens for departments and appointment reasons | Burak Demir | 5 Nov 2026 | 12 h | Approved |
| CR-004 | Reporting page with filters and Excel (CSV) export | Burak Demir | 5 Nov 2026 | 14 h | Approved |
| CR-005 | Structure for appointment statuses (status table / workflow) | Burak Demir | 5 Nov 2026 | not estimated | **On hold** |
| | **Total approved** | | | **54 h** | Reserve left: 2 h |

## 2. Details

### CR-001 Corporate user interface and logo

- **Description:** New corporate look: sidebar menu, top bar with the signed-in user, KPI cards,
  consistent tables and forms, and a logo (calendar + medical cross + confirmation tick).
- **Reason:** The clinic manager wants a professional look for the demo and for daily use.
- **Impact:** Only the presentation layer (templates and CSS). No change to business rules.
  Risk R5 (low Flask experience) is slightly higher; no schedule impact because UI work runs in
  parallel with testing (activity J).
- **WBS:** part of 1.3.3 User interface design.

### CR-002 Login system with user roles

- **Description:** Users must sign in. Two roles:
  **ADMIN** (manages users, departments, reasons and doctors) and **RECEPTIONIST**
  (manages patients and appointments). Passwords are stored only as salted hashes (scrypt).
  Each new appointment stores the user who created it. Users can change their own password.
- **Reason:** Patient data is personal health data (KVKK). Only staff may see it (risk R8).
- **Impact:** M1 scope listed "user login" as **out of scope**. With this CR it moves **into** scope.
  New table `users`, new column `appointments.created_by`. All pages now need a signed-in user.
  Reduces risk R8 (privacy). New tests for login, roles and password hashing.
- **WBS:** new work inside 1.4.1 Database implementation and 1.4.4 Appointment module.

### CR-003 Departments and appointment reasons

- **Description:** Admin screens to add and edit departments (name, description, active) and
  standard appointment reasons. A reason can be general or belong to one department.
  The booking form shows only the reasons that fit the doctor's department.
- **Reason:** Free-text reasons could not be counted in reports.
- **Impact:** New table `appointment_reasons`; `appointments.reason` (free text) became
  `reason_id` + `notes`. Departments got `description` and `is_active`.
- **WBS:** 1.3.2 Database design, 1.4.3 Doctor & schedule module.

### CR-004 Reporting

- **Description:** A "Reports" page with a date range and department filter. It shows totals,
  completed, still booked and cancellation rate, and breakdowns by doctor (with utilization),
  department, appointment reason, day of the week and hour. All rows can be exported to a CSV file
  that opens in Excel.
- **Reason:** The clinic manager needs numbers for decisions (objective O3 in the charter).
- **Impact:** Read-only SQL queries; no change to existing data. Extends 1.4.5 Reports & dashboard.

### CR-005 Appointment status structure (on hold)

- **Description:** A separate structure for appointment statuses (for example a status table,
  more statuses such as "no-show", and status history).
- **Decision:** **On hold** by the PM. The current three statuses (BOOKED, COMPLETED, CANCELLED)
  stay as they are. The team will decide later; if approved it needs a new estimate because the
  management reserve is almost used.

## 3. Baseline and document impact

| Item | Impact |
|---|---|
| Scope statement (M1 1.3) | "User login" moves from out-of-scope to in-scope (CR-002). New features FR for reasons, departments, reports. |
| WBS (M2 2.1) | No new work packages; the work is inside existing packages and paid from the reserve. |
| Schedule (M2 2.2, 2.3) | No change to the critical path: the work was done in parallel with activity J (testing). |
| Cost (M2 2.3) | Baseline stays 560 h / BAC 84,000 TL. Reserve used: 54 of 56 h. |
| Risks (M2 2.4) | R8 (privacy) lower because of login. R9 (scope creep) **happened in a controlled way**: all changes went through this log. |
| Code size | Measured size grew from 920 to 1,933 non-blank lines (FP estimate was 1.78 KLOC). |
| Tests | Grew from 19 to 33 automated tests, all pass. |

## 4. Approval

| Name | Role | Decision | Date |
|---|---|---|---|
| Burak Demir | Project Manager, CCB chair | Approved CR-001 to CR-004, CR-005 on hold | 8 Nov 2026 |
| Davut Ayfer | CCB member (database owner) | Approved | 8 Nov 2026 |
| Asst. Prof. M. Fatih Mintaş | Sponsor | Informed (no milestone date or budget change) | |
