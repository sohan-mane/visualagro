"""
VisualAgro — Dashboard Router
GET /dashboard/stats  → headline stat cards (Screen 1)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_vendor
from ai.brain import get_brain
from database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _format_currency(value: float | int) -> str:
    try:
        return f"₹{value:,.0f}"
    except Exception:
        return f"₹{value}"


@router.get("/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    """
    Headline stat cards shown at the top of the Dashboard screen.
    """
    rows = (
        db.query(models.WeeklyMetric)
        .order_by(models.WeeklyMetric.metric_date.desc())
        .limit(2)
        .all()
    )

    today_rev = rows[0].revenue if rows else 0
    yesterday = rows[1].revenue if len(rows) > 1 else today_rev
    waste_today = rows[0].waste if rows else 0
    wastes = [r[0] for r in db.query(models.WeeklyMetric.waste).all()]
    avg_waste = sum(wastes) / max(len(wastes), 1)

    rev_delta_pct = round((today_rev - yesterday) / yesterday * 100) if yesterday else 0
    rev_sign = "↑" if rev_delta_pct >= 0 else "↓"
    waste_saved_pct = round((avg_waste - waste_today) / avg_waste * 100) if avg_waste else 0

    all_items = db.query(models.StockItem).all()
    total_items = len(all_items)
    critically_low = sum(1 for i in all_items if i.pct < 20)

    brain = get_brain()
    forecast = brain.revenue_forecast(db)

    return schemas.DashboardStats(
        today_revenue=_format_currency(today_rev),
        revenue_change=f"{rev_sign} {abs(rev_delta_pct)}% vs yesterday",
        waste_cost=_format_currency(waste_today),
        waste_change=f"↓ {abs(waste_saved_pct)}% vs average",
        items_in_stock=total_items,
        critically_low=critically_low,
        ai_forecast=_format_currency(forecast["value"]),
        forecast_label=forecast["label"],
    )
