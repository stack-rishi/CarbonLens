"""
Compliance PDF Report Generator.
Reuses all constants, color definitions, and table styling from report_service.py.
"""
from __future__ import annotations

import io
import os
import uuid
from datetime import date
from typing import Any

import matplotlib
from backend.models.models import Alert, Organization
from backend.services.compliance_service import (
    _first_of_month,
    _last_of_month,
    get_compliance_status,
)

# Reuse ReportLab setup (same imports/constants as report_service.py)
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import structlog

logger = structlog.get_logger()

# Reuse exact same color constants from report_service.py
COLOR_GREEN = HexColor("#2d7a4f")
COLOR_DARK = HexColor("#0d1a0f")
COLOR_GRAY = HexColor("#5a6b5a")
COLOR_RED = HexColor("#ef4444")
COLOR_ORANGE = HexColor("#f97316")
COLOR_YELLOW = HexColor("#eab308")
COLOR_BG = HexColor("#f8fafc")
COLOR_MINT = HexColor("#e8f2e8")
COLOR_CRITICAL = HexColor("#ef4444")
COLOR_HIGH = HexColor("#f97316")
COLOR_MEDIUM = HexColor("#eab308")
COLOR_LOW = HexColor("#94a3b8")
COLOR_COMPLIANT = HexColor("#22c55e")
COLOR_WARNING = HexColor("#eab308")


def _status_color(status: str) -> HexColor:
    return {
        "compliant": COLOR_COMPLIANT,
        "warning": COLOR_WARNING,
        "critical": COLOR_CRITICAL,
        "unconfigured": COLOR_GRAY,
    }.get(status, COLOR_GRAY)


def _severity_color(severity: str) -> HexColor:
    return {
        "critical": COLOR_CRITICAL,
        "high": COLOR_HIGH,
        "medium": COLOR_MEDIUM,
        "low": COLOR_LOW,
    }.get(severity, COLOR_GRAY)


async def generate_compliance_pdf(
    db: AsyncSession,
    org_id: str | uuid.UUID,
    report_id: str | uuid.UUID,
    period_start: date,
    period_end: date,
) -> str:
    """Generate compliance PDF report. Returns file path relative URL."""
    org_id_uuid = uuid.UUID(str(org_id)) if not isinstance(org_id, uuid.UUID) else org_id

    try:
        safe_id = str(uuid.UUID(str(report_id)))
    except ValueError:
        raise ValueError(f"Invalid report_id format: {report_id}")

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(backend_dir, "static", "reports")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{safe_id}.pdf")

    # Fetch org
    org_result = await db.execute(select(Organization).where(Organization.id == org_id_uuid))
    org = org_result.scalars().first()
    org_name = org.name if org else "Organization"

    # Get compliance status
    compliance_data = await get_compliance_status(org_id_uuid, db)
    comp_status = compliance_data["status"]
    compliance_pct = compliance_data["compliance_pct"]
    sustainability_score = compliance_data["sustainability_score"]
    scope_breakdown = compliance_data["scope_breakdown"]
    current_month = compliance_data["current_month"]
    previous_month = compliance_data["previous_month"]

    # Fetch alerts in period
    period_month_start = _first_of_month(period_start)
    period_month_end = _last_of_month(period_end)
    alerts_result = await db.execute(
        select(Alert)
        .where(
            Alert.org_id == org_id_uuid,
            Alert.period_month >= period_month_start,
            Alert.period_month <= period_month_end,
        )
        .order_by(Alert.triggered_at.desc())
    )
    alerts = alerts_result.scalars().all()

    # Build PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.8 * cm,
        bottomMargin=2.8 * cm,
    )

    story: list[Any] = []

    # Reusable style helpers
    def h1(text: str) -> list[Any]:
        return [
            Paragraph(text, ParagraphStyle("H1", fontSize=18, fontName="Helvetica-Bold",
                                            textColor=COLOR_DARK, spaceAfter=0.4 * cm)),
            HRFlowable(width="100%", thickness=1.5, color=COLOR_GREEN, spaceAfter=0.6 * cm),
        ]

    body_style = ParagraphStyle("Body", fontSize=10, fontName="Helvetica",
                                 textColor=HexColor("#374151"), spaceAfter=0.2 * cm, leading=14)

    # ── PAGE 1: COVER ──────────────────────────────────────────────────────────
    def make_cover() -> list[Any]:
        elements: list[Any] = []
        elements.append(Spacer(1, 3.5 * cm))

        title_style = ParagraphStyle("CoverTitle", fontSize=26, textColor=COLOR_DARK,
                                      spaceAfter=0.3 * cm, fontName="Helvetica-Bold", leading=32)
        subtitle_style = ParagraphStyle("CoverSubtitle", fontSize=12, textColor=COLOR_GRAY,
                                         spaceAfter=1.5 * cm, fontName="Helvetica", leading=16)
        org_style = ParagraphStyle("CoverOrg", fontSize=17, textColor=COLOR_GREEN,
                                    spaceAfter=0.3 * cm, fontName="Helvetica-Bold")
        meta_style = ParagraphStyle("CoverMeta", fontSize=9.5, textColor=COLOR_GRAY,
                                     leading=14, fontName="Helvetica")

        # Status badge rendered as colored text block
        status_color = _status_color(comp_status)
        status_badge = Paragraph(
            f'<font color="#{status_color.hexval()[2:].upper()}" name="Helvetica-Bold">'
            f"  ● {comp_status.upper()}  </font>",
            ParagraphStyle("Badge", fontSize=16, fontName="Helvetica-Bold",
                            textColor=status_color, spaceAfter=0.5 * cm),
        )

        content = [
            Paragraph("Carbon Compliance Report", title_style),
            Paragraph("Automated compliance assessment and alert analysis", subtitle_style),
            Paragraph(org_name, org_style),
            Spacer(1, 0.3 * cm),
            status_badge,
            Paragraph(
                f"<b>Sustainability Score:</b> {sustainability_score:.1f} / 100", meta_style
            ),
            Paragraph(
                f"<b>Compliance:</b> {compliance_pct:.1f}%", meta_style
            ),
            Spacer(1, 0.3 * cm),
            Paragraph(
                f"<b>Reporting Period:</b> {period_start.strftime('%B %Y')} — {period_end.strftime('%B %Y')}",
                meta_style,
            ),
            Paragraph(f"<b>Generated:</b> {date.today().strftime('%d %B %Y')}", meta_style),
        ]

        cover_table = Table([[Spacer(1, 1), content]], colWidths=[5.5 * cm, 11.5 * cm])
        cover_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (1, 0), (1, 0), 0.6 * cm),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(cover_table)
        elements.append(PageBreak())
        return elements

    story.extend(make_cover())

    # ── PAGE 2: EMISSION SUMMARY (scope breakdown table) ──────────────────────
    def make_scope_summary() -> list[Any]:
        elements: list[Any] = []
        elements.extend(h1("Emission Summary"))

        table_data: list[list[Any]] = [[
            Paragraph("<b>Scope</b>", ParagraphStyle("TH", fontSize=10, textColor=white, fontName="Helvetica-Bold")),
            Paragraph("<b>Current (tCO2e)</b>", ParagraphStyle("TH", fontSize=10, textColor=white, fontName="Helvetica-Bold", alignment=2)),
            Paragraph("<b>Threshold (tCO2e)</b>", ParagraphStyle("TH", fontSize=10, textColor=white, fontName="Helvetica-Bold", alignment=2)),
            Paragraph("<b>% of Threshold</b>", ParagraphStyle("TH", fontSize=10, textColor=white, fontName="Helvetica-Bold", alignment=2)),
            Paragraph("<b>Status</b>", ParagraphStyle("TH", fontSize=10, textColor=white, fontName="Helvetica-Bold", alignment=1)),
        ]]

        row_styles: list[Any] = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 9),
        ]

        for i, sb in enumerate(scope_breakdown, 1):
            scope_label = f"Scope {sb['scope']}" if sb["scope"] != "total" else "Total"
            curr_val = sb["current_tco2e"]
            thresh_val = sb["threshold_tco2e"]
            pct = sb["pct_of_threshold"]
            _configured = sb["configured"]

            thresh_str = f"{thresh_val:.2f}" if thresh_val is not None else "—"
            pct_str = f"{pct:.1f}%" if pct is not None else "N/A"

            if pct is not None:
                if pct > 110:
                    row_status = "EXCEEDED"
                    status_color = COLOR_CRITICAL
                elif pct > 90:
                    row_status = "WARNING"
                    status_color = COLOR_YELLOW
                else:
                    row_status = "OK"
                    status_color = COLOR_COMPLIANT
            else:
                row_status = "NOT SET"
                status_color = COLOR_GRAY

            table_data.append([
                Paragraph(scope_label, ParagraphStyle("TD", fontSize=9, textColor=COLOR_DARK, fontName="Helvetica-Bold")),
                Paragraph(f"{curr_val:.2f}", ParagraphStyle("TD", fontSize=9, textColor=COLOR_DARK, alignment=2)),
                Paragraph(thresh_str, ParagraphStyle("TD", fontSize=9, textColor=COLOR_GRAY, alignment=2)),
                Paragraph(pct_str, ParagraphStyle("TD", fontSize=9, textColor=COLOR_DARK, alignment=2)),
                Paragraph(f"<b>{row_status}</b>", ParagraphStyle("TD", fontSize=9, textColor=status_color, alignment=1)),
            ])

        t = Table(table_data, colWidths=[3.5 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm, 3.0 * cm])
        t.setStyle(TableStyle(row_styles))
        elements.append(t)
        elements.append(PageBreak())
        return elements

    story.extend(make_scope_summary())

    # ── PAGE 3: ALERT HISTORY ─────────────────────────────────────────────────
    def make_alert_history() -> list[Any]:
        elements: list[Any] = []
        elements.extend(h1("Alert History"))

        if alerts:
            table_data = [[
                Paragraph("<b>Date</b>", ParagraphStyle("TH", fontSize=9, textColor=white, fontName="Helvetica-Bold")),
                Paragraph("<b>Type</b>", ParagraphStyle("TH", fontSize=9, textColor=white, fontName="Helvetica-Bold")),
                Paragraph("<b>Severity</b>", ParagraphStyle("TH", fontSize=9, textColor=white, fontName="Helvetica-Bold")),
                Paragraph("<b>Title</b>", ParagraphStyle("TH", fontSize=9, textColor=white, fontName="Helvetica-Bold")),
                Paragraph("<b>Status</b>", ParagraphStyle("TH", fontSize=9, textColor=white, fontName="Helvetica-Bold")),
            ]]

            for a in alerts:
                sev_color = _severity_color(a.severity)
                date_str = a.triggered_at.strftime("%d %b %Y") if a.triggered_at else "—"
                atype = a.alert_type.replace("_", " ").title()
                table_data.append([
                    Paragraph(date_str, ParagraphStyle("TD", fontSize=8.5, textColor=COLOR_GRAY)),
                    Paragraph(atype, ParagraphStyle("TD", fontSize=8.5, textColor=COLOR_DARK)),
                    Paragraph(
                        f"<b>{a.severity.upper()}</b>",
                        ParagraphStyle("TD", fontSize=8.5, textColor=sev_color, fontName="Helvetica-Bold")
                    ),
                    Paragraph(a.title[:80], ParagraphStyle("TD", fontSize=8.5, textColor=COLOR_DARK, leading=11)),
                    Paragraph(a.status.title(), ParagraphStyle("TD", fontSize=8.5, textColor=COLOR_GRAY)),
                ])

            t = Table(table_data, colWidths=[2.5 * cm, 3.0 * cm, 2.0 * cm, 7.5 * cm, 2.0 * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f8fafc")]),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("No alerts triggered in this period.", body_style))

        elements.append(PageBreak())
        return elements

    story.extend(make_alert_history())

    # ── PAGE 4: RECOMMENDATIONS ───────────────────────────────────────────────
    def make_recommendations() -> list[Any]:
        elements: list[Any] = []
        elements.extend(h1("Recommendations"))

        # Collect all recommendations from active/acknowledged alerts
        category_groups: dict[str, list[dict[str, Any]]] = {}
        for a in alerts:
            if a.status == "resolved":
                continue
            recs = a.recommendations or []
            for rec in recs:
                cat = rec.get("category", "general")
                if cat not in category_groups:
                    category_groups[cat] = []
                category_groups[cat].append(rec)

        if category_groups:
            for cat, recs in category_groups.items():
                elements.append(
                    Paragraph(
                        f"<b>{cat.replace('_', ' ').title()}</b>",
                        ParagraphStyle("Cat", fontSize=12, fontName="Helvetica-Bold",
                                        textColor=COLOR_GREEN, spaceAfter=0.2 * cm, spaceBefore=0.4 * cm),
                    )
                )
                for rec in recs:
                    title = rec.get("title", "")
                    desc = rec.get("description", "")
                    impact = rec.get("estimated_impact_pct")
                    impact_str = f" (est. {impact:.0f}% impact)" if impact else ""
                    elements.append(
                        Paragraph(
                            f"<b>• {title}</b>{impact_str}",
                            ParagraphStyle("RecTitle", fontSize=10, fontName="Helvetica-Bold",
                                            textColor=COLOR_DARK, spaceAfter=0.1 * cm),
                        )
                    )
                    elements.append(
                        Paragraph(f"  {desc}", ParagraphStyle("RecDesc", fontSize=9,
                                                               textColor=COLOR_GRAY, leading=13,
                                                               spaceAfter=0.3 * cm, leftIndent=0.5 * cm))
                    )
        else:
            elements.append(Paragraph("No active recommendations at this time.", body_style))

        elements.append(PageBreak())
        return elements

    story.extend(make_recommendations())

    # ── PAGE 5: TREND CHART (current vs previous month, grouped by scope) ─────
    def make_trend_chart() -> list[Any]:
        elements: list[Any] = []
        elements.extend(h1("Monthly Trend: Current vs Previous"))

        # collect uniq recs
        scope_labels = ["Scope 1", "Scope 2", "Scope 3"]
        curr_vals = [
            current_month.get("scope1", 0),
            current_month.get("scope2", 0),
            current_month.get("scope3", 0),
        ]
        prev_vals = [
            previous_month.get("scope1", 0),
            previous_month.get("scope2", 0),
            previous_month.get("scope3", 0),
        ]

        import numpy as np

        x = np.arange(len(scope_labels))
        width = 0.35

        fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="white")
        ax.bar(x - width / 2, prev_vals, width, label="Previous Month",
                        color="#94a3b8", alpha=0.85, edgecolor="white")
        ax.bar(x + width / 2, curr_vals, width, label="Current Month",
                        color="#2d7a4f", alpha=0.85, edgecolor="white")

        ax.set_xticks(x)
        ax.set_xticklabels(scope_labels, fontsize=10, color="#0f172a")
        ax.set_ylabel("tCO₂e", fontsize=10, color="#0f172a", weight="bold")
        ax.set_title("Scope Emissions: Current vs Previous Month", fontsize=12,
                      weight="bold", color="#0f172a", pad=10)
        ax.legend(fontsize=9, frameon=True, facecolor="white", edgecolor="#e2e8f0")
        ax.grid(axis="y", linestyle="--", alpha=0.4, color="#cbd5e1")
        ax.set_facecolor("#f8fafc")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#cbd5e1")
        ax.spines["bottom"].set_color("#cbd5e1")

        plt.tight_layout()
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        img_buffer.seek(0)
        elements.append(Image(img_buffer, width=16 * cm, height=9 * cm))
        return elements

    story.extend(make_trend_chart())

    # ── BACKGROUND DECORATORS (same pattern as report_service.py) ─────────────
    def draw_cover(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFillColor(COLOR_DARK)
        canvas.rect(0, 0, 5.0 * cm, 29.7 * cm, fill=1, stroke=0)
        canvas.setFillColor(COLOR_GREEN)
        canvas.rect(5.0 * cm, 0, 0.2 * cm, 29.7 * cm, fill=1, stroke=0)
        canvas.restoreState()

    def draw_later(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(HexColor("#6b7280"))
        canvas.drawString(2 * cm, 28.2 * cm, "CarbonLens — Compliance Report")
        canvas.setStrokeColor(HexColor("#e5e7eb"))
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, 27.9 * cm, 19 * cm, 27.9 * cm)
        canvas.line(2 * cm, 2.2 * cm, 19 * cm, 2.2 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(2 * cm, 1.8 * cm, "CONFIDENTIAL — FOR INTERNAL COMPLIANCE USE")
        canvas.drawRightString(19 * cm, 1.8 * cm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_cover, onLaterPages=draw_later)

    logger.info("compliance_report_generated", report_id=safe_id, path=output_path)
    return f"/static/reports/{safe_id}.pdf"
