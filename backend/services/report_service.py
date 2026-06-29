import io
import os
import uuid
from datetime import date
from typing import Any

import matplotlib
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
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
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import EmissionRecord, Organization, Supplier

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import structlog

logger = structlog.get_logger()

COLOR_GREEN = HexColor('#22c55e')
COLOR_DARK = HexColor('#0a0a0a')
COLOR_GRAY = HexColor('#6b7280')
COLOR_RED = HexColor('#ef4444')
COLOR_ORANGE = HexColor('#f97316')
COLOR_YELLOW = HexColor('#eab308')
COLOR_BG = HexColor('#f9fafb')

class ReportService:
    @staticmethod
    async def generate_pdf_report(
        db: AsyncSession,
        org_id: str | uuid.UUID,
        period_start: date,
        period_end: date,
        report_id: str | uuid.UUID | None = None
    ) -> str:
        """Generate GHG Protocol aligned PDF report. Returns file path relative url."""
        if report_id is None:
            report_id = str(uuid.uuid4())
        
        # SECURITY FIX: Sanitize report_id to prevent path traversal
        try:
            safe_id = str(uuid.UUID(str(report_id)))  # Validates it's a proper UUID
        except ValueError:
            raise ValueError(f"Invalid report_id format: {report_id}")
            
        output_dir = "backend/static/reports"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{safe_id}.pdf")
        
        # Fetch all data needed
        org_result = await db.execute(select(Organization).where(Organization.id == org_id))
        org = org_result.scalars().first()
        
        # Emission totals by scope
        emission_data = await db.execute(
            select(
                EmissionRecord.scope,
                func.sum(EmissionRecord.amount_tco2e).label('total')
            ).where(
                EmissionRecord.org_id == org_id,
                EmissionRecord.period_start >= period_start,
                EmissionRecord.period_end <= period_end
            ).group_by(EmissionRecord.scope)
        )
        scope_totals = {row.scope: row.total for row in emission_data}
        
        # Monthly breakdown for charts
        monthly_data = await db.execute(
            select(
                func.date_trunc('month', EmissionRecord.period_start).label('month'),
                EmissionRecord.scope,
                func.sum(EmissionRecord.amount_tco2e).label('total')
            ).where(
                EmissionRecord.org_id == org_id,
                EmissionRecord.period_start >= period_start,
                EmissionRecord.period_end <= period_end
            ).group_by('month', EmissionRecord.scope)
            .order_by('month')
        )
        monthly_rows = monthly_data.fetchall()
        
        # Top suppliers
        supplier_data = await db.execute(
            select(
                Supplier.name,
                Supplier.sector,
                Supplier.esg_score,
                func.sum(EmissionRecord.amount_tco2e).label('total')
            ).join(EmissionRecord, EmissionRecord.supplier_id == Supplier.id)
            .where(
                EmissionRecord.org_id == org_id,
                EmissionRecord.period_start >= period_start,
                EmissionRecord.period_end <= period_end
            ).group_by(Supplier.id, Supplier.name, Supplier.sector, Supplier.esg_score)
            .order_by(desc('total'))
            .limit(10)
        )
        top_suppliers = supplier_data.fetchall()
        
        grand_total = sum(scope_totals.values()) or 0
        
        # Build PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        

        story = []
        
        # --- PAGE 1: COVER ---
        def make_cover() -> list[Any]:
            elements = []
            elements.append(Spacer(1, 3*cm))
            
            # Green accent bar
            elements.append(HRFlowable(
                width="100%", thickness=4, color=COLOR_GREEN, spaceAfter=0.5*cm
            ))
            
            # Title
            title_style = ParagraphStyle('Title',
                fontSize=28, textColor=COLOR_DARK, spaceAfter=0.3*cm,
                fontName='Helvetica-Bold')
            elements.append(Paragraph("Greenhouse Gas", title_style))
            elements.append(Paragraph("Emissions Report", title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Org name
            org_style = ParagraphStyle('OrgName',
                fontSize=16, textColor=COLOR_GREEN, spaceAfter=0.2*cm,
                fontName='Helvetica-Bold')
            elements.append(Paragraph(org.name if org else "Organization", org_style))
            
            # Period
            period_style = ParagraphStyle('Period',
                fontSize=12, textColor=COLOR_GRAY, spaceAfter=2*cm,
                fontName='Helvetica')
            period_str = f"{period_start.strftime('%B %Y')} — {period_end.strftime('%B %Y')}"
            elements.append(Paragraph(period_str, period_style))
            
            elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_GRAY))
            elements.append(Spacer(1, 1*cm))
            
            # Summary stats box
            total_scope1 = scope_totals.get('1', 0)
            total_scope2 = scope_totals.get('2', 0)
            total_scope3 = scope_totals.get('3', 0)
            
            stats_data = [
                ['Metric', 'Value'],
                ['Total Scope 1 Emissions', f"{total_scope1:,.1f} tCO₂e"],
                ['Total Scope 2 Emissions', f"{total_scope2:,.1f} tCO₂e"],
                ['Total Scope 3 Emissions', f"{total_scope3:,.1f} tCO₂e"],
                ['TOTAL GHG EMISSIONS', f"{grand_total:,.1f} tCO₂e"],
            ]
            stats_table = Table(stats_data, colWidths=[10*cm, 6*cm])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), COLOR_DARK),
                ('TEXTCOLOR', (0,0), (-1,0), white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 11),
                ('BACKGROUND', (0,4), (-1,4), COLOR_GREEN),
                ('TEXTCOLOR', (0,4), (-1,4), white),
                ('FONTNAME', (0,4), (-1,4), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('ROWBACKGROUNDS', (0,1), (-1,3), [COLOR_BG, white]),
                ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
                ('PADDING', (0,0), (-1,-1), 8),
                ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ]))
            elements.append(stats_table)
            elements.append(Spacer(1, 2*cm))
            
            # Footer
            footer_style = ParagraphStyle('Footer',
                fontSize=9, textColor=COLOR_GRAY, fontName='Helvetica',
                alignment=TA_CENTER)
            elements.append(Paragraph(
                "This report is aligned with the GHG Protocol Corporate Standard. "
                f"Generated by CarbonLens on {date.today().strftime('%d %B %Y')}.",
                footer_style
            ))
            elements.append(PageBreak())
            return elements
        
        story.extend(make_cover())
        
        # --- PAGE 2: SCOPE BREAKDOWN WITH PIE CHART ---
        def make_scope_breakdown() -> list[Any]:
            elements = []
            h1 = ParagraphStyle('H1', fontSize=18, fontName='Helvetica-Bold',
                textColor=COLOR_DARK, spaceAfter=0.5*cm)
            body = ParagraphStyle('Body', fontSize=10, fontName='Helvetica',
                textColor=COLOR_GRAY, spaceAfter=0.3*cm, leading=14)
            
            elements.append(Paragraph("Scope Emissions Breakdown", h1))
            elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_GREEN))
            elements.append(Spacer(1, 0.5*cm))
            
            # Pie chart
            fig, ax = plt.subplots(figsize=(5, 3.5), facecolor='white')
            scope_labels = ['Scope 1', 'Scope 2', 'Scope 3']
            scope_values = [
                scope_totals.get('1', 0.001),
                scope_totals.get('2', 0.001),
                scope_totals.get('3', 0.001)
            ]
            colors_list = ['#ef4444', '#f97316', '#eab308']
            wedges, texts, autotexts = ax.pie(
                scope_values, labels=scope_labels, colors=colors_list,
                autopct='%1.1f%%', startangle=90,
                wedgeprops={'width': 0.6, 'edgecolor': 'white', 'linewidth': 2}
            )
            for autotext in autotexts:
                autotext.set_fontsize(9)
            ax.set_title(f'Total: {grand_total:,.1f} tCO₂e', fontsize=11, pad=10)
            plt.tight_layout()
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight',
                        facecolor='white')
            plt.close()
            img_buffer.seek(0)
            elements.append(Image(img_buffer, width=12*cm, height=8*cm))
            elements.append(Spacer(1, 0.5*cm))
            
            # Scope definitions
            scopes = [
                ('Scope 1', 'Direct emissions from owned or controlled sources.',
                 scope_totals.get('1', 0)),
                ('Scope 2', 'Indirect emissions from purchased electricity/heat.',
                 scope_totals.get('2', 0)),
                ('Scope 3', 'All other indirect emissions in the value chain.',
                 scope_totals.get('3', 0)),
            ]
            for scope_name, desc_text, total in scopes:
                pct = (total / grand_total * 100) if grand_total > 0 else 0
                elements.append(Paragraph(
                    f"<b>{scope_name}</b>: {total:,.1f} tCO₂e ({pct:.1f}%) — {desc_text}",
                    body
                ))
            
            elements.append(PageBreak())
            return elements
        
        story.extend(make_scope_breakdown())
        
        # --- PAGE 3: MONTHLY TREND CHART ---
        def make_monthly_trend() -> list[Any]:
            elements = []
            h1 = ParagraphStyle('H1', fontSize=18, fontName='Helvetica-Bold',
                textColor=COLOR_DARK, spaceAfter=0.5*cm)
            elements.append(Paragraph("Monthly Emission Trends", h1))
            elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_GREEN))
            elements.append(Spacer(1, 0.5*cm))
            
            # Process monthly data
            from collections import defaultdict
            monthly_by_scope: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
            months_set = set()
            for row in monthly_rows:
                month_str = row.month.strftime('%b %Y') if row.month else 'Unknown'
                monthly_by_scope[month_str][row.scope] += float(row.total or 0)
                months_set.add(month_str)
            
            months_list = sorted(months_set, key=lambda x: 
                __import__('datetime').datetime.strptime(x, '%b %Y'))
            
            if months_list:
                fig, ax = plt.subplots(figsize=(7, 4), facecolor='white')
                s1 = [monthly_by_scope[m].get('1', 0) for m in months_list]
                s2 = [monthly_by_scope[m].get('2', 0) for m in months_list]
                s3 = [monthly_by_scope[m].get('3', 0) for m in months_list]
                x = range(len(months_list))
                
                ax.fill_between(x, s1, alpha=0.8, color='#ef4444', label='Scope 1')
                ax.fill_between(x, 
                    [a+b for a,b in zip(s1,s2, strict=False)], s1, 
                    alpha=0.8, color='#f97316', label='Scope 2')
                ax.fill_between(x,
                    [a+b+c for a,b,c in zip(s1,s2,s3, strict=False)], 
                    [a+b for a,b in zip(s1,s2, strict=False)],
                    alpha=0.8, color='#eab308', label='Scope 3')
                
                ax.set_xticks(x)
                ax.set_xticklabels(
                    [m.split()[0] for m in months_list], 
                    rotation=45, ha='right', fontsize=8
                )
                ax.set_ylabel('tCO₂e', fontsize=9)
                ax.legend(loc='upper left', fontsize=8)
                ax.grid(axis='y', alpha=0.3)
                ax.set_facecolor('#fafafa')
                plt.tight_layout()
                
                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight',
                            facecolor='white')
                plt.close()
                img_buffer.seek(0)
                elements.append(Image(img_buffer, width=15*cm, height=9*cm))
            
            elements.append(PageBreak())
            return elements
        
        story.extend(make_monthly_trend())
        
        # --- PAGE 4: TOP SUPPLIERS TABLE ---
        def make_suppliers_table() -> list[Any]:
            elements = []
            h1 = ParagraphStyle('H1', fontSize=18, fontName='Helvetica-Bold',
                textColor=COLOR_DARK, spaceAfter=0.5*cm)
            elements.append(Paragraph("Top Emitting Suppliers", h1))
            elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_GREEN))
            elements.append(Spacer(1, 0.5*cm))
            
            if top_suppliers:
                table_data: list[list[str]] = [['Supplier', 'Sector', 'tCO₂e', '% of Total', 'ESG Score']]
                for s in top_suppliers:
                    pct = (s.total / grand_total * 100) if grand_total > 0 else 0
                    esg = f"{s.esg_score:.0f}/100" if s.esg_score else "N/A"
                    table_data.append([
                        s.name, s.sector or '—',
                        f"{s.total:,.1f}", f"{pct:.1f}%", esg
                    ])
                
                t = Table(table_data, 
                    colWidths=[5.5*cm, 3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
                style = [
                    ('BACKGROUND', (0,0), (-1,0), COLOR_DARK),
                    ('TEXTCOLOR', (0,0), (-1,0), white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,0), 10),
                    ('FONTSIZE', (0,1), (-1,-1), 9),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [COLOR_BG, white]),
                    ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
                    ('PADDING', (0,0), (-1,-1), 6),
                    ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
                ]
                # Highlight top emitter red
                if len(top_suppliers) > 0:
                    style.append(('TEXTCOLOR', (0,1), (-1,1), COLOR_RED))
                    style.append(('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'))
                t.setStyle(TableStyle(style))
                elements.append(t)
            else:
                body = ParagraphStyle('Body', fontSize=10, fontName='Helvetica',
                    textColor=COLOR_GRAY)
                elements.append(Paragraph("No supplier data available for this period.", body))
            
            elements.append(PageBreak())
            return elements
        
        story.extend(make_suppliers_table())
        
        # --- PAGE 5: METHODOLOGY ---
        def make_methodology() -> list[Any]:
            elements = []
            h1 = ParagraphStyle('H1', fontSize=18, fontName='Helvetica-Bold',
                textColor=COLOR_DARK, spaceAfter=0.5*cm)
            h2 = ParagraphStyle('H2', fontSize=13, fontName='Helvetica-Bold',
                textColor=COLOR_DARK, spaceAfter=0.3*cm, spaceBefore=0.5*cm)
            body = ParagraphStyle('Body', fontSize=10, fontName='Helvetica',
                textColor=HexColor('#374151'), spaceAfter=0.2*cm, leading=14)
            
            elements.append(Paragraph("Methodology & Data Sources", h1))
            elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_GREEN))
            elements.append(Spacer(1, 0.3*cm))
            
            elements.append(Paragraph("GHG Protocol Alignment", h2))
            elements.append(Paragraph(
                "This report has been prepared in accordance with the GHG Protocol "
                "Corporate Accounting and Reporting Standard. Emissions are categorized "
                "into Scope 1 (direct), Scope 2 (indirect energy), and Scope 3 "
                "(value chain) following the GHG Protocol definitions.", body))
            
            elements.append(Paragraph("Emission Factors", h2))
            elements.append(Paragraph(
                "Transport emission factors sourced from UK DEFRA 2023 Guidelines: "
                "Road freight: 0.10621 kg CO₂e/tonne-km, "
                "Air freight: 0.60210 kg CO₂e/tonne-km, "
                "Sea freight: 0.01570 kg CO₂e/tonne-km, "
                "Rail: 0.02750 kg CO₂e/tonne-km.", body))
            
            elements.append(Paragraph("Data Quality", h2))
            elements.append(Paragraph(
                "Emission data sourced from direct supplier submissions, "
                "logistics provider APIs, and internal energy consumption records. "
                "All values reported in metric tonnes of CO₂ equivalent (tCO₂e) "
                "using GWP100 values from IPCC AR6.", body))
            
            elements.append(Paragraph("Limitations", h2))
            elements.append(Paragraph(
                "Scope 3 figures are estimates based on available supplier data "
                "and may not capture the full value chain. This report covers the "
                f"period {period_start.strftime('%d %B %Y')} to "
                f"{period_end.strftime('%d %B %Y')}.", body))
            
            return elements
        
        story.extend(make_methodology())
        
        # Build PDF
        doc.build(story)
        logger.info("report_generated", report_id=report_id, path=output_path)
        return f"/static/reports/{safe_id}.pdf"
