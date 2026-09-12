"""Generate frontend-grounded Infra Monitor UML use-case diagrams."""

from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "infra_monitor_frontend_use_case_diagrams.pdf"
W, H = landscape(A4)

INK = colors.HexColor("#162033")
MUTED = colors.HexColor("#60708A")
BLUE = colors.HexColor("#1769E0")
PALE = colors.HexColor("#EEF5FF")
GREEN = colors.HexColor("#198754")
ORANGE = colors.HexColor("#D97706")
LINE = colors.HexColor("#B9C6D8")
SYSTEM = colors.HexColor("#F2F4F7")


def wrapped(c: canvas.Canvas, text: str, x: float, y: float, width: float,
            font="Helvetica", size=9, color=INK, leading=None, align="left"):
    leading = leading or size * 1.25
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if stringWidth(trial, font, size) <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    c.setFont(font, size)
    c.setFillColor(color)
    for i, line in enumerate(lines):
        tx = x if align == "left" else x + (width - stringWidth(line, font, size)) / 2
        c.drawString(tx, y - i * leading, line)
    return len(lines) * leading


def header(c, number, title, subtitle):
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(34, H - 35, f"{number}. {title}")
    wrapped(c, subtitle, 34, H - 55, W - 68, size=8.5, color=MUTED)
    c.setStrokeColor(LINE)
    c.line(34, H - 70, W - 34, H - 70)


def stick_actor(c, x, y, label, scale=1.0):
    """Actual human actor only."""
    c.setStrokeColor(INK)
    c.setLineWidth(1.25)
    c.circle(x, y + 23 * scale, 7 * scale, stroke=1, fill=0)
    c.line(x, y + 16 * scale, x, y - 4 * scale)
    c.line(x - 12 * scale, y + 8 * scale, x + 12 * scale, y + 8 * scale)
    c.line(x, y - 4 * scale, x - 10 * scale, y - 19 * scale)
    c.line(x, y - 4 * scale, x + 10 * scale, y - 19 * scale)
    wrapped(c, label, x - 48, y - 30, 96, font="Helvetica-Bold", size=8,
            align="center")


def system_actor(c, x, y, label):
    """Non-human secondary actor rendered as a component box."""
    c.setFillColor(SYSTEM)
    c.setStrokeColor(MUTED)
    c.roundRect(x - 53, y - 19, 106, 38, 5, fill=1, stroke=1)
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x, y + 7, "«SYSTEM»")
    wrapped(c, label, x - 48, y - 5, 96, font="Helvetica", size=8,
            align="center")


def use_case(c, x, y, label, restricted=False):
    c.setFillColor(colors.HexColor("#FFF7ED") if restricted else PALE)
    c.setStrokeColor(ORANGE if restricted else BLUE)
    c.setLineWidth(1.1)
    c.ellipse(x - 75, y - 22, x + 75, y + 22, fill=1, stroke=1)
    wrapped(c, label, x - 65, y + 4, 130, font="Helvetica-Bold", size=7.6,
            align="center", leading=9)


def association(c, x1, y1, x2, y2, dashed=False):
    c.saveState()
    c.setStrokeColor(MUTED)
    c.setLineWidth(.8)
    if dashed:
        c.setDash(4, 3)
    c.line(x1, y1, x2, y2)
    c.restoreState()


def generalization(c, x1, y1, x2, y2):
    """UML generalization: specialized actor points to generalized User."""
    c.setStrokeColor(INK)
    c.setLineWidth(1)
    angle = math.atan2(y2 - y1, x2 - x1)
    tip_x, tip_y = x2, y2
    base_x = tip_x - 12 * math.cos(angle)
    base_y = tip_y - 12 * math.sin(angle)
    perp_x, perp_y = 6 * math.sin(angle), -6 * math.cos(angle)
    c.line(x1, y1, base_x, base_y)
    p = c.beginPath()
    p.moveTo(tip_x, tip_y)
    p.lineTo(base_x + perp_x, base_y + perp_y)
    p.lineTo(base_x - perp_x, base_y - perp_y)
    p.close()
    c.setFillColor(colors.white)
    c.drawPath(p, fill=1, stroke=1)


def boundary(c, title):
    x, y, w, h = 210, 55, 470, 420
    c.setStrokeColor(LINE)
    c.setLineWidth(1.3)
    c.roundRect(x, y, w, h, 8, fill=0, stroke=1)
    c.setFillColor(colors.white)
    c.rect(x + 15, y + h - 8, 170, 18, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 20, y + h - 2, f"INFRA MONITOR — {title.upper()}")


def roles(c):
    """One generalized User with Engineer/Admin/Owner specializations, all left."""
    ux, uy = 110, 420
    stick_actor(c, ux, uy, "User")
    positions = [(110, 295, "Engineer"), (110, 195, "Admin"), (110, 95, "Owner")]
    for x, y, label in positions:
        stick_actor(c, x, y, label, .85)
    # Put the generalization tree to the left of the actors. Associations leave
    # to the right, so inheritance and participation lines never intersect.
    trunk_x = 35
    c.setStrokeColor(INK)
    c.setLineWidth(1)
    for x, y, _ in positions:
        c.line(x - 13, y + 5, trunk_x, y + 5)
    c.line(trunk_x, positions[-1][1] + 5, trunk_x, uy + 5)
    generalization(c, trunk_x, uy + 5, ux - 13, uy + 5)
    return {"User": (ux, uy), **{label: (x, y) for x, y, label in positions}}


def diagram(c, number, title, subtitle, cases, links, systems=()):
    boundary(c, f"{number}. {title}")
    actors = roles(c)
    points = {}
    # A single use-case column avoids lines passing through neighboring
    # ellipses. Case order follows the actor hierarchy from User to Owner.
    count = len(cases)
    top, bottom = 425, 85
    rows = [top - i * ((top - bottom) / max(count - 1, 1)) for i in range(count)]
    for i, item in enumerate(cases):
        label, restricted = item if isinstance(item, tuple) else (item, False)
        x, y = 455, rows[i]
        points[label] = (x, y)
        use_case(c, x, y, label, restricted)
    sys_points = {}
    sy = 385
    for name in systems:
        sys_points[name] = (750, sy)
        system_actor(c, 750, sy, name)
        sy -= 95
    # With one ordered case column, these associations fan without crossing an
    # ellipse, actor label, generalization line, or another actor figure.
    for actor, target in links:
        ax, ay = actors.get(actor, sys_points.get(actor))
        tx, ty = points[target]
        if ax < 210:
            association(c, ax + 18, ay + 5, tx - 75, ty)
        else:
            association(c, ax - 53, ay, tx + 75, ty)
    c.showPage()


def cover(c):
    c.setFillColor(INK)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(58, H - 120, "Infra Monitor")
    c.setFont("Helvetica", 19)
    c.drawString(58, H - 154, "Frontend-based use-case diagrams")
    c.setFillColor(colors.HexColor("#AFCBFF"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(58, H - 200, "IMPLEMENTED FLUTTER SURFACE • 10 SEPTEMBER 2026")
    wrapped(c, "Scope: use cases visible and actionable in the Flutter frontend. Backend-only endpoints, internal implementation details, and speculative capabilities are excluded.",
            58, H - 245, 560, size=11, color=colors.white, leading=16)
    c.setFillColor(colors.HexColor("#243550"))
    c.roundRect(58, 82, 700, 105, 8, fill=1, stroke=0)
    wrapped(c, "UML conventions", 78, 160, 150, font="Helvetica-Bold", size=11,
            color=colors.white)
    wrapped(c, "User is the generalized human actor. Engineer, Admin, and Owner specialize User and appear on the left. Non-human integrations appear as «SYSTEM» boxes on the right. Orange use cases are role-restricted actions.",
            78, 137, 640, size=9, color=colors.white, leading=14)
    c.showPage()


def matrix_page(c):
    header(c, 9, "Frontend access summary",
           "Dominant controls visible in the Flutter client; organization and resource visibility still apply.")
    rows = [
        ("Capability", "Engineer", "Admin", "Owner"),
        ("View overview, servers, incidents, and AI", "Yes", "Yes", "Yes"),
        ("Enroll a server", "No", "No", "Yes"),
        ("View host-wide metrics", "No", "No", "Yes"),
        ("Assign incidents/anomalies", "View only", "Yes", "Yes"),
        ("Manage service admins", "No", "No", "Yes"),
        ("List members", "No", "Yes", "Yes"),
        ("Approve/reject join requests", "No", "No", "Yes"),
        ("Change member roles", "No", "No", "Yes"),
    ]
    x0, y0 = 50, H - 110
    widths = [390, 115, 115, 115]
    rh = 38
    for r, row in enumerate(rows):
        x = x0
        c.setFillColor(INK if r == 0 else colors.white)
        c.setStrokeColor(LINE)
        for col, value in enumerate(row):
            c.rect(x, y0 - (r + 1) * rh, widths[col], rh, fill=1, stroke=1)
            c.setFillColor(colors.white if r == 0 else INK)
            c.setFont("Helvetica-Bold" if r == 0 or col == 0 else "Helvetica", 8.5)
            c.drawString(x + 8, y0 - r * rh - 24, value)
            x += widths[col]
            c.setFillColor(INK if r == 0 else colors.white)
    c.showPage()


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(W, H), pageCompression=1)
    c.setTitle("Infra Monitor — Frontend-based use-case diagrams")
    c.setAuthor("Infra Monitor project")
    diagram(c, 1, "Identity and account access",
            "Public and signed-in account actions exposed by Flutter routes.",
            ["Register account", "Verify email", "Sign in", "Recover / reset password",
             "Manage preferences", "Sign out"],
            [("User", x) for x in ["Register account", "Verify email", "Sign in",
                                          "Recover / reset password", "Manage preferences", "Sign out"]]
            + [("Email service", "Verify email"),
               ("Email service", "Recover / reset password")],
            ["Email service"])

    diagram(c, 2, "Organization and membership",
            "User is generalized; Engineer, Admin, and Owner specialize User.",
            ["Search organizations", "Request to join", "Switch organization",
             ("List members", True), ("Create organization", True),
             ("Approve / reject join request", True), ("Change member role", True)],
            [("User", "Search organizations"), ("User", "Request to join"),
             ("User", "Switch organization"), ("Owner", "Create organization"),
             ("Admin", "List members"), ("Owner", "List members"),
             ("Owner", "Approve / reject join request"), ("Owner", "Change member role")])

    diagram(c, 3, "Server enrollment",
            "Owner-only actions exposed by the Flutter Add Server flow.",
            [("Enter server details", True), ("Generate install command", True),
             "Copy install command", "Enroll host with command", "Finish enrollment"],
            [("Owner", "Enter server details"),
             ("Owner", "Generate install command"), ("Owner", "Copy install command"),
             ("Owner", "Finish enrollment"),
             ("Host agent", "Enroll host with command")],
            ["Host agent"])

    diagram(c, 4, "Overview dashboard",
            "Operational cards and panels available on the Flutter Overview page.",
            ["View operational overview", "View fleet status", "View active incidents",
             "View alerts", "View anomalies needing attention", "View platform health"],
            [("User", x) for x in ["View operational overview", "View fleet status",
                                          "View active incidents", "View alerts",
                                          "View anomalies needing attention", "View platform health"]])

    diagram(c, 5, "Servers, services and metrics",
            "Server and service read paths reflect the role visibility enforced by the client.",
            ["List / filter servers", "View server detail", "View service health",
             "View anomalies", "Explore host metric history", ("Assign service admins", True)],
            [("User", "List / filter servers"), ("User", "View server detail"),
             ("User", "View service health"), ("Owner", "Explore host metric history"),
             ("User", "View anomalies"), ("Owner", "Assign service admins")])

    diagram(c, 6, "Anomalies and assignments",
            "Only anomaly evidence and assignment controls present in the frontend are included.",
            ["List visible anomalies", "Inspect anomaly evidence", "Open anomaly in AI assistant",
             "View anomaly assignment", ("Assign / reassign anomaly — Admin / Owner", True),
             ("Mark anomaly resolved — Admin / Owner", True)],
            [("User", "List visible anomalies"), ("User", "Inspect anomaly evidence"),
             ("User", "Open anomaly in AI assistant"),
             ("Engineer", "View anomaly assignment"),
             ("Admin", "Assign / reassign anomaly — Admin / Owner"),
             ("Admin", "Mark anomaly resolved — Admin / Owner")])

    diagram(c, 7, "Incident response",
            "Actions available on the Flutter Incidents page.",
            ["List / search incidents", "Filter / sort incidents", "Acknowledge incident",
             "Bulk acknowledge", "View incident assignment",
             ("Assign / reassign incident — Admin / Owner", True)],
            [("User", "List / search incidents"), ("User", "Filter / sort incidents"),
             ("User", "Acknowledge incident"), ("User", "Bulk acknowledge"),
             ("Engineer", "View incident assignment"),
             ("Admin", "Assign / reassign incident — Admin / Owner")])

    diagram(c, 8, "AI operations assistant",
            "User-visible anomaly context, evidence, conversation, and streaming interactions.",
            ["Select anomaly context", "Inspect stored evidence", "Ask operational question",
             "Receive streamed response", "Review conversation messages", "Retry assistant"],
            [("User", x) for x in ["Select anomaly context", "Inspect stored evidence",
                                          "Ask operational question", "Receive streamed response",
                                          "Review conversation messages", "Retry assistant"]]
            + [("Gemini AI", "Receive streamed response")],
            ["Gemini AI"])

    c.save()
    print(OUT)


if __name__ == "__main__":
    build()
