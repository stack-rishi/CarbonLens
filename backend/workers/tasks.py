from uuid import UUID

import structlog
from backend.core.db import AsyncSessionLocal
from backend.models.models import Report
from backend.services.report_service import ReportService
from sqlalchemy import select

logger = structlog.get_logger()


async def compile_report_task(report_id: UUID) -> None:
    """Asynchronous background task to generate PDF report and update report status in database."""
    logger.info("report_compilation_started", report_id=str(report_id))

    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch report details
            result = await db.execute(select(Report).where(Report.id == report_id))
            report = result.scalars().first()

            if not report:
                logger.error("report_not_found", report_id=str(report_id))
                return

            # Update status to processing
            report.status = "processing"
            await db.commit()

            # 2. Branch on report_type
            report_type = getattr(report, "report_type", "sustainability") or "sustainability"

            if report_type == "compliance":
                from backend.services.compliance_pdf_service import generate_compliance_pdf
                pdf_url = await generate_compliance_pdf(
                    db=db,
                    org_id=report.org_id,
                    report_id=report.id,
                    period_start=report.period_start,
                    period_end=report.period_end,
                )
            else:
                pdf_url = await ReportService.generate_pdf_report(
                    db=db,
                    org_id=report.org_id,
                    period_start=report.period_start,
                    period_end=report.period_end,
                )

            # 3. Update report record on success
            result = await db.execute(select(Report).where(Report.id == report_id))
            report = result.scalars().first()
            if report:
                report.s3_url = pdf_url
                report.status = "done"
                await db.commit()
                logger.info("report_compilation_success", report_id=str(report_id), path=pdf_url)

        except Exception as e:
            logger.error("report_compilation_failed", report_id=str(report_id), error=str(e))
            # Mark as failed in DB
            try:
                result = await db.execute(select(Report).where(Report.id == report_id))
                report = result.scalars().first()
                if report:
                    report.status = "failed"
                    await db.commit()
            except Exception as db_err:
                logger.error("report_status_update_failed", error=str(db_err))
