"""
Alert Service — evaluates emission data and generates compliance alerts with upsert logic.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import Alert, ComplianceThreshold, EmissionRecord, Supplier
from backend.services.compliance_service import (
    _first_of_month,
    _get_monthly_by_scope,
    _prev_month,
    get_compliance_status,
)

logger = structlog.get_logger()


def _generate_recommendations(
    alert_type: str,
    scope: str | None,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Rule-based recommendation generator. Minimum 3 per alert.
    Uses real data from context: top_supplier_name, top_supplier_factor, pct_change, category.
    """
    top_supplier = context.get("top_supplier_name", "your highest-emission supplier")
    top_factor_supplier = context.get("top_factor_supplier_name", "the supplier with highest emission factor")
    pct_increase = context.get("pct_increase", 0.0)
    category = context.get("top_category", "purchased_goods")
    scope_label = f"Scope {scope}" if scope and scope != "total" else "total emissions"
    sustainability_score = context.get("sustainability_score", 0.0)

    if alert_type in ("emission_spike", "threshold_exceeded"):
        return [
            {
                "title": f"Switch {top_supplier}'s transport mode to rail or sea",
                "description": (
                    f"{top_supplier} is your top emitter in {scope_label}. Switching from road or air freight "
                    f"to rail or sea can reduce transport-related carbon by 60-85%%. "
                    f"Contact your logistics team to renegotiate routing contracts."
                ),
                "category": "logistics",
                "estimated_impact_pct": 15.0,
            },
            {
                "title": f"Renegotiate sourcing volume with {top_factor_supplier}",
                "description": (
                    f"{top_factor_supplier} has the highest emission factor in your supply chain. "
                    f"Reducing sourcing volume by 20%% or shifting to a lower-intensity alternative "
                    f"could directly reduce {scope_label} by an estimated 12-18%%. "
                    f"Issue an RFQ to pre-qualified greener suppliers in the same category."
                ),
                "category": "sourcing",
                "estimated_impact_pct": 12.0,
            },
            {
                "title": f"Schedule audit of {category.replace('_', ' ')} in {scope_label}",
                "description": (
                    f"The largest emission category in this scope is '{category}', which showed a "
                    f"{pct_increase:.1f}%% increase this month. Commission an operational audit to identify "
                    f"data quality issues, unreported efficiency gains, and reduction opportunities "
                    f"in this specific process."
                ),
                "category": "process",
                "estimated_impact_pct": 8.0,
            },
        ]

    elif alert_type == "low_sustainability_score":
        return [
            {
                "title": "Audit and update supplier ESG scores",
                "description": (
                    f"Your sustainability score is {sustainability_score:.0f}/100. Many ESG scores may be "
                    f"outdated or missing — these default to 70 which drags your score. "
                    f"Request updated ESG certifications from suppliers who have not submitted data "
                    f"in the past 12 months. Even 2-3 verified high scorers can lift your score significantly."
                ),
                "category": "data_quality",
                "estimated_impact_pct": 10.0,
            },
            {
                "title": "Set or revise emission reduction targets",
                "description": (
                    "If baseline year and net-zero target year are not configured, your reduction progress "
                    "score defaults to 70. Configure a baseline year (e.g., 2023) and a net-zero target "
                    f"year (e.g., 2030) in Compliance Settings. A 20%% reduction goal with {top_supplier} "
                    "as primary focus is a recommended starting point."
                ),
                "category": "strategy",
                "estimated_impact_pct": 15.0,
            },
            {
                "title": "Prioritize switching top-intensity suppliers to lower-carbon alternatives",
                "description": (
                    f"Your two highest-intensity suppliers — including {top_supplier} and "
                    f"{top_factor_supplier} — represent a disproportionate share of your Scope 3 footprint. "
                    f"Identify verified alternatives via the CDP Supply Chain Program or EcoVadis. "
                    f"Even partial volume shifts can meaningfully reduce total emissions."
                ),
                "category": "sourcing",
                "estimated_impact_pct": 18.0,
            },
        ]

    return []


async def evaluate_and_generate_alerts(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> list[Alert]:
    """
    Runs all three alert checks for the org, upserts (not duplicates) alerts per spec,
    and returns all created/updated alerts.
    """
    today = date.today()
    curr_month_start = _first_of_month(today)
    prev_month_start = _prev_month(curr_month_start)

    current_by_scope = await _get_monthly_by_scope(db, org_id, curr_month_start)
    previous_by_scope = await _get_monthly_by_scope(db, org_id, prev_month_start)

    current_total = sum(current_by_scope.values())
    previous_total = sum(previous_by_scope.values())
    current_by_scope["total"] = current_total
    previous_by_scope["total"] = previous_total

    # Fetch thresholds
    thresh_result = await db.execute(
        select(ComplianceThreshold).where(ComplianceThreshold.org_id == org_id)
    )
    thresholds = {t.scope: t.threshold_tco2e for t in thresh_result.scalars().all()}

    # Fetch compliance status for sustainability score
    compliance_data = await get_compliance_status(org_id, db)
    sustainability_score = compliance_data["sustainability_score"]

    # Fetch top supplier info for recommendations
    top_supplier_result = await db.execute(
        select(
            Supplier.name,
            Supplier.emission_factor_kg_per_unit,
            func.sum(EmissionRecord.amount_tco2e).label("total"),
        )
        .join(EmissionRecord, EmissionRecord.supplier_id == Supplier.id)
        .where(
            EmissionRecord.org_id == org_id,
            EmissionRecord.period_start >= curr_month_start,
        )
        .group_by(Supplier.id, Supplier.name, Supplier.emission_factor_kg_per_unit)
        .order_by(func.sum(EmissionRecord.amount_tco2e).desc())
        .limit(2)
    )
    top_suppliers_rows = top_supplier_result.fetchall()
    top_supplier_name = top_suppliers_rows[0].name if top_suppliers_rows else "your top supplier"
    top_factor_supplier_name = (
        top_suppliers_rows[1].name if len(top_suppliers_rows) > 1 else top_supplier_name
    )

    # Fetch top emission category
    top_category_result = await db.execute(
        select(EmissionRecord.category, func.sum(EmissionRecord.amount_tco2e).label("total"))
        .where(EmissionRecord.org_id == org_id, EmissionRecord.period_start >= curr_month_start)
        .group_by(EmissionRecord.category)
        .order_by(func.sum(EmissionRecord.amount_tco2e).desc())
        .limit(1)
    )
    top_cat_row = top_category_result.fetchone()
    top_category = top_cat_row.category if top_cat_row and top_cat_row.category else "purchased_goods"

    created_or_updated: list[Alert] = []

    async def _upsert_alert(
        alert_type: str,
        scope: str | None,
        severity: str,
        title: str,
        message: str,
        metric_value: float | None,
        threshold_value: float | None,
        recommendations: list[dict[str, Any]],
    ) -> Alert:
        """Upsert: update existing active/acknowledged alert, or create new one."""
        stmt = select(Alert).where(
            Alert.org_id == org_id,
            Alert.alert_type == alert_type,
            Alert.period_month == curr_month_start,
        )
        if scope is not None:
            stmt = stmt.where(Alert.scope == scope)
        else:
            stmt = stmt.where(Alert.scope.is_(None))

        res = await db.execute(stmt)
        existing = res.scalars().first()

        if existing and existing.status in ("active", "acknowledged"):
            # UPDATE in place
            existing.severity = severity
            existing.title = title
            existing.message = message
            existing.metric_value = metric_value
            existing.threshold_value = threshold_value
            existing.recommendations = recommendations
            existing.triggered_at = datetime.utcnow()
            await db.flush()
            logger.info("alert_updated", alert_id=str(existing.id), alert_type=alert_type, scope=scope)
            return existing
        elif existing and existing.status == "resolved":
            # Already resolved this month — don't recreate
            return existing
        else:
            # INSERT new
            alert = Alert(
                id=uuid.uuid4(),
                org_id=org_id,
                alert_type=alert_type,
                severity=severity,
                status="active",
                title=title,
                message=message,
                scope=scope,
                metric_value=metric_value,
                threshold_value=threshold_value,
                recommendations=recommendations,
                period_month=curr_month_start,
                triggered_at=datetime.utcnow(),
            )
            db.add(alert)
            await db.flush()
            logger.info("alert_created", alert_id=str(alert.id), alert_type=alert_type, scope=scope)
            return alert

    # ── CHECK 1: Monthly emission spike (per scope AND total) ──────────────────
    for scope_label in ["1", "2", "3", "total"]:
        curr = current_by_scope.get(scope_label, 0.0)
        prev = previous_by_scope.get(scope_label, 0.0)
        if prev == 0:
            continue
        pct_increase = (curr - prev) / prev * 100
        if pct_increase <= 15:
            continue

        if pct_increase > 40:
            severity = "critical"
        elif pct_increase > 25:
            severity = "high"
        else:
            severity = "medium"

        scope_display = f"Scope {scope_label}" if scope_label != "total" else "Total"
        title = f"{scope_display} emissions increased {pct_increase:.1f}% this month"
        message = (
            f"{scope_display} emissions rose from {prev:.1f} to {curr:.1f} tCO2e "
            f"({pct_increase:.1f}% increase). This exceeds the 15% spike threshold. "
            f"Immediate investigation into {top_supplier_name} sourcing patterns is recommended."
        )
        context: dict[str, Any] = {
            "top_supplier_name": top_supplier_name,
            "top_factor_supplier_name": top_factor_supplier_name,
            "pct_increase": pct_increase,
            "top_category": top_category,
        }
        recommendations = _generate_recommendations("emission_spike", scope_label, context)
        alert = await _upsert_alert(
            "emission_spike", scope_label, severity, title, message,
            round(curr, 3), None, recommendations
        )
        created_or_updated.append(alert)

    # ── CHECK 2: Threshold exceeded (per configured scope) ────────────────────
    for scope_label, threshold_val in thresholds.items():
        curr = current_by_scope.get(scope_label, 0.0)
        if threshold_val <= 0:
            continue
        pct_of_thresh = curr / threshold_val * 100
        if pct_of_thresh <= 100:
            continue

        pct_over = pct_of_thresh - 100
        if pct_of_thresh > 130:
            severity = "critical"
        elif pct_of_thresh > 110:
            severity = "high"
        else:
            severity = "medium"

        scope_display = f"Scope {scope_label}" if scope_label != "total" else "Total"
        title = f"{scope_display} exceeded threshold by {pct_over:.1f}%"
        message = (
            f"{scope_display} current emissions are {curr:.1f} tCO2e, exceeding the configured "
            f"threshold of {threshold_val:.1f} tCO2e by {pct_over:.1f}%%. "
            f"Immediate corrective action is required to restore compliance."
        )
        context = {
            "top_supplier_name": top_supplier_name,
            "top_factor_supplier_name": top_factor_supplier_name,
            "pct_increase": pct_over,
            "top_category": top_category,
        }
        recommendations = _generate_recommendations("threshold_exceeded", scope_label, context)
        alert = await _upsert_alert(
            "threshold_exceeded", scope_label, severity, title, message,
            round(curr, 3), threshold_val, recommendations
        )
        created_or_updated.append(alert)

    # ── CHECK 3: Sustainability score below 60 ────────────────────────────────
    if sustainability_score < 60:
        if sustainability_score < 35:
            severity = "critical"
        elif sustainability_score < 50:
            severity = "high"
        else:
            severity = "medium"

        title = f"Sustainability score dropped to {sustainability_score:.0f}/100"
        message = (
            f"Your organization's sustainability score is {sustainability_score:.1f}/100, "
            f"which is below the 60/100 minimum threshold. "
            f"This score reflects weighted factors: emission reduction progress, "
            f"supplier ESG quality, trend performance, and compliance adherence. "
            f"Review the recommendations below for targeted improvements."
        )
        context = {
            "top_supplier_name": top_supplier_name,
            "top_factor_supplier_name": top_factor_supplier_name,
            "sustainability_score": sustainability_score,
            "top_category": top_category,
        }
        recommendations = _generate_recommendations("low_sustainability_score", None, context)
        alert = await _upsert_alert(
            "low_sustainability_score", None, severity, title, message,
            round(sustainability_score, 2), 60.0, recommendations
        )
        created_or_updated.append(alert)

    await db.commit()
    logger.info(
        "alert_evaluation_complete",
        org_id=str(org_id),
        alerts_processed=len(created_or_updated),
    )
    return created_or_updated
