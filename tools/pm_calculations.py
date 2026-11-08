"""Project management calculations for the Clinic Appointment System.

This script is the "single source of truth" for the numbers in the documents:
  * PERT expected times and variances
  * CPM forward / backward pass, slack and critical path
  * Probability of finishing before the deadline (normal distribution)
  * Baseline Gantt chart
  * COCOMO 81 effort estimation (Basic + Intermediate)
  * Earned Value Management (EVM) at the status date
  * Risk matrix

Run:  python tools/pm_calculations.py          (add --evm for the Milestone 3 EVM report)
Output: docs/figures/*.png and docs/figures/results.md (all tables)
"""
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "docs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

PROJECT_START = date(2026, 9, 28)   # Monday of Week 1
DEADLINE_DAYS = 60                  # end of Week 12 (Week 13 = presentation)
HOURLY_RATE = 150                   # TL per person-hour (notional cost for EVM)
STATUS_DAY = 50                     # EVM status date = end of Week 10
# x = number of working days finished, so x = 20 is the end of Friday 23 Oct (end of Week 4)
MILESTONES = [(20, "M1 23 Oct"), (35, "M2 13 Nov"), (65, "M3 25 Dec")]
SPRINTS = [("Sprint 1 (W4-5)", 15, 25), ("Sprint 2 (W6-7)", 25, 35), ("Sprint 3 (W8-9)", 35, 45)]
TEAM = ["Burak Demir", "Davut Ayfer", "Enes Kucukkaya", "Alper Keskin"]

# id, name, optimistic, most likely, pessimistic (working days), predecessors, owner, planned hours
ACTIVITIES = [
    ("A", "Project initiation & concept proposal", 3, 5, 7, [], "Burak Demir", 30),
    ("B", "Requirements & stakeholder analysis", 5, 7, 11, ["A"], "Burak Demir, Alper Keskin", 50),
    ("C", "Project planning (WBS, schedule, cost, risk)", 4, 6, 9, ["B"], "Burak Demir", 45),
    ("D", "System & UI design", 5, 7, 11, ["B"], "Enes Kucukkaya", 50),
    ("E", "Database design & implementation", 4, 6, 9, ["B"], "Davut Ayfer", 45),
    ("F", "Patient module", 5, 8, 12, ["D", "E"], "Enes Kucukkaya", 60),
    ("G", "Doctor & schedule module", 4, 6, 10, ["D", "E"], "Davut Ayfer", 45),
    ("H", "Appointment booking module", 7, 10, 16, ["F", "G"], "Burak Demir, Davut Ayfer", 80),
    ("I", "Reports & dashboard", 3, 4, 7, ["H"], "Enes Kucukkaya", 30),
    ("J", "Testing & bug fixing", 5, 7, 12, ["H"], "Alper Keskin", 55),
    ("K", "Final documentation (IEEE)", 4, 6, 9, ["C", "I", "J"], "Alper Keskin", 45),
    ("L", "Retrospective & presentation", 2, 3, 5, ["K"], "All members", 25),
]

# EVM status at end of Week 10: (percent complete, actual hours)
STATUS = {
    "A": (100, 32), "B": (100, 55), "C": (100, 40), "D": (100, 52), "E": (100, 50),
    "F": (100, 66), "G": (100, 44), "H": (90, 85), "I": (50, 14), "J": (40, 20),
    "K": (20, 8), "L": (0, 0),
}

# Risk register: id, short name, category, probability (0.1-0.9), impact (1-5)
RISKS = [
    ("R1", "Team member not available (exams, illness)", "Organizational", 0.7, 3),
    ("R2", "Requirements change late", "Project Management", 0.5, 4),
    ("R3", "Effort underestimated", "Project Management", 0.5, 3),
    ("R4", "Double booking bug in scheduling", "Technical", 0.3, 5),
    ("R5", "Low experience with Flask / pyodbc", "Technical", 0.5, 2),
    ("R6", "Data loss (no database backup)", "Technical", 0.3, 4),
    ("R7", "Merge conflicts in Git", "Technical", 0.5, 2),
    ("R8", "Personal health data privacy (KVKK) issue", "External", 0.3, 5),
    ("R9", "Scope creep (extra features)", "Project Management", 0.5, 3),
    ("R10", "Poor communication in team", "Organizational", 0.3, 3),
    ("R11", "SQL Server LocalDB setup fails on a laptop", "Technical", 0.5, 2),
]
PROB_LEVELS = [0.1, 0.3, 0.5, 0.7, 0.9]


def risk_zone(exposure):
    return "Red" if exposure >= 2.0 else "Yellow" if exposure >= 1.0 else "Green"


OUT = []


def md(line=""):
    OUT.append(line)


# ---------------------------------------------------------------- calendar
def workday_to_date(day_index):
    """Working day number (0 = project start) -> calendar date (skips weekends)."""
    d = PROJECT_START
    n = int(math.floor(day_index))
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


# ---------------------------------------------------------------- PERT + CPM
def pert_cpm():
    act = {}
    for a in ACTIVITIES:
        aid, name, o, m, p, pred, owner, hours = a
        te = (o + 4 * m + p) / 6
        var = ((p - o) / 6) ** 2
        act[aid] = dict(id=aid, name=name, o=o, m=m, p=p, pred=pred, owner=owner,
                        hours=hours, te=te, var=var)
    order = [a[0] for a in ACTIVITIES]          # already topologically sorted
    for aid in order:                            # forward pass
        x = act[aid]
        x["es"] = max((act[p]["ef"] for p in x["pred"]), default=0.0)
        x["ef"] = x["es"] + x["te"]
    finish = max(x["ef"] for x in act.values())
    succ = {aid: [b for b in order if aid in act[b]["pred"]] for aid in order}
    for aid in reversed(order):                  # backward pass
        x = act[aid]
        x["lf"] = min((act[s]["ls"] for s in succ[aid]), default=finish)
        x["ls"] = round(x["lf"] - x["te"], 6) + 0.0
        x["slack"] = round(x["ls"] - x["es"], 2) + 0.0
        x["critical"] = abs(x["slack"]) < 1e-6
    return act, order, succ, finish


def normal_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def write_pert_tables(act, order, finish):
    md("## PERT estimates (working days)")
    md()
    md("| ID | Activity | Predecessors | O | M | P | te = (O+4M+P)/6 | Variance ((P-O)/6)^2 |")
    md("|---|---|---|---|---|---|---|---|")
    for aid in order:
        x = act[aid]
        md(f"| {aid} | {x['name']} | {', '.join(x['pred']) or '-'} | {x['o']} | {x['m']} | {x['p']} "
           f"| {x['te']:.2f} | {x['var']:.3f} |")
    md()
    md("## CPM forward and backward pass")
    md()
    md("| ID | te | ES | EF | LS | LF | Slack | Critical |")
    md("|---|---|---|---|---|---|---|---|")
    for aid in order:
        x = act[aid]
        md(f"| {aid} | {x['te']:.2f} | {x['es']:.2f} | {x['ef']:.2f} | {x['ls']:.2f} | {x['lf']:.2f} "
           f"| {x['slack']:.2f} | {'YES' if x['critical'] else 'no'} |")
    cp = [a for a in order if act[a]["critical"]]
    var = sum(act[a]["var"] for a in cp)
    sd = math.sqrt(var)
    z = (DEADLINE_DAYS - finish) / sd
    md()
    md(f"- Critical path: **{' -> '.join(cp)}**")
    md(f"- Expected project duration: **{finish:.2f} working days** (about {finish / 5:.1f} weeks)")
    md(f"- Variance of critical path: {var:.3f}, standard deviation: {sd:.2f} days")
    md(f"- Deadline: {DEADLINE_DAYS} working days (end of Week 12, {workday_to_date(DEADLINE_DAYS - 1)})")
    md(f"- Z = ({DEADLINE_DAYS} - {finish:.2f}) / {sd:.2f} = **{z:.2f}**")
    md(f"- Probability to finish on time: **P(T <= {DEADLINE_DAYS}) = {normal_cdf(z) * 100:.1f}%**")
    for target in (55, 58, 62):
        zz = (target - finish) / sd
        md(f"- P(T <= {target}) = {normal_cdf(zz) * 100:.1f}%")
    md()
    return cp, sd


# ---------------------------------------------------------------- figures
def draw_network(act, order, succ):
    pos = {"A": (0, 2), "B": (1, 2), "C": (2, 3.6), "D": (2, 2), "E": (2, 0.4), "F": (3, 2.8),
           "G": (3, 1.2), "H": (4, 2), "I": (5, 2.8), "J": (5, 1.2), "K": (6, 2), "L": (7, 2)}
    fig, ax = plt.subplots(figsize=(15, 6.5))
    w, h = 0.78, 1.05
    for aid in order:
        for s in succ[aid]:
            (x1, y1), (x2, y2) = pos[aid], pos[s]
            crit = act[aid]["critical"] and act[s]["critical"]
            ax.annotate("", xy=(x2 - w / 2, y2), xytext=(x1 + w / 2, y1),
                        arrowprops=dict(arrowstyle="-|>", lw=2.4 if crit else 1.2,
                                        color="#c0392b" if crit else "#555"))
    for aid in order:
        x, y = pos[aid]
        a = act[aid]
        color = "#fdecea" if a["critical"] else "#eef3f7"
        edge = "#c0392b" if a["critical"] else "#456"
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02",
                                    fc=color, ec=edge, lw=2 if a["critical"] else 1))
        ax.plot([x - w / 2, x + w / 2], [y + h / 6, y + h / 6], color=edge, lw=0.8)
        ax.plot([x - w / 2, x + w / 2], [y - h / 6, y - h / 6], color=edge, lw=0.8)
        ax.text(x - w / 2 + 0.04, y + h / 3, f"{a['es']:.1f}", va="center", fontsize=8)
        ax.text(x + w / 2 - 0.04, y + h / 3, f"{a['ef']:.1f}", va="center", ha="right", fontsize=8)
        ax.text(x, y + h / 3, f"te={a['te']:.1f}", va="center", ha="center", fontsize=7, color="#555")
        ax.text(x, y, f"{aid}", va="center", ha="center", fontsize=13, weight="bold")
        ax.text(x - w / 2 + 0.04, y - h / 3, f"{a['ls']:.1f}", va="center", fontsize=8)
        ax.text(x + w / 2 - 0.04, y - h / 3, f"{a['lf']:.1f}", va="center", ha="right", fontsize=8)
        ax.text(x, y - h / 3, f"S={a['slack']:.1f}", va="center", ha="center", fontsize=7, color="#555")
    ax.text(-0.4, -0.55, "Node:  ES | te | EF  /  activity  /  LS | slack | LF     "
            "Red = critical path", fontsize=9, color="#333")
    ax.set_xlim(-0.6, 7.6)
    ax.set_ylim(-0.8, 4.3)
    ax.axis("off")
    ax.set_title("CPM / PERT Activity-on-Node Network (working days)", fontsize=13)
    fig.tight_layout()
    fig.savefig(FIG / "cpm_network.png", dpi=150)
    plt.close(fig)


def draw_gantt(act, order):
    fig, ax = plt.subplots(figsize=(13, 6))
    for i, aid in enumerate(order):
        a = act[aid]
        y = len(order) - 1 - i
        ax.barh(y, a["te"], left=a["es"], color="#c0392b" if a["critical"] else "#2e86ab", height=0.55)
        if a["slack"] > 0:
            ax.barh(y, a["slack"], left=a["ef"], color="none", edgecolor="#999", hatch="//", height=0.55)
        ax.text(a["es"] + 0.2, y, f"{aid}", va="center", color="white", fontsize=9, weight="bold")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{aid}  {act[aid]['name']}" for aid in reversed(order)], fontsize=9)
    for name, start, end in SPRINTS:
        ax.axvspan(start, end, color="#14b8a6", alpha=0.08)
        ax.text((start + end) / 2, -0.55, name, ha="center", fontsize=8.5, color="#0e7490", weight="bold")
    ax.axvline(DEADLINE_DAYS, color="#c0392b", ls=":", lw=1.2)
    ax.text(DEADLINE_DAYS - 0.3, -0.55, "Deadline 18 Dec", ha="right", fontsize=8, color="#c0392b")
    for d, label in MILESTONES:
        ax.axvline(d, color="#333", ls="--", lw=1)
        ax.plot(d, len(order) - 0.3, marker="D", color="#f39c12", ms=10)
        ax.text(d + 0.3, len(order) - 0.3, label, fontsize=8.5, va="center")
    ticks = list(range(0, 66, 5))
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"W{t // 5 + 1}\n{workday_to_date(t).strftime('%d %b')}" for t in ticks], fontsize=8)
    ax.set_xlim(0, 66)
    ax.set_ylim(-0.9, len(order) + 0.3)
    ax.grid(axis="x", alpha=0.3)
    ax.set_title("Baseline Gantt Chart (red = critical, hatched = slack, shaded = sprints)", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG / "gantt_baseline.png", dpi=150)
    plt.close(fig)


def write_gantt_table(act, order):
    md("## Baseline schedule (calendar dates)")
    md()
    md("| ID | Activity | Owner | Start | Finish | Duration (days) |")
    md("|---|---|---|---|---|---|")
    for aid in order:
        a = act[aid]
        start = math.floor(round(a["es"], 6))
        finish = max(math.ceil(round(a["ef"], 6)) - 1, start)
        md(f"| {aid} | {a['name']} | {a['owner']} | {workday_to_date(start)} "
           f"| {workday_to_date(finish)} | {a['te']:.1f} |")
    md()
    md("Date rule: ES and EF are counted in working days from 28 Sep 2026. An activity starts on working day "
       "floor(ES) and finishes on working day ceil(EF) - 1, so a part-day at the end is shown on the last day "
       "that the activity uses (a successor may start on the same day).")
    md()
    md("| Sprint | Weeks | Dates | Main activities |")
    md("|---|---|---|---|")
    for name, start, end in SPRINTS:
        acts = [a for a in order if a in "EFGHIJ"
                and min(act[a]["ef"], end) - max(act[a]["es"], start) >= 1.5]   # at least 1.5 days inside
        md(f"| {name.split(' (')[0]} | {start // 5 + 1}-{end // 5} | {workday_to_date(start)} to "
           f"{workday_to_date(end - 1)} | {', '.join(acts)} |")
    md()


def _spread(load, hours, start, end, shares):
    days = end - start
    day = start
    while day < end - 1e-9:
        nxt = min(math.floor(day) + 1, end)
        w = int(day // 5)
        if w < len(next(iter(load.values()))):
            for person, share in shares.items():
                load[person][w] += hours * share * (nxt - day) / days
        day = nxt


def _loading(act, order, levelled):
    weeks = 12
    load = {p: [0.0] * weeks for p in TEAM}
    for aid in order:
        a = act[aid]
        owners = TEAM if a["owner"] == "All members" else [o.strip() for o in a["owner"].split(",")]
        shares = {o: 1 / len(owners) for o in owners}
        hours = a["hours"]
        if levelled:
            if aid == "F":
                shares = {"Enes Kucukkaya": 0.7, "Alper Keskin": 0.3}
            if aid == "G":
                shares = {"Davut Ayfer": 0.7, "Alper Keskin": 0.3}
            if aid == "D":
                shares = {"Enes Kucukkaya": 0.7, "Alper Keskin": 0.3}
            if aid == "J":   # module owners fix their own bugs during testing
                shares = {"Alper Keskin": 0.5, "Burak Demir": 0.2, "Davut Ayfer": 0.15, "Enes Kucukkaya": 0.15}
            if aid == "K":   # 1.1.4 Monitoring & EVM (10 h) is level-of-effort work of the PM from F to J
                hours -= 10
                _spread(load, 10, act["F"]["es"], act["J"]["ef"], {"Burak Demir": 1.0})
        _spread(load, hours, a["es"], a["ef"], shares)
    return load


def _loading_table(load, title):
    weeks = 12
    md(f"### {title}")
    md()
    md("| Member | " + " | ".join(f"W{w + 1}" for w in range(weeks)) + " | Total | Max/week |")
    md("|---|" + "---|" * (weeks + 2))
    for p in TEAM:
        row = load[p]
        md(f"| {p} | " + " | ".join(f"{h:.0f}" for h in row) + f" | {sum(row):.0f} | {max(row):.0f} |")
    team = [sum(load[p][w] for p in TEAM) for w in range(weeks)]
    md("| **Team** | " + " | ".join(f"{h:.0f}" for h in team) + f" | {sum(team):.0f} | {max(team):.0f} |")
    md()


def resource_loading(act, order):
    """Planned hours per person per week (activity hours spread evenly over its duration)."""
    md("## Resource loading (planned hours per person per week)")
    md()
    raw = _loading(act, order, levelled=False)
    lev = _loading(act, order, levelled=True)
    _loading_table(raw, "Before levelling (owners only)")
    _loading_table(lev, "After levelling (baseline)")
    over = [(p, w + 1, raw[p][w]) for p in TEAM for w in range(12) if raw[p][w] > 20]
    md("- Average load is 560 h / 4 people / 12 weeks = about 11.7 h per person per week (plan: ~12 h).")
    md("- **Over-allocation before levelling** (more than 20 h in one week): "
       + ", ".join(f"{p.split()[0]} W{w} ({h:.0f} h)" for p, w, h in over) + ".")
    md("- **Levelling actions in the baseline:** Alper Keskin pairs with the module owners in Sprint 1-2 and takes "
       "30% of F (patient module) and G (doctor module); the PM's 1.1.4 Monitoring & EVM (10 h) is spread from the "
       "start of F to the end of J as level-of-effort work. Durations do not change, so the critical path stays the same.")
    peak = max((lev[p][w], p, w + 1) for p in TEAM for w in range(12))
    md(f"- **Remaining peak after levelling:** {peak[1]} in Week {peak[2]} with {peak[0]:.0f} h. Peak weeks are "
       "planned outside exam days and are watched under risks R1 (member not available) and R3 (effort "
       "underestimated).")
    md()


# ---------------------------------------------------------------- COCOMO
# Function Point Analysis (IFPUG weights: simple / average / complex)
FP_WEIGHTS = {"EI": (3, 4, 6), "EO": (4, 5, 7), "EQ": (3, 4, 6), "ILF": (7, 10, 15), "EIF": (5, 7, 10)}
FP_ITEMS = [  # type, item, complexity 0=simple 1=average 2=complex
    ("EI", "Add patient form", 1), ("EI", "Edit patient form", 1), ("EI", "Delete patient", 0),
    ("EI", "Add doctor form", 1), ("EI", "Edit doctor form", 1),
    ("EI", "Book appointment (with rule checks)", 2),
    ("EI", "Cancel appointment", 0), ("EI", "Complete appointment", 0),
    ("EO", "Dashboard (counts, cancellation rate)", 2), ("EO", "Doctor utilization report", 1),
    ("EQ", "Search patients", 1), ("EQ", "List doctors", 0),
    ("EQ", "List / filter appointments", 1), ("EQ", "Free slots query (JSON)", 1),
    ("ILF", "Patients table", 0), ("ILF", "Doctors table", 0),
    ("ILF", "Appointments table", 1), ("ILF", "Departments table", 0),
]
GSC = [  # 14 General System Characteristics, rating 0-5
    ("Data communications", 3), ("Distributed data processing", 1), ("Performance", 2),
    ("Heavily used configuration", 1), ("Transaction rate", 2), ("Online data entry", 5),
    ("End-user efficiency", 4), ("Online update", 4), ("Complex processing", 2),
    ("Reusability", 2), ("Installation ease", 2), ("Operational ease", 3),
    ("Multiple sites", 1), ("Facilitate change", 3),
]
LOC_PER_FP = 20   # assumed gearing factor for Python + HTML/SQL (high-level languages)


def function_points():
    md("## Function Point Analysis")
    md()
    md("| Type | Item | Complexity | Weight |")
    md("|---|---|---|---|")
    ufp = 0
    names = ["Simple", "Average", "Complex"]
    for t, item, c in FP_ITEMS:
        w = FP_WEIGHTS[t][c]
        ufp += w
        md(f"| {t} | {item} | {names[c]} | {w} |")
    md(f"| | **Unadjusted Function Points (UFP)** | | **{ufp}** |")
    md()
    md("| # | General System Characteristic | Rating (0-5) |")
    md("|---|---|---|")
    for k, (n, r) in enumerate(GSC, 1):
        md(f"| {k} | {n} | {r} |")
    tdi = sum(r for _, r in GSC)
    vaf = 0.65 + 0.01 * tdi
    fp = ufp * vaf
    md(f"| | **Total Degree of Influence (TDI)** | **{tdi}** |")
    md()
    md(f"- VAF = 0.65 + 0.01 x TDI = 0.65 + 0.01 x {tdi} = **{vaf:.2f}**")
    md(f"- FP = UFP x VAF = {ufp} x {vaf:.2f} = **{fp:.1f} function points**")
    md(f"- Size = FP x {LOC_PER_FP} LOC/FP = **{fp * LOC_PER_FP:.0f} LOC = {fp * LOC_PER_FP / 1000:.2f} KLOC**")
    md()
    return fp * LOC_PER_FP / 1000


SIZE = [  # module, optimistic, most likely, pessimistic LOC
    ("Database layer (schema, connection, seed)", 100, 150, 250),
    ("Patient module", 150, 230, 350),
    ("Doctor module", 120, 180, 300),
    ("Appointment booking + rules", 250, 330, 500),
    ("Reports & dashboard", 100, 160, 250),
    ("User interface (HTML templates, CSS, JS)", 250, 330, 500),
    ("Automated tests", 150, 230, 350),
]
DRIVERS = [  # name, rating, multiplier (COCOMO 81 table values)
    ("RELY - Required reliability", "High (health data)", 1.15),
    ("DATA - Database size", "Low", 0.94),
    ("CPLX - Product complexity", "Low", 0.85),
    ("TIME - Execution time constraint", "Nominal", 1.00),
    ("STOR - Main storage constraint", "Nominal", 1.00),
    ("VIRT - Platform volatility", "Low", 0.87),
    ("TURN - Turnaround time", "Low", 0.87),
    ("ACAP - Analyst capability", "Nominal", 1.00),
    ("AEXP - Application experience", "Low (students)", 1.13),
    ("PCAP - Programmer capability", "Nominal", 1.00),
    ("VEXP - Platform experience", "Nominal", 1.00),
    ("LEXP - Language experience", "High (Python)", 0.95),
    ("MODP - Modern practices", "High (Git, tests)", 0.91),
    ("TOOL - Software tools", "High", 0.91),
    ("SCED - Schedule constraint", "Nominal", 1.00),
]
HOURS_PER_PM = 152


def cocomo(kloc_fp):
    md("## Cross-check: three-point size estimate per module (LOC)")
    md()
    md("| Module | O | M | P | Expected (O+4M+P)/6 |")
    md("|---|---|---|---|---|")
    total = 0
    for name, o, m, p in SIZE:
        e = (o + 4 * m + p) / 6
        total += e
        md(f"| {name} | {o} | {m} | {p} | {e:.0f} |")
    md(f"| **Total** | | | | **{total:.0f} LOC = {total / 1000:.2f} KLOC** |")
    md()
    md(f"The FP size ({kloc_fp:.2f} KLOC) and the module estimate ({total / 1000:.2f} KLOC) differ by "
       f"{(kloc_fp * 1000 - total) / total * 100:+.1f}%. We use the FP size for COCOMO.")
    md()
    kloc = kloc_fp
    e_basic = 2.4 * kloc ** 1.05
    d_basic = 2.5 * e_basic ** 0.38
    eaf = math.prod(m for _, _, m in DRIVERS)
    e_nom = 3.2 * kloc ** 1.05
    e_int = e_nom * eaf
    d_int = 2.5 * e_int ** 0.38
    md("## Basic COCOMO (organic mode)")
    md()
    md(f"- Effort E = 2.4 x KLOC^1.05 = 2.4 x {kloc:.2f}^1.05 = **{e_basic:.2f} person-months**")
    md(f"- Duration D = 2.5 x E^0.38 = **{d_basic:.2f} months**")
    md(f"- Average staff = E / D = **{e_basic / d_basic:.2f} full-time people**")
    md(f"- Effort in hours = {e_basic:.2f} x {HOURS_PER_PM} = **{e_basic * HOURS_PER_PM:.0f} person-hours**")
    md()
    md("## Intermediate COCOMO (organic mode)")
    md()
    md("| Cost driver | Rating | Multiplier |")
    md("|---|---|---|")
    for n, r, m in DRIVERS:
        md(f"| {n} | {r} | {m:.2f} |")
    md(f"| **EAF (product)** | | **{eaf:.3f}** |")
    md()
    md(f"- Nominal effort = 3.2 x {kloc:.2f}^1.05 = {e_nom:.2f} PM")
    md(f"- Adjusted effort E = {e_nom:.2f} x {eaf:.3f} = **{e_int:.2f} person-months** "
       f"= **{e_int * HOURS_PER_PM:.0f} person-hours**")
    md(f"- Duration D = 2.5 x E^0.38 = **{d_int:.2f} months**")
    md(f"- Average staff = **{e_int / d_int:.2f} full-time people**")
    bottom_up = sum(a[7] for a in ACTIVITIES)
    md()
    md("## Comparison with bottom-up (WBS) estimate")
    md()
    md(f"- WBS bottom-up estimate: **{bottom_up} person-hours** "
       f"({bottom_up / HOURS_PER_PM:.2f} PM)")
    md(f"- Team capacity: 4 students x 12 weeks x ~12 hours/week = **576 person-hours**")
    md(f"- Cost view: Basic {e_basic * HOURS_PER_PM:.0f} h x 150 TL = {e_basic * HOURS_PER_PM * 150:,.0f} TL; "
       f"Intermediate {e_int * HOURS_PER_PM:.0f} h x 150 TL = {e_int * HOURS_PER_PM * 150:,.0f} TL; "
       f"WBS {bottom_up} h x 150 TL = {bottom_up * 150:,} TL (BAC)")
    md("- COCOMO covers design, coding, testing and project management of the software; the whole WBS "
       "(560 h) has the same coverage, so the full WBS is compared.")
    md(f"- Difference Intermediate COCOMO vs WBS: "
       f"{(e_int * HOURS_PER_PM - bottom_up) / bottom_up * 100:+.1f}%")
    md()
    return kloc, e_basic, e_int


# ---------------------------------------------------------------- EVM
def planned_hours_until(a, day):
    if day <= a["es"]:
        return 0.0
    if day >= a["ef"]:
        return a["hours"]
    return a["hours"] * (day - a["es"]) / a["te"]


def evm(act, order, finish):
    bac_h = sum(act[a]["hours"] for a in order)
    md("## Earned Value Management (status date: end of Week 10, "
       f"working day {STATUS_DAY}, {workday_to_date(STATUS_DAY - 1)})")
    md()
    md(f"Cost unit: person-hours x {HOURLY_RATE} TL. BAC = {bac_h} h x {HOURLY_RATE} = "
       f"{bac_h * HOURLY_RATE:,} TL")
    md()
    md("| ID | Activity | Budget (TL) | % complete | PV (TL) | EV (TL) | AC (TL) |")
    md("|---|---|---|---|---|---|---|")
    pv = ev = ac = 0.0
    for aid in order:
        a = act[aid]
        pct, hours = STATUS[aid]
        p = planned_hours_until(a, STATUS_DAY) * HOURLY_RATE
        e = a["hours"] * pct / 100 * HOURLY_RATE
        c = hours * HOURLY_RATE
        pv, ev, ac = pv + p, ev + e, ac + c
        md(f"| {aid} | {a['name']} | {a['hours'] * HOURLY_RATE:,.0f} | {pct}% | {p:,.0f} | {e:,.0f} | {c:,.0f} |")
    md(f"| | **Total** | **{bac_h * HOURLY_RATE:,.0f}** | | **{pv:,.0f}** | **{ev:,.0f}** | **{ac:,.0f}** |")
    bac = bac_h * HOURLY_RATE
    sv, cv = ev - pv, ev - ac
    spi, cpi = ev / pv, ev / ac
    eac = bac / cpi
    etc = eac - ac
    vac = bac - eac
    tcpi = (bac - ev) / (bac - ac)
    eac_t = finish / spi
    md()
    md("| Metric | Formula | Value | Meaning |")
    md("|---|---|---|---|")
    md(f"| Schedule Variance | SV = EV - PV | {sv:,.0f} TL | {'behind' if sv < 0 else 'ahead of'} schedule |")
    md(f"| Cost Variance | CV = EV - AC | {cv:,.0f} TL | {'over' if cv < 0 else 'under'} budget |")
    md(f"| Schedule Performance Index | SPI = EV / PV | {spi:.3f} | {spi * 100:.1f}% of planned work done |")
    md(f"| Cost Performance Index | CPI = EV / AC | {cpi:.3f} | {cpi:.2f} TL of value per 1 TL spent |")
    md(f"| Estimate at Completion | EAC = BAC / CPI | {eac:,.0f} TL | expected final cost |")
    md(f"| Estimate to Complete | ETC = EAC - AC | {etc:,.0f} TL | cost of remaining work |")
    md(f"| Variance at Completion | VAC = BAC - EAC | {vac:,.0f} TL | expected over/under run |")
    md(f"| To-Complete Performance Index | TCPI = (BAC - EV) / (BAC - AC) | {tcpi:.3f} | needed efficiency |")
    md(f"| Estimated duration | {finish:.1f} / SPI | {eac_t:.1f} days | forecast finish |")
    md()

    # S-curve
    days = [i / 2 for i in range(0, int(finish * 2) + 2)]
    pv_curve = [sum(planned_hours_until(act[a], d) for a in order) * HOURLY_RATE / 1000 for d in days]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(days, pv_curve, color="#2e86ab", lw=2, label="PV (planned value, baseline)")
    ax.plot([0, STATUS_DAY], [0, ev / 1000], color="#27ae60", lw=2, marker="o", label="EV (earned value)")
    ax.plot([0, STATUS_DAY], [0, ac / 1000], color="#c0392b", lw=2, marker="o", label="AC (actual cost)")
    ax.plot([STATUS_DAY, finish / spi], [ac / 1000, eac / 1000], color="#c0392b", ls=":", lw=1.5,
            label="Forecast (EAC)")
    ax.axhline(bac / 1000, color="#555", ls="--", lw=1)
    ax.text(1, bac / 1000 + 1, f"BAC = {bac / 1000:.1f}k TL", fontsize=9)
    ax.axvline(STATUS_DAY, color="#999", ls="--", lw=1)
    ax.text(STATUS_DAY + 0.5, 5, "Status date\n(end of Week 10)", fontsize=9)
    ax.set_xlabel("Working day")
    ax.set_ylabel("Thousand TL")
    ax.set_title(f"EVM S-curve   SPI = {spi:.2f}   CPI = {cpi:.2f}")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "evm_scurve.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- risk matrix
def risk_matrix():
    md("## Risk exposure (RE = P x I)")
    md()
    md("| ID | Risk | Category | P | I | RE | Zone |")
    md("|---|---|---|---|---|---|---|")
    for rid, name, cat, p, i in sorted(RISKS, key=lambda r: -r[3] * r[4]):
        md(f"| {rid} | {name} | {cat} | {p} | {i} | {p * i:.1f} | {risk_zone(p * i)} |")
    md()
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    for row, p in enumerate(PROB_LEVELS, start=1):
        for i in range(1, 6):
            re_ = p * i
            zone = risk_zone(re_)
            color = {"Red": "#e74c3c", "Yellow": "#f5d041", "Green": "#58d68d"}[zone]
            ax.add_patch(plt.Rectangle((i - 0.5, row - 0.5), 1, 1, fc=color, ec="white", alpha=0.85))
            ax.text(i + 0.42, row - 0.4, f"{re_:.1f}", fontsize=7, ha="right", color="#333")
    cells = {}
    for rid, _, _, p, i in RISKS:
        cells.setdefault((PROB_LEVELS.index(p) + 1, i), []).append(rid)
    for (row, i), ids in cells.items():
        ax.text(i, row, "\n".join(ids), ha="center", va="center", fontsize=10, weight="bold")
    ax.set_xticks(range(1, 6))
    ax.set_xticklabels(["1\nVery low", "2\nLow", "3\nMedium", "4\nHigh", "5\nVery high"])
    ax.set_yticks(range(1, 6))
    ax.set_yticklabels([f"{p} " + n for p, n in zip(PROB_LEVELS,
                        ["Rare", "Unlikely", "Possible", "Likely", "Almost certain"])])
    ax.set_xlabel("Impact (I)")
    ax.set_ylabel("Probability (P)")
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_title("Probability-Impact Matrix  (RE = P x I;  Green < 1.0,  Yellow 1.0-1.9,  Red >= 2.0)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "risk_matrix.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- WBS chart
WBS = [  # names and hours as in the WBS dictionary (chapter 2.1)
    ("1.1", "Project\nManagement", [("1.1.1 Concept proposal & charter", 30), ("1.1.2 Planning: WBS, CPM/PERT, Gantt", 25),
                                     ("1.1.3 Estimation & risk register", 20), ("1.1.4 Monitoring & EVM", 10)]),
    ("1.2", "Requirements", [("1.2.1 Stakeholders & TELOS", 15), ("1.2.2 Requirements (SRS)", 25),
                             ("1.2.3 Scope statement", 10)]),
    ("1.3", "Design", [("1.3.1 System architecture", 15), ("1.3.2 Database design", 20), ("1.3.3 UI design", 35)]),
    ("1.4", "Implementation", [("1.4.1 Database implementation", 25), ("1.4.2 Patient module", 60),
                               ("1.4.3 Doctor & schedule module", 45), ("1.4.4 Appointment booking", 80),
                               ("1.4.5 Reports & dashboard", 30)]),
    ("1.5", "Testing", [("1.5.1 Unit tests", 25), ("1.5.2 Integration tests", 20), ("1.5.3 User acceptance test", 10)]),
    ("1.6", "Closure", [("1.6.1 Final IEEE documentation", 25), ("1.6.2 SCM audit", 10), ("1.6.3 Retrospective", 10),
                        ("1.6.4 Presentation & defense", 15)]),
]


def draw_wbs():
    fig, ax = plt.subplots(figsize=(15, 7.5))
    ax.axis("off")
    top = (0.5, 0.92)
    ax.text(*top, "1.0  Clinic Appointment System  (560 h)", ha="center", va="center", fontsize=13, weight="bold",
            bbox=dict(boxstyle="round,pad=0.5", fc="#0f6e8c", ec="none", color="white"), color="white")
    n = len(WBS)
    for k, (code, name, items) in enumerate(WBS):
        x = (k + 0.5) / n
        ax.plot([top[0], x], [0.88, 0.76], color="#888", lw=1)
        total = sum(h for _, h in items)
        ax.text(x, 0.72, f"{code}\n{name}\n({total} h)", ha="center", va="center", fontsize=10, weight="bold",
                bbox=dict(boxstyle="round,pad=0.4", fc="#d6eaf2", ec="#0f6e8c"))
        for j, (it, hours) in enumerate(items):
            y = 0.58 - j * 0.11
            ax.plot([x, x], [0.66, y + 0.03], color="#bbb", lw=0.8)
            ax.text(x, y, it.replace(" ", "\n", 1) + f"\n({hours} h)", ha="center", va="center", fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#9ab"))
    ax.set_xlim(0, 1)
    ax.set_ylim(0.08, 0.98)
    ax.set_title("Work Breakdown Structure (WBS)", fontsize=13, pad=14)
    fig.tight_layout()
    fig.savefig(FIG / "wbs.png", dpi=150)
    plt.close(fig)


def main():
    act, order, succ, finish = pert_cpm()
    md("# Calculation results (generated by tools/pm_calculations.py)")
    md()
    write_pert_tables(act, order, finish)
    write_gantt_table(act, order)
    resource_loading(act, order)
    cocomo(function_points())
    if "--evm" in sys.argv:   # EVM is a Milestone 3 deliverable (status date Week 10)
        evm(act, order, finish)
    draw_network(act, order, succ)
    draw_gantt(act, order)
    risk_matrix()
    draw_wbs()
    (FIG / "results.md").write_text("\n".join(OUT), encoding="utf-8")
    print("\n".join(OUT))


if __name__ == "__main__":
    main()
