"""
VisualAgro — Alerts Router
GET  /alerts               → active spoilage alerts
PATCH /alerts/{id}/resolve → mark an alert as resolved
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_vendor
from database import get_db

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _list_alerts(db: Session):
    risk_order = {"HIGH": 0, "MED": 1, "LOW": 2}
    alerts = (
        db.query(models.SpoilageAlert)
        .filter(models.SpoilageAlert.resolved == False)
        .all()
    )
    alerts.sort(key=lambda a: (risk_order.get(a.risk, 9), a.created_at or datetime.min))
    return [
        schemas.AlertOut(
            id=a.id,
            emoji=a.emoji,
            name=a.name,
            detail=a.detail,
            risk=a.risk,
            resolved=a.resolved,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.get("", response_model=list[schemas.AlertOut])
def list_active_alerts(
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    return _list_alerts(db)


@router.patch("/{alert_id}/resolve", response_model=dict)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    alert = db.query(models.SpoilageAlert).filter(models.SpoilageAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    db.commit()
    return {"id": alert_id, "resolved": True}
