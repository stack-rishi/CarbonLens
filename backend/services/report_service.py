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

COLOR_GREEN = HexColor('#2d7a4f') # Brand green (forest)
COLOR_DARK = HexColor('#0d1a0f')  # Brand dark forest bg
COLOR_GRAY = HexColor('#5a6b5a')  # Sage/gray text
COLOR_RED = HexColor('#ef4444')
COLOR_ORANGE = HexColor('#f97316')
COLOR_YELLOW = HexColor('#eab308')
COLOR_BG = HexColor('#f8fafc')
COLOR_MINT = HexColor('#e8f2e8')  # Brand mint highlight

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
            
        # Ensure output directory exists absolutely relative to project structure
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(backend_dir, "static", "reports")
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
        
        # Build PDF with generous margins to prevent overlap with header/footers
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2.8*cm,
            bottomMargin=2.8*cm
        )
        
        story = []
        
        # --- PAGE 1: COVER ---
        def make_cover() -> list[Any]:
            elements = []
            elements.append(Spacer(1, 4.5*cm))
            
            title_style = ParagraphStyle('CoverTitle',
                fontSize=28, textColor=COLOR_DARK, spaceAfter=0.4*cm,
                fontName='Helvetica-Bold', leading=34)
            
            subtitle_style = ParagraphStyle('CoverSubtitle',
                fontSize=13, textColor=COLOR_GRAY, spaceAfter=2.0*cm,
                fontName='Helvetica', leading=17)
                
            org_style = ParagraphStyle('CoverOrg',
                fontSize=18, textColor=COLOR_GREEN, spaceAfter=0.3*cm,
                fontName='Helvetica-Bold')
                
            metadata_style = ParagraphStyle('CoverMeta',
                fontSize=9.5, textColor=COLOR_GRAY, leading=14, fontName='Helvetica')
            
            content_elements = [
                Paragraph("Greenhouse Gas Emissions Disclosure & Carbon Audit Report", title_style),
                Paragraph("Aligned with the Greenhouse Gas (GHG) Protocol Corporate Standard", subtitle_style),
                Paragraph(org.name if org else "Organization", org_style),
                Spacer(1, 0.4*cm),
                Paragraph(f"<b>Reporting Period:</b> {period_start.strftime('%B %Y')} — {period_end.strftime('%B %Y')}", metadata_style),
                Paragraph(f"<b>Audit Date:</b> {date.today().strftime('%d %B %Y')}", metadata_style),
                Paragraph("<b>Audit Standard:</b> GHG Protocol Scope 1, 2 & 3", metadata_style),
            ]
            
            # Pack cover elements into table where Col 1 is spacing for sidebar background, Col 2 is content
            cover_table = Table([[Spacer(1, 1), content_elements]], colWidths=[5.5*cm, 11.5*cm])
            cover_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (1,0), (1,0), 0.6*cm),
                ('RIGHTPADDING', (1,0), (1,0), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            elements.append(cover_table)
            elements.append(PageBreak())
            return elements
        
        story.extend(make_cover())
        
        # --- PAGE 2: SCOPE BREAKDOWN WITH PIE CHART ---
        def make_scope_breakdown() -> list[Any]:
            elements = []
            h1 = ParagraphStyle('H1', fontSize=18, fontName='Helvetica-Bold',
                textColor=COLOR_DARK, spaceAfter=0.5*cm)
            body = ParagraphStyle('Body', fontSize=10, fontName='Helvetica',
                textColor=COLOR_GRAY, spaceAfter=0.4*cm, leading=15)
            
            elements.append(Paragraph("Scope Emissions Breakdown", h1))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_GREEN, spaceAfter=0.6*cm))
            
            # Donut chart
            fig, ax = plt.subplots(figsize=(6, 3.8), facecolor='white')
            scope_labels = ['Scope 1', 'Scope 2', 'Scope 3']
            scope_values = [
                scope_totals.get('1', 0.001),
                scope_totals.get('2', 0.001),
                scope_totals.get('3', 0.001)
            ]
            colors_list = ['#ef4444', '#f97316', '#eab308']
            
            # Donut chart (width=0.4 creates the hollow center)
            wedges, texts, autotexts = ax.pie(
                scope_values, labels=scope_labels, colors=colors_list,
                autopct='%1.1f%%', startangle=90, pctdistance=0.75,
                wedgeprops={'width': 0.4, 'edgecolor': 'white', 'linewidth': 2},
                textprops={'fontsize': 9, 'color': '#0f172a', 'weight': 'bold'}
            )
            ax.set_title(f'Total Footprint: {grand_total:,.1f} tCO$_2$e', fontsize=12, pad=10, weight='bold', color='#0f172a')
            plt.tight_layout()
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight',
                        facecolor='white')
            plt.close()
            img_buffer.seek(0)
            
            elements.append(Image(img_buffer, width=13*cm, height=8.2*cm))
            elements.append(Spacer(1, 0.4*cm))
            
            # Scope definitions in styled table panel
            scopes = [
                ('Scope 1 (Direct)', 'Emissions from owned/controlled stationary or mobile combustion sources.', scope_totals.get('1', 0)),
                ('Scope 2 (Indirect)', 'Emissions from purchased electricity, steam, heating, and cooling.', scope_totals.get('2', 0)),
                ('Scope 3 (Value Chain)', 'Emissions from supply chain, outsourced logistics, and product lifecycle.', scope_totals.get('3', 0)),
            ]
            
            panel_data = []
            for scope_name, desc_text, total in scopes:
                pct = (total / grand_total * 100) if grand_total > 0 else 0
                panel_data.append([
                    Paragraph(f"<b>{scope_name}</b>", ParagraphStyle('P1', fontSize=10, textColor=COLOR_DARK, fontName='Helvetica-Bold')),
                    Paragraph(f"{desc_text}", ParagraphStyle('P2', fontSize=9, textColor=COLOR_GRAY, leading=12)),
                    Paragraph(f"<b>{total:,.1f} t</b><br/><font color='#5a6b5a'>({pct:.1f}%)</font>", ParagraphStyle('P3', fontSize=9, alignment=2, leading=12))
                ])
            
            panel_table = Table(panel_data, colWidths=[4.2*cm, 9.8*cm, 3.0*cm])
            panel_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,0), (-1,-1), COLOR_MINT),
                ('GRID', (0,0), (-1,-1), 0.5, HexColor('#d1e3d1')),
                ('PADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('TOPPADDING', (0,0), (-1,-1), 10),
            ]))
            elements.append(panel_table)
            
            elements.append(PageBreak())
            return elements
        
        story.extend(make_scope_breakdown())
        
        # --- PAGE 3: MONTHLY TREND CHART ---
        def make_monthly_trend() -> list[Any]:
            elements = []
            h1 = ParagraphStyle('H1', fontSize=18, fontName='Helvetica-Bold',
                textColor=COLOR_DARK, spaceAfter=0.5*cm)
            elements.append(Paragraph("Monthly Emission Trends", h1))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_GREEN, spaceAfter=0.6*cm))
            
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
                fig, ax = plt.subplots(figsize=(7.5, 4.2), facecolor='white')
                s1 = [monthly_by_scope[m].get('1', 0) for m in months_list]
                s2 = [monthly_by_scope[m].get('2', 0) for m in months_list]
                s3 = [monthly_by_scope[m].get('3', 0) for m in months_list]
                x = range(len(months_list))
                
                # Plot with alpha area blends for modern look
                ax.fill_between(x, s1, alpha=0.75, color='#ef4444', label='Scope 1')
                ax.fill_between(x, 
                    [a+b for a,b in zip(s1,s2, strict=False)], s1, 
                    alpha=0.75, color='#f97316', label='Scope 2')
                ax.fill_between(x,
                    [a+b+c for a,b,c in zip(s1,s2,s3, strict=False)], 
                    [a+b for a,b in zip(s1,s2, strict=False)],
                    alpha=0.75, color='#eab308', label='Scope 3')
                
                ax.set_xticks(x)
                ax.set_xticklabels(
                    [m.split()[0] for m in months_list], 
                    rotation=45, ha='right', fontsize=9, color='#0f172a'
                )
                ax.set_ylabel('tCO$_2$e', fontsize=10, color='#0f172a', weight='bold')
                ax.legend(loc='upper left', fontsize=9, frameon=True, facecolor='white', edgecolor='#e2e8f0')
                ax.grid(axis='y', linestyle='--', alpha=0.4, color='#cbd5e1')
                ax.set_axisbelow(True)
                ax.set_facecolor('#f8fafc')
                
                # Hide unnecessary chart frames
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_color('#cbd5e1')
                ax.spines['bottom'].set_color('#cbd5e1')
                
                plt.tight_layout()
                
                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight',
                            facecolor='white')
                plt.close()
                img_buffer.seek(0)
                elements.append(Image(img_buffer, width=16*cm, height=9.2*cm))
                
            elements.append(PageBreak())
            return elements
        
        story.extend(make_monthly_trend())
        
        # --- PAGE 4: TOP SUPPLIERS TABLE ---
        def make_suppliers_table() -> list[Any]:
            elements = []
            h1 = ParagraphStyle('H1', fontSize=18, fontName='Helvetica-Bold',
                textColor=COLOR_DARK, spaceAfter=0.5*cm)
            elements.append(Paragraph("Top Value Chain Contributors (Scope 3)", h1))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_GREEN, spaceAfter=0.6*cm))
            
            if top_suppliers:
                table_data: list[list[Any]] = [[
                    Paragraph('<b>Supplier Node</b>', ParagraphStyle('TH', fontSize=10, textColor=white, fontName='Helvetica-Bold')),
                    Paragraph('<b>Sector</b>', ParagraphStyle('TH', fontSize=10, textColor=white, fontName='Helvetica-Bold')),
                    Paragraph('<b>Emissions (tCO<sub>2</sub>e)</b>', ParagraphStyle('TH', fontSize=10, textColor=white, fontName='Helvetica-Bold', alignment=2)),
                    Paragraph('<b>% of Total</b>', ParagraphStyle('TH', fontSize=10, textColor=white, fontName='Helvetica-Bold', alignment=2)),
                    Paragraph('<b>ESG Index</b>', ParagraphStyle('TH', fontSize=10, textColor=white, fontName='Helvetica-Bold', alignment=2))
                ]]
                
                for s in top_suppliers:
                    pct = (s.total / grand_total * 100) if grand_total > 0 else 0
                    esg = f"{s.esg_score:.0f}/100" if s.esg_score else "N/A"
                    table_data.append([
                        Paragraph(s.name, ParagraphStyle('TD', fontSize=9, textColor=COLOR_DARK)),
                        Paragraph(s.sector or '—', ParagraphStyle('TD', fontSize=9, textColor=COLOR_GRAY)),
                        Paragraph(f"{s.total:,.1f}", ParagraphStyle('TD', fontSize=9, textColor=COLOR_DARK, alignment=2)),
                        Paragraph(f"{pct:.1f}%", ParagraphStyle('TD', fontSize=9, textColor=COLOR_DARK, alignment=2)),
                        Paragraph(esg, ParagraphStyle('TD', fontSize=9, textColor=COLOR_DARK, alignment=2))
                    ])
                
                t = Table(table_data, 
                    colWidths=[6.0*cm, 3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
                
                style = [
                    ('BACKGROUND', (0,0), (-1,0), COLOR_DARK),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor('#ffffff'), HexColor('#f8fafc')]),
                    ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e2e8f0')),
                    ('PADDING', (0,0), (-1,-1), 10),
                    ('TOPPADDING', (0,0), (-1,-1), 10),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ]
                
                # Highlight top emitter text red
                if len(top_suppliers) > 0:
                    style.append(('BACKGROUND', (0,1), (-1,1), HexColor('#fee2e2')))
                
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
            
            elements.append(Paragraph("Methodology & Reference Standards", h1))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_GREEN, spaceAfter=0.6*cm))
            
            elements.append(Paragraph("GHG Protocol Alignment", h2))
            elements.append(Paragraph(
                "This disclosure report follows the Greenhouse Gas (GHG) Protocol Corporate "
                "Accounting and Reporting Standard guidelines. Emissions are categorized "
                "into direct operational activities (Scope 1), purchased utility grids (Scope 2), "
                "and external supply chain supply/logistics (Scope 3) to prevent double counting.", body))
            
            elements.append(Paragraph("Emission Factors Applied", h2))
            elements.append(Paragraph(
                "Carbon intensities are derived using DEFRA 2023 Guidelines: "
                "Road freight: 0.10621 kg CO<sub>2</sub>e/tonne-km | "
                "Air freight: 0.60210 kg CO<sub>2</sub>e/tonne-km | "
                "Sea freight: 0.01570 kg CO<sub>2</sub>e/tonne-km | "
                "Rail transit: 0.02750 kg CO<sub>2</sub>e/tonne-km.", body))
            
            elements.append(Paragraph("Quality & Accuracy Metrics", h2))
            elements.append(Paragraph(
                "Data consists of direct utility sync APIs, verified supplier declarations, "
                "and ERP ledger exports. Total figures are represented in metric tonnes of "
                "CO<sub>2</sub> equivalent (tCO<sub>2</sub>e) using the IPCC Sixth Assessment Report (AR6) GWP100 values.", body))
            
            elements.append(Paragraph("Report Limitations", h2))
            elements.append(Paragraph(
                "Value chain calculations are based on primary supplier reporting. Gaps in supplier "
                "reporting are filled using global industry averages, which may introduce minor variances. "
                "This disclosure is valid solely for the verified dates specified.", body))
            
            return elements
        
        story.extend(make_methodology())
        
        # --- BACKGROUND CANVAS DECORATIONS ---
        def draw_cover_decorations(canvas: Any, document: Any) -> None:
            canvas.saveState()
            # Left forest block
            canvas.setFillColor(HexColor('#0d1a0f'))
            canvas.rect(0, 0, 5.0*cm, 29.7*cm, fill=1, stroke=0)
            
            # Left thin mint accent line
            canvas.setFillColor(HexColor('#2d7a4f'))
            canvas.rect(5.0*cm, 0, 0.2*cm, 29.7*cm, fill=1, stroke=0)
            canvas.restoreState()

        def draw_later_decorations(canvas: Any, document: Any) -> None:
            canvas.saveState()
            # Running header
            canvas.setFont('Helvetica-Bold', 8)
            canvas.setFillColor(HexColor('#6b7280'))
            canvas.drawString(2*cm, 28.2*cm, "CarbonLens — Corporate Emissions Disclosure")
            
            # Header border line
            canvas.setStrokeColor(HexColor('#e5e7eb'))
            canvas.setLineWidth(0.5)
            canvas.line(2*cm, 27.9*cm, 19*cm, 27.9*cm)
            
            # Footer border line
            canvas.line(2*cm, 2.2*cm, 19*cm, 2.2*cm)
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.drawString(2*cm, 1.8*cm, "CONFIDENTIAL — FOR INTERNAL SUSTAINABILITY AUDITS")
            canvas.drawRightString(19*cm, 1.8*cm, f"Page {document.page}")
            canvas.restoreState()

        # Build PDF
        doc.build(
            story,
            onFirstPage=draw_cover_decorations,
            onLaterPages=draw_later_decorations
        )
        
        logger.info("report_generated", report_id=report_id, path=output_path)
        return f"/static/reports/{safe_id}.pdf"
