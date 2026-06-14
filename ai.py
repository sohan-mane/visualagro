
"""
routers/ai.py — Phase 3 brain endpoints.

Endpoints:
- GET  /ai/status
- POST /ai/train
- GET  /ai/predict/demand
- GET  /ai/predict/spoilage
- POST /ai/reorder/refresh
"""

from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import get_current_vendor
from database import get_db
from ai.brain import get_brain
import models

router = APIRouter(prefix="/ai", tags=["Phase 3 Brain"])


@router.get("/status")
def status(
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    return get_brain().status(db)


@router.post("/train")
def train(
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    return get_brain().train(db).__dict__


@router.get("/predict/demand")
def predict_demand(
    item_name: str = Query(..., min_length=1),
    horizon_days: int = Query(1, ge=1, le=30),
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    return get_brain().demand_prediction(db, item_name=item_name, horizon_days=horizon_days)


@router.get("/predict/spoilage")
def predict_spoilage(
    item_name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    return get_brain().spoilage_prediction(db, item_name=item_name)


@router.post("/reorder/refresh")
def refresh_reorder(
    for_date: date | None = None,
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    return get_brain().refresh_reorder_table(db, for_date=for_date)
