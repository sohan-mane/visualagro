"""
routers/insights.py — /insights
Profit Insights screen (Screen 4):
  weekly summary KPIs, revenue+waste chart data,
  per-item spoilage losses, and best-seller rankings.
"""

from datetime import date, timedelta
from fastapi  import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models   import WeeklyMetric, SpoilageLoss, BestSeller
from schemas  import WeeklySummary, WeeklyMetricOut, SpoilageLossOut, BestSellerOut
from auth     import get_current_vendor

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/weekly", response_model=WeeklySummary,
            summary="Aggregated weekly KPIs + chart arrays for the Insights screen")
def weekly_summary(
    week_start: date = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_vendor),
):
    if week_start is None:
        # default: most recent 7 days
        latest = (
            db.query(func.max(WeeklyMetric.metric_date)).scalar()
            or date.today()
        )
        week_start = latest - timedelta(days=6)

    week_end = week_start + timedelta(days=6)

    rows = (
        db.query(WeeklyMetric)
        .filter(
            WeeklyMetric.metric_date >= week_start,
            WeeklyMetric.metric_date <= week_end,
        )
        .order_by(WeeklyMetric.metric_date)
        .all()
    )

    labels  = [r.day_label for r in rows]
    revenue = [r.revenue   for r in rows]
    waste   = [r.waste     for r in rows]

    total_rev   = sum(revenue)
    total_waste = sum(waste)
    avg_daily   = total_rev // max(len(revenue), 1)

    return WeeklySummary(
        total_revenue    = total_rev,
        total_waste      = total_waste,
        avg_daily        = avg_daily,
        best_margin_note = "48% — Onions",   # updated by ML pipeline
        labels           = labels,
        revenue          = revenue,
        waste            = waste,
    )


@router.get("/weekly/days", response_model=list[WeeklyMetricOut],
            summary="Raw daily rows for the chart (revenue + waste per day)")
def weekly_days(
    week_start: date = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_vendor),
):
    if week_start is None:
        latest = (
            db.query(func.max(WeeklyMetric.metric_date)).scalar()
            or date.today()
        )
        week_start = latest - timedelta(days=6)
    week_end = week_start + timedelta(days=6)

    return (
        db.query(WeeklyMetric)
        .filter(
            WeeklyMetric.metric_date >= week_start,
            WeeklyMetric.metric_date <= week_end,
        )
        .order_by(WeeklyMetric.metric_date)
        .all()
    )


@router.get("/spoilage", response_model=list[SpoilageLossOut],
            summary="Per-item spoilage ₹ losses for the bar chart")
def spoilage_losses(
    week_start: date = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_vendor),
):
    q = db.query(SpoilageLoss)
    if week_start:
        q = q.filter(SpoilageLoss.week_start == week_start)
    return q.order_by(SpoilageLoss.value.desc()).all()


@router.get("/bestsellers", response_model=list[BestSellerOut],
            summary="Best-seller rankings table")
def bestsellers(
    week_start: date = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_vendor),
):
    q = db.query(BestSeller)
    if week_start:
        q = q.filter(BestSeller.week_start == week_start)
    return q.order_by(BestSeller.rank).all()
