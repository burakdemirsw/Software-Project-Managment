"""Convert the Markdown documents in docs/M1_*, docs/M2_*, docs/M3_* to Word (.docx).

Each Word file gets a cover page (university, course, team, milestone) and a
table of contents field. Supported Markdown: headings, paragraphs, **bold**,
*italic*, `code`, bullet and numbered lists, pipe tables, images, code blocks.

Run:  python tools/build_docx.py
Output: docs/Word/<same name>.docx
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "Word"

TEAM = [
    ("Burak Demir", "20091000008", "Project Manager, Backend"),
    ("Davut Ayfer", "20091000054", "Database, Doctor module"),
    ("Enes Küçükkaya", "22091000275", "UI, Patient module, Dashboard"),
    ("Alper Keskin", "24352525053", "Testing, Documentation"),
]
ACCENT = RGBColor(0x0F, 0x6E, 0x8C)
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)")


def add_runs(par, text):
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            par.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            r = par.add_run(part[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            par.add_run(part[1:-1]).italic = True
        else:
            par.add_run(part)


def shade(cell, hex_color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def add_table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, body = cells[0], [r for r in cells[2:]]
    ncol = len(header)
    table = doc.add_table(rows=1, cols=ncol)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = table.rows[0].cells[i]
        c.text = ""
        add_runs(c.paragraphs[0], h)
        for r in c.paragraphs[0].runs:
            r.bold = True
        shade(c, "D6EAF2")
    for row in body:
        cells_ = table.add_row().cells
        for i in range(ncol):
            cells_[i].text = ""
            add_runs(cells_[i].paragraphs[0], row[i] if i < len(row) else "")
    for row in table.rows:
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph()


def add_toc(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    for tag, text in (("begin", None), (None, 'TOC \\o "1-3" \\h \\z \\u'), ("separate", None), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
            run._r.append(el)
            if tag == "separate":
                t = OxmlElement("w:t")
                t.text = "Right-click here and choose 'Update Field' to build the table of contents."
                run._r.append(t)
        else:
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = text
            run._r.append(instr)


def cover(doc, title, meta):
    doc.add_paragraph()
    logo = DOCS / "figures" / "logo.png"
    if logo.exists():
        doc.add_picture(str(logo), width=Cm(2.6))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for text, size, bold in (("HALİÇ UNIVERSITY", 20, True), ("Faculty of Engineering", 13, False),
                             ("Department of Software Engineering", 13, False)):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        r.font.size = Pt(size)
        r.bold = bold
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("SEN4100 – Software Project Management")
    r.font.size = Pt(14)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Team Project: Clinic Appointment System (CAS)")
    r.font.size = Pt(13)
    r.italic = True
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title)
    r.font.size = Pt(24)
    r.bold = True
    r.font.color.rgb = ACCENT
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(meta.get("Milestone", ""))
    r.font.size = Pt(13)
    doc.add_paragraph()
    t = doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(("Name", "Student No", "Role")):
        t.rows[0].cells[i].text = h
        t.rows[0].cells[i].paragraphs[0].runs[0].bold = True
        shade(t.rows[0].cells[i], "D6EAF2")
    for row in TEAM:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    doc.add_paragraph()
    for label in ("Instructor", "Version / Date"):
        if meta.get(label):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(f"{label}: ").bold = True
            p.add_run(meta[label])
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def read_meta_table(lines, i):
    """Read the '| | |' metadata table at the top of each document."""
    meta = {}
    while i < len(lines) and lines[i].startswith("|"):
        cols = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if len(cols) >= 2 and cols[0].startswith("**"):
            meta[cols[0].strip("*")] = cols[1]
        i += 1
    return meta, i


def convert(md_path):
    lines = md_path.read_text(encoding="utf-8").splitlines()
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    for lvl, size in ((1, 18), (2, 14), (3, 12)):
        hs = doc.styles[f"Heading {lvl}"]
        hs.font.color.rgb = ACCENT
        hs.font.size = Pt(size)

    title = md_path.stem
    i = 0
    while i < len(lines) and not lines[i].startswith("# "):
        i += 1
    if i < len(lines):
        title = lines[i][2:].strip()
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    meta = {}
    if i < len(lines) and lines[i].startswith("| |"):
        meta, i = read_meta_table(lines, i)
    cover(doc, title, meta)
    doc.add_heading("Contents", level=1)
    in_code = False
    for ln in lines[i:]:
        if ln.strip().startswith("```"):
            in_code = not in_code
        hm = None if in_code else re.match(r"^(##|###)\s+(.*)", ln.strip())
        if hm:
            p = doc.add_paragraph(hm.group(2).replace("**", ""))
            p.paragraph_format.space_after = Pt(1)
            if hm.group(1) == "###":
                p.paragraph_format.left_indent = Cm(0.8)
                p.runs[0].font.size = Pt(10)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    para_buf = []

    def flush():
        if para_buf:
            p = doc.add_paragraph()
            add_runs(p, " ".join(s.strip() for s in para_buf))
            para_buf.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            flush()
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            p = doc.add_paragraph()
            r = p.add_run("\n".join(code))
            r.font.name = "Consolas"
            r.font.size = Pt(8)
            p.paragraph_format.left_indent = Cm(0.4)
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            flush()
            doc.add_heading(m.group(2).replace("**", ""), level=min(len(m.group(1)), 3))
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            if len(rows) >= 2:
                add_table(doc, rows)
            continue
        elif re.match(r"^!\[.*\]\(.*\)", s):
            flush()
            cap, src = re.match(r"^!\[(.*)\]\((.*)\)", s).groups()
            img = (md_path.parent / src).resolve()
            if img.exists():
                doc.add_picture(str(img), width=Cm(16.5))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                cp = doc.add_paragraph()
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = cp.add_run(cap)
                r.italic = True
                r.font.size = Pt(9)
        elif re.match(r"^\s*[-*]\s+", line):
            flush()
            level = (len(line) - len(line.lstrip())) // 2
            p = doc.add_paragraph(style="List Bullet 2" if level else "List Bullet")
            add_runs(p, re.sub(r"^\s*[-*]\s+", "", line))
        elif re.match(r"^\s*\d+[.)]\s+", line):
            flush()
            num = re.match(r"^\s*(\d+)", line).group(1)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.9)
            p.paragraph_format.first_line_indent = Cm(-0.6)
            p.paragraph_format.space_after = Pt(2)
            p.add_run(f"{num}.\t")
            add_runs(p, re.sub(r"^\s*\d+[.)]\s+", "", line))
        elif s in ("---", "***"):
            flush()
        elif not s:
            flush()
        elif s.startswith(">"):
            flush()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.8)
            add_runs(p, s.lstrip("> "))
            for r in p.runs:
                r.italic = True
        else:
            para_buf.append(s)
        i += 1
    flush()

    sub = OUT if md_path.parent == DOCS else OUT / md_path.parent.name
    out = sub / (md_path.stem + ".docx")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out


def main():
    files = sorted(DOCS.glob("M*_Milestone*/*.md")) + sorted(DOCS.glob("*.md"))
    for f in files:
        print("written:", convert(f).relative_to(ROOT))


if __name__ == "__main__":
    main()
