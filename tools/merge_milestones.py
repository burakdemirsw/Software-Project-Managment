"""Merge the Milestone 1 and Milestone 2 Markdown documents into one report.

Run:  python tools/merge_milestones.py   (then python tools/build_docx.py)
Output: docs/M1_M2_Combined_Report.md  (generated - edit the source documents, not this file)
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "M1_M2_Combined_Report.md"

PARTS = [
    ("Part I - Milestone 1 (Week 4): Initiation", "M1_Milestone1"),
    ("Part II - Milestone 2 (Week 7): Planning", "M2_Milestone2"),
]

HEADER = """# Milestone 1 & Milestone 2 Report

| | |
|---|---|
| **Project** | Clinic Appointment System (CAS) |
| **Course** | SEN4100 Software Project Management, Haliç University |
| **Instructor** | Asst. Prof. M. Fatih Mintaş |
| **Milestone** | Milestone 1 (Week 4) and Milestone 2 (Week 7) - combined report |
| **Version / Date** | 1.1 / 13 November 2026 |
| **Team** | Burak Demir (20091000008), Davut Ayfer (20091000054), Enes Küçükkaya (22091000275), Alper Keskin (24352525053) |

This report puts all Milestone 1 and Milestone 2 deliverables of the Clinic Appointment System
project into one document. Part I covers project initiation (concept, stakeholders, charter, scope).
Part II covers planning (WBS, schedule, effort estimation, risks). All numbers come from one
calculation script (`tools/pm_calculations.py`), so they are the same in every chapter.

## How this report covers the course requirements

| Course requirement (lecture notes) | Where in this report |
|---|---|
| Project concept proposal & stakeholder analysis, stakeholder register with at least 6 stakeholders, Power-Interest grid (Week 3) | Chapter 1.1 |
| Project charter: business case, measurable KPIs, squad roles, assumptions, constraints (Week 3) | Chapter 1.2 |
| Preliminary feasibility review (TELOS), NPV / ROI (Week 3) | Chapter 1.2, section 2 |
| Lifecycle model with technical justification in the charter and scope document (Week 2) | Chapters 1.1, 1.2 (section 1.2), 1.3 (section 12) |
| Scope statement: product scope, project scope, acceptance criteria, out-of-scope (Week 3) | Chapter 1.3 |
| Visual WBS (100% rule) and WBS dictionary for three core work packages (Week 4) | Chapter 1.3, section 10 |
| Backlog repository on GitHub / GitHub Projects (Weeks 2, 3, 4) | Chapter 1.3, section 11; Chapter 2.3, Part C |
| Effort estimate for every bottom-level work package (Week 5) | Chapter 2.1 |
| Algorithmic estimation: Function Points + COCOMO (Weeks 4-5) | Chapter 2.3, Part B |
| Story points (Fibonacci) and projected sprint velocity for the sprints (Weeks 2, 5) | Chapter 2.3, Part C |
| Baseline schedule with dependencies, AON network, CPM/PERT and critical path (Week 6) | Chapters 2.2 and 2.3, Part A |
| Risk register with at least 5 risks, P x I matrix, strategies and owners (Week 6) | Chapter 2.4 |
"""


def convert(md_text):
    lines = md_text.splitlines()
    out, i, in_code = [], 0, False
    # skip the per-document header table (it is on the cover page instead)
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("| |") and not out[-1:] == ["CODE"]:
            while i < len(lines) and lines[i].strip().startswith("|"):
                i += 1
            break
        out.append(line)
        i += 1
    else:
        out, i = [], 0
    out.extend(lines[i:])
    result = []
    for line in out:
        if line.strip().startswith("```"):
            in_code = not in_code
        if not in_code:
            m = re.match(r"^(#{1,5})(\s+.*)$", line)
            if m:
                line = "#" + m.group(1) + m.group(2)       # demote one level
            line = line.replace("](../figures/", "](figures/")
        result.append(line)
    return "\n".join(result).strip()


def main():
    parts = [HEADER.strip()]
    for title, folder in PARTS:
        parts.append(f"# {title}")
        for f in sorted((DOCS / folder).glob("*.md")):
            text = convert(f.read_text(encoding="utf-8"))
            number = f.stem.split("_")[0]                     # e.g. "1.1"
            text = re.sub(r"^## (?!\d)", f"## {number} ", text, count=1)
            parts.append(text)
    OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print("written:", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
