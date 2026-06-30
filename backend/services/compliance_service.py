"""
Compliance Service — evaluates compliance status, sustainability score, and threshold adherence.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import Alert, ComplianceThreshold, EmissionRecord, Organization, Supplier


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _prev_month(d: date) -> date:
    if d.month == 1:
        return date(d.year - 1, 12, 1)
    return date(d.year, d.month - 1, 1)


def _last_of_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1).replace(day=1).__class__(d.year, 12, 31)
    import calendar
    _, last_day = calendar.monthrange(d.year, d.month)
    return d.replace(day=last_day)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


async def _get_monthly_by_scope(
    db: AsyncSession,
    org_id: uuid.UUID,
    month_start: date,
) -> dict[str, float]:
    """Return {scope: total_tco2e} for all records whose period_start falls in the given month."""
    month_end = _last_of_month(month_start)
    result = await db.execute(
        select(
            EmissionRecord.scope,
            func.sum(EmissionRecord.amount_tco2e).label("total"),
        )
        .where(
            EmissionRecord.org_id == org_id,
            EmissionRecord.period_start >= month_start,
            EmissionRecord.period_start <= month_end,
        )
        .group_by(EmissionRecord.scope)
    )
    return {row.scope: float(row.total or 0) for row in result}


async def _get_year_total(
    db: AsyncSession,
    org_id: uuid.UUID,
    year: int,
) -> float:
    """Return total tCO2e for an entire calendar year."""
    result = await db.execute(
        select(func.sum(EmissionRecord.amount_tco2e).label("total"))
        .where(
            EmissionRecord.org_id == org_id,
            EmissionRecord.period_start >= date(year, 1, 1),
            EmissionRecord.period_start <= date(year, 12, 31),
        )
    )
    row = result.fetchone()
    return float(row.total or 0) if row and row.total else 0.0


async def get_compliance_status(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Compute full compliance status object per the spec."""

    today = date.today()
    curr_month_start = _first_of_month(today)
    prev_month_start = _prev_month(curr_month_start)

    # 1. Fetch monthly emissions by scope
    current_by_scope = await _get_monthly_by_scope(db, org_id, curr_month_start)
    previous_by_scope = await _get_monthly_by_scope(db, org_id, prev_month_start)

    current_totals = {
        "scope1": current_by_scope.get("1", 0.0),
        "scope2": current_by_scope.get("2", 0.0),
        "scope3": current_by_scope.get("3", 0.0),
        "total": sum(current_by_scope.values()),
    }
    previous_totals = {
        "scope1": previous_by_scope.get("1", 0.0),
        "scope2": previous_by_scope.get("2", 0.0),
        "scope3": previous_by_scope.get("3", 0.0),
        "total": sum(previous_by_scope.values()),
    }

    # Pct change
    def _pct_change(curr: float, prev: float) -> float:
        if prev == 0:
            return 0.0
        return round((curr - prev) / prev * 100, 2)

    pct_change = {
        "scope1": _pct_change(current_totals["scope1"], previous_totals["scope1"]),
        "scope2": _pct_change(current_totals["scope2"], previous_totals["scope2"]),
        "scope3": _pct_change(current_totals["scope3"], previous_totals["scope3"]),
        "total": _pct_change(current_totals["total"], previous_totals["total"]),
    }

    # 2. Fetch thresholds
    thresh_result = await db.execute(
        select(ComplianceThreshold).where(ComplianceThreshold.org_id == org_id)
    )
    thresholds = {t.scope: t.threshold_tco2e for t in thresh_result.scalars().all()}

    # 3. Build scope breakdown (1, 2, 3, total)
    scope_breakdown = []
    for scope_label, key in [("1", "scope1"), ("2", "scope2"), ("3", "scope3"), ("total", "total")]:
        curr_val = current_totals[key]
        thresh_val = thresholds.get(scope_label)
        if thresh_val is not None:
            pct_of_thresh = round(curr_val / thresh_val * 100, 2)
            configured = True
        else:
            pct_of_thresh = None
            configured = False
        scope_breakdown.append({
            "scope": scope_label,
            "current_tco2e": round(curr_val, 3),
            "threshold_tco2e": thresh_val,
            "pct_of_threshold": pct_of_thresh,
            "configured": configured,
        })

    # 4. Compute compliance_pct from total scope
    total_thresh = thresholds.get("total")
    total_curr = current_totals["total"]
    if total_thresh is not None and total_thresh > 0:
        if total_curr <= total_thresh:
            compliance_pct = 100.0
        else:
            compliance_pct = _clamp((total_thresh / total_curr) * 100)
    else:
        compliance_pct = 100.0  # no threshold = can't determine non-compliance

    # 5. Compute sustainability_score (weighted formula from spec)
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalars().first()

    target_reduction_pct = float(org.target_reduction_pct) if org and org.target_reduction_pct is not None else 20.0

    # reduction_progress_score
    if org and org.baseline_year:
        baseline_total = await _get_year_total(db, org_id, org.baseline_year)
        if baseline_total > 0:
            target_total = baseline_total * (1 - target_reduction_pct / 100)
            denom = baseline_total - target_total
            if denom != 0:
                progress = (baseline_total - total_curr) / denom * 100
            else:
                progress = 100.0
            reduction_progress_score = _clamp(progress)
        else:
            reduction_progress_score = 70.0
    else:
        reduction_progress_score = 70.0

    # supplier_esg_avg_score
    supp_result = await db.execute(
        select(Supplier.esg_score).where(
            Supplier.org_id == org_id,
            Supplier.esg_score.isnot(None)
        )
    )
    esg_scores = [float(r.esg_score) for r in supp_result if r.esg_score is not None]
    supplier_esg_avg_score = sum(esg_scores) / len(esg_scores) if esg_scores else 70.0

    # emission_trend_score
    pct_change_total = pct_change["total"]
    emission_trend_score = _clamp(100 - (pct_change_total * 2))

    # compliance_adherence_score
    any_thresh_configured = bool(thresholds)
    if not any_thresh_configured:
        compliance_adherence_score = 70.0
    else:
        pcts = [b["pct_of_threshold"] for b in scope_breakdown if b["pct_of_threshold"] is not None]
        if pcts:
            max_pct = max(pcts)
            if max_pct > 110:
                compliance_adherence_score = 20.0
            elif max_pct > 90:
                compliance_adherence_score = 60.0
            else:
                compliance_adherence_score = 100.0
        else:
            compliance_adherence_score = 70.0

    sustainability_score = round(
        0.35 * reduction_progress_score
        + 0.25 * supplier_esg_avg_score
        + 0.25 * emission_trend_score
        + 0.15 * compliance_adherence_score,
        2,
    )

    # 6. Determine overall status (exact decision order from spec)
    pcts_with_thresh = [b["pct_of_threshold"] for b in scope_breakdown if b["pct_of_threshold"] is not None]
    max_pct_of_thresh = max(pcts_with_thresh) if pcts_with_thresh else 0.0

    if max_pct_of_thresh > 110 or sustainability_score < 40:
        status = "critical"
    elif max_pct_of_thresh > 90 or sustainability_score < 60:
        status = "warning"
    elif not any_thresh_configured:
        status = "unconfigured"
    else:
        status = "compliant"

    # 7. Active alerts count by severity
    alert_counts_result = await db.execute(
        select(Alert.severity, func.count(Alert.id).label("cnt"))
        .where(Alert.org_id == org_id, Alert.status == "active")
        .group_by(Alert.severity)
    )
    alert_counts: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for row in alert_counts_result:
        alert_counts[row.severity] = row.cnt

    return {
        "status": status,
        "compliance_pct": round(compliance_pct, 2),
        "sustainability_score": sustainability_score,
        "scope_breakdown": scope_breakdown,
        "current_month": current_totals,
        "previous_month": previous_totals,
        "pct_change": pct_change,
        "active_alerts_count": alert_counts,
        "last_evaluated_at": datetime.utcnow().isoformat() + "Z",
    }
