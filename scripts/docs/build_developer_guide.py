#!/usr/bin/env python3
"""Render docs/DEVELOPER_GUIDE.md to its matching PDF.

Requires reportlab. Run from an approved environment with the dependency
already installed. This script performs no network access or installation.
"""
from pathlib import Path
import html
import re
import textwrap

import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted,
    Table, TableStyle, Flowable,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "DEVELOPER_GUIDE.md"
OUTPUT = ROOT / "docs" / "DEVELOPER_GUIDE.pdf"
# Embed ReportLab's bundled Vera fonts for portable, consistent rendering.
FONT_DIR = Path(reportlab.__file__).resolve().parent / "fonts"
for name, filename in [
    ("GuideSans", "Vera.ttf"),
    ("GuideSans-Bold", "VeraBd.ttf"),
    ("GuideSans-Italic", "VeraIt.ttf"),
    ("GuideSans-BoldItalic", "VeraBI.ttf"),
    ("GuideCode", "Vera.ttf"),
]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily(
    "GuideSans", normal="GuideSans", bold="GuideSans-Bold",
    italic="GuideSans-Italic", boldItalic="GuideSans-BoldItalic",
)
INK = colors.HexColor("#19332D")
ACCENT = colors.HexColor("#12644F")
MUTED = colors.HexColor("#58716B")
PALE = colors.HexColor("#EDF4F1")
LINE = colors.HexColor("#D9E5DF")
PAGE_W, PAGE_H = A4
MARGIN = 51
WIDTH = PAGE_W - 2 * MARGIN

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    "GuideTitle", fontName="GuideSans-Bold", fontSize=26, leading=30,
    textColor=INK, spaceAfter=14,
))
styles.add(ParagraphStyle(
    "SectionTitle", fontName="GuideSans-Bold", fontSize=20, leading=25,
    textColor=INK, spaceAfter=14,
))
styles.add(ParagraphStyle(
    "SubTitle", fontName="GuideSans-Bold", fontSize=13, leading=17,
    textColor=ACCENT, spaceBefore=9, spaceAfter=7,
))
styles.add(ParagraphStyle(
    "GuideBody", fontName="GuideSans", fontSize=10, leading=14.5,
    textColor=INK, spaceAfter=8, splitLongWords=True,
))
styles.add(ParagraphStyle(
    "GuideList", parent=styles["GuideBody"], leftIndent=12,
    firstLineIndent=-10, spaceAfter=6,
))
styles.add(ParagraphStyle(
    "GuideCode", fontName="GuideCode", fontSize=8.3, leading=11.5,
    textColor=INK, backColor=PALE, borderPadding=9,
    spaceBefore=5, spaceAfter=12,
))
styles.add(ParagraphStyle(
    "Cell", fontName="GuideSans", fontSize=8.7, leading=12,
    textColor=INK, spaceAfter=0, splitLongWords=True,
))
styles.add(ParagraphStyle(
    "HeaderCell", parent=styles["Cell"], fontName="GuideSans-Bold",
    textColor=colors.white,
))

def inline(text):
    text = html.escape(text, quote=True)
    text = re.sub(r"`([^`]+)`",
                  r'<font name="GuideCode" size="8.5">\1</font>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    def link(match):
        label, target = match.groups()
        if target.startswith(("https://", "http://")):
            return '<link href="' + target + '" color="#12644F">' + label + "</link>"
        return label + ' <font name="GuideCode" size="8">(' + target + ")</font>"
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    return text

class ArchitectureDiagram(Flowable):
    """Vector rendering of the architecture Mermaid figure in the guide."""
    def __init__(self):
        Flowable.__init__(self)
        self.width = WIDTH
        self.height = 270

    def draw(self):
        c = self.canv
        def box(x, y, width, title, subtitle):
            c.setFillColor(PALE)
            c.setStrokeColor(LINE)
            c.roundRect(x, y, width, 35, 6, fill=1, stroke=1)
            c.setFillColor(INK)
            c.setFont("GuideSans-Bold", 10)
            c.drawCentredString(x + width / 2, y + 21, title)
            c.setFont("GuideSans", 8)
            c.setFillColor(MUTED)
            c.drawCentredString(x + width / 2, y + 9, subtitle)
        def arrow(x1, y1, x2, y2):
            c.setStrokeColor(ACCENT)
            c.setFillColor(ACCENT)
            c.setLineWidth(1.3)
            c.line(x1, y1, x2, y2)
            import math
            angle = math.atan2(y2-y1, x2-x1)
            p = c.beginPath()
            p.moveTo(x2, y2)
            for delta in (2.65, -2.65):
                p.lineTo(x2 + 6 * math.cos(angle+delta),
                         y2 + 6 * math.sin(angle+delta))
            p.close()
            c.drawPath(p, fill=1, stroke=0)
        left, lw, right, rw = 12, 205, 270, 200
        rows = [
            (210, "Next.js", "Pages and interaction"),
            (166, "Same-origin proxy", "/api/v1 to a fixed backend"),
            (122, "Django REST API", "Authenticated requests"),
            (78, "Domain services", "Permissions and business rules"),
            (34, "PostgreSQL", "Business data and transactions"),
        ]
        c.setFillColor(MUTED)
        c.setFont("GuideSans", 9)
        c.drawCentredString(left+lw/2, 258, "Customer / employee")
        arrow(left+lw/2, 252, left+lw/2, 246)
        for y, title, subtitle in rows:
            box(left, y, lw, title, subtitle)
        for top, bottom in zip(rows, rows[1:]):
            arrow(left+lw/2, top[0], left+lw/2, bottom[0]+35)
        box(right, 122, rw, "AI adapter + validator", "Grounded recommendations")
        box(right, 78, rw, "Scoped tools", "Act with the caller's permissions")
        arrow(left+lw, 139.5, right, 139.5)
        arrow(right+rw/2, 122, right+rw/2, 113)
        arrow(right, 95.5, left+lw, 95.5)
        c.setFillColor(MUTED)
        c.setFont("GuideSans", 8)
        c.drawCentredString(right+rw/2, 48, "The AI uses domain services.")
        c.drawCentredString(right+rw/2, 36, "It does not write directly to the database.")

def make_table(lines):
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in lines]
    rows = [row for row in rows if not all(
        re.fullmatch(r":?-{3,}:?", cell or "") for cell in row)]
    count = len(rows[0])
    first = rows[0][0]
    if count == 2:
        ratio = {"Path": .48, "Command": .48, "Agent": .30,
                 "Owner": .25, "Change": .30, "Symptom": .36}.get(first, .35)
        widths = [WIDTH * ratio, WIDTH * (1-ratio)]
    else:
        widths = [WIDTH / count] * count
    data = [[Paragraph(inline(cell), styles["HeaderCell" if i == 0 else "Cell"])
             for cell in row] for i, row in enumerate(rows)]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), ACCENT),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, PALE]),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 9),
        ("RIGHTPADDING", (0,0), (-1,-1), 9),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LINEBELOW", (0,-1), (-1,-1), .5, LINE),
    ]))
    return table

def build_story(markdown):
    story, paragraph = [], []
    lines = markdown.splitlines()
    i, first_title = 0, True
    def flush():
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), styles["GuideBody"]))
            paragraph.clear()
    while i < len(lines):
        line = lines[i]
        if line == "<!-- pagebreak -->":
            flush()
            story.append(PageBreak())
        elif line.startswith("```"):
            flush()
            language = line[3:].strip()
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            if language == "mermaid":
                story.append(ArchitectureDiagram())
            else:
                wrapped = []
                for entry in code:
                    wrapped.extend(textwrap.wrap(
                        entry, width=90, replace_whitespace=False,
                        drop_whitespace=False, break_long_words=True,
                        break_on_hyphens=False) or [""])
                story.append(Preformatted("\n".join(wrapped), styles["GuideCode"]))
        elif line.startswith("|"):
            flush()
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            story.append(make_table(table_lines))
            story.append(Spacer(1, 10))
            continue
        elif line.startswith("# "):
            flush()
            style = "GuideTitle" if first_title else "SectionTitle"
            story.append(Paragraph(inline(line[2:]), styles[style]))
            first_title = False
        elif line.startswith("## "):
            flush()
            story.append(Paragraph(inline(line[3:]), styles["SubTitle"]))
        elif line.startswith("### "):
            flush()
            story.append(Paragraph(inline(line[4:]), styles["SubTitle"]))
        elif line.startswith("- "):
            flush()
            story.append(Paragraph("- " + inline(line[2:]), styles["GuideList"]))
        elif re.match(r"^\d+\. ", line):
            flush()
            story.append(Paragraph(inline(line), styles["GuideList"]))
        elif not line.strip():
            flush()
        elif line.startswith("<!--"):
            flush()
        else:
            paragraph.append(line.strip())
        i += 1
    flush()
    return story

def decorate(canvas, document):
    canvas.saveState()
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_H-9, PAGE_W, 9, fill=1, stroke=0)
    canvas.setFont("GuideSans-Bold", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, PAGE_H-32, "HARDWARE STORE PLATFORM")
    canvas.setFont("GuideSans", 8)
    canvas.drawRightString(PAGE_W-MARGIN, PAGE_H-32, "DEVELOPER PLAYBOOK")
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 42, PAGE_W-MARGIN, 42)
    canvas.setFillColor(MUTED)
    canvas.setFont("GuideSans", 8)
    canvas.drawString(MARGIN, 27, "2026-10-21  |  Editable source: docs/DEVELOPER_GUIDE.md")
    canvas.drawRightString(PAGE_W-MARGIN, 27, str(document.page))
    canvas.restoreState()

def main():
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=57, bottomMargin=57, title="Hardware Store Platform - Developer Guide",
        author="Hardware Store Platform contributors",
        subject="Architecture, Claude plugins and Linear ticket implementation",
    )
    doc.build(build_story(SOURCE.read_text()), onFirstPage=decorate, onLaterPages=decorate)
    print("Created " + str(OUTPUT))

if __name__ == "__main__":
    main()
