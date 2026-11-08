"""Merge the documents of each milestone into one report per milestone.

Run:  python tools/merge_milestones.py   (then python tools/build_docx.py)
Output (generated - edit the source documents, not these files):
  docs/M1_Combined_Report.md   = 1.1 + 1.2 + 1.3
  docs/M2_Combined_Report.md   = 2.1 + 2.2 + 2.3 + 2.4
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

TEAM = ("Burak Demir (20091000008), Davut Ayfer (20091000054), "
        "Enes Küçükkaya (22091000275), Alper Keskin (24352525053)")

REPORTS = [
    {
        "out": "M1_Combined_Report.md",
        "folder": "M1_Milestone1",
        "title": "Milestone 1 Report: Project Initiation",
        "milestone": "Milestone 1 (Week 4)",
        "date": "13 November 2026",
        "history": [("1.0", "23 Oct 2026", "Milestone 1 submitted (concept, charter, scope)."),
                    ("1.1", "13 Nov 2026", "Aligned with the lecture-note requirements: lifecycle justification in the "
                     "charter and scope, squad roles, benefit derivation and NPV sensitivity, sprint dates aligned with "
                     "the CPM baseline, backlog/board description; note about change request CR-002.")],
        "intro": ("This report contains all Milestone 1 deliverables of the Clinic Appointment System "
                  "project: the concept proposal and stakeholder analysis, the project charter, and the "
                  "scope statement with assumptions and constraints."),
        "coverage": [
            ("Project Concept Proposal & Stakeholder Analysis (syllabus)", "Chapter 1.1"),
            ("Formal Project Charter: business justification, objectives (syllabus)", "Chapter 1.2"),
            ("High-Level Scope Definition & Assumptions / Constraints (syllabus)", "Chapter 1.3"),
            ("Lifecycle model with technical justification (requirements, architectural risk, "
             "delivery cadence) in the charter and the scope document (Week 2)",
             "Chapter 1.2 section 1.2, Chapter 1.3 section 12 (also 1.1 section 5)"),
            ("Tracking tool that matches the process model: GitHub Projects with 2-week sprints and "
             "story points (Week 2)", "Chapter 1.3 section 11"),
            ("Charter per template: business case, measurable KPIs, squad roles, assumptions, "
             "constraints (Week 3)", "Chapter 1.2 sections 1.1, 2, 3, 10"),
            ("Stakeholder register with at least 6 stakeholders and Mendelow Power-Interest grid (Week 3)",
             "Chapter 1.1 section 6"),
            ("Scope statement: product scope, project scope, acceptance criteria, out-of-scope (Week 3)",
             "Chapter 1.3 sections 1, 5, 6"),
            ("Preliminary feasibility review with TELOS, technical and economic logic (Week 3)",
             "Chapter 1.2 section 2"),
            ("Centralized backlog on GitHub / GitHub Projects reflecting the scope baseline (Week 3)",
             "Chapter 1.3 section 11"),
            ("Visual WBS (100% rule) and WBS dictionary for three core work packages (Week 4)",
             "Chapter 1.3 section 10"),
        ],
    },
    {
        "out": "M2_Combined_Report.md",
        "folder": "M2_Milestone2",
        "title": "Milestone 2 Report: Project Planning",
        "milestone": "Milestone 2 (Week 7)",
        "date": "13 November 2026",
        "history": [("1.0", "13 Nov 2026", "Milestone 2 deliverables: WBS dictionary, CPM/PERT, Gantt, estimation "
                     "(FP, COCOMO, story points), risk register, resource levelling, change requests.")],
        "intro": ("This report contains all Milestone 2 deliverables of the Clinic Appointment System "
                  "project: the WBS and WBS dictionary, the CPM/PERT network and critical path, the "
                  "baseline Gantt chart with the effort estimation, and the initial risk register. All "
                  "numbers come from one calculation script (tools/pm_calculations.py)."),
        "coverage": [
            ("Comprehensive Work Breakdown Structure (WBS & Dictionary) (syllabus)", "Chapter 2.1"),
            ("CPM / PERT Network Diagram & Critical Path Calculation (syllabus)", "Chapter 2.2"),
            ("Baseline Gantt Chart & Algorithmic Effort Estimation (syllabus)", "Chapter 2.3 Parts A and B"),
            ("Initial Risk Register: identification, qualitative matrix (syllabus)", "Chapter 2.4"),
            ("Effort estimate for every bottom-level work package (Week 5)", "Chapter 2.1 sections 5-6"),
            ("Predictive part: algorithmic estimation, FP sizing converted to hours and cost (Weeks 4-5)",
             "Chapter 2.3 Part B"),
            ("Agile part: story points (Fibonacci) and projected sprint velocity (Weeks 2, 5)",
             "Chapter 2.3 Part C"),
            ("Estimates documented on the GitHub board (Week 4)", "Chapter 2.3 Part C (C5); docs/backlog"),
            ("Baseline schedule from the WBS with dependencies and critical path (Week 6)",
             "Chapter 2.2, Chapter 2.3 Part A"),
            ("Risk register with at least 5 risks, mitigation strategies and owners; P-I matrix (Week 6)",
             "Chapter 2.4"),
            ("Resource loading and levelling of the schedule", "Chapter 2.2"),
            ("Change control after the baseline (scope changes CR-001..CR-005)", "Chapter 2.5"),
        ],
    },
]


def strip_header_table(md_text):
    """Remove the per-document metadata table (it is on the cover page instead)."""
    lines = md_text.splitlines()
    for i, line in enumerate(lines[:15]):
        if line.strip().startswith("| |"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            return "\n".join(lines[:i] + lines[j:])
    return md_text


def header(r):
    rows = "\n".join(f"| {req} | {where} |" for req, where in r["coverage"])
    history = "\n".join(f"| {v} | {d} | {c} |" for v, d, c in r["history"])
    return f"""# {r['title']}

| | |
|---|---|
| **Project** | Clinic Appointment System (CAS) |
| **Course** | SEN4100 Software Project Management, Haliç University |
| **Instructor** | Asst. Prof. M. Fatih Mintaş |
| **Milestone** | {r['milestone']} |
| **Version / Date** | {r['history'][-1][0]} / {r['date']} |
| **Team** | {TEAM} |

{r['intro']}

**Revision history**

| Version | Date | Change |
|---|---|---|
{history}

## How this report covers the course requirements

| Course requirement (syllabus and lecture notes) | Where in this report |
|---|---|
{rows}"""


def main():
    for r in REPORTS:
        parts = [header(r)]
        for f in sorted((DOCS / r["folder"]).glob("*.md")):
            text = strip_header_table(f.read_text(encoding="utf-8")).replace("](../figures/", "](figures/")
            number = f.stem.split("_")[0]                         # e.g. "1.1"
            text = re.sub(r"^# (?!\d)", f"# {number} ", text, count=1, flags=re.M)
            parts.append(text.strip())
        (DOCS / r["out"]).write_text("\n\n".join(parts) + "\n", encoding="utf-8")
        print("written:", (DOCS / r["out"]).relative_to(ROOT))


if __name__ == "__main__":
    main()
