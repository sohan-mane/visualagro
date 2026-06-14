"""
routers/stock.py — /stock
Current stock snapshot (Screen 1 right panel) + end-of-day log (Screen 2).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models   import StockItem, StockLog
from schemas  import (
    StockItemCreate, StockItemOut, StockItemUpdate,
    StockLogCreate, StockLogOut,
)
from auth import get_current_vendor
from models import Vendor

router = APIRouter(prefix="/stock", tags=["Stock"])


# ── Current Stock ────────────────────────────────────────────────────

@router.get("/", response_model=list[StockItemOut],
            summary="Get all current stock items (dashboard list)")
def list_stock(db: Session = Depends(get_db), _=Depends(get_current_vendor)):
    return db.query(StockItem).order_by(StockItem.pct.asc()).all()


@router.get("/{item_id}", response_model=StockItemOut,
            summary="Get a single stock item by ID")
def get_stock_item(
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_vendor),
):
    item = db.get(StockItem, item_id)
    if not item:
        raise HTTPException(404, "Stock item not found")
    return item


@router.post("/", response_model=StockItemOut, status_code=201,
             summary="Create or upsert a stock item by name")
def create_stock_item(
    payload: StockItemCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_vendor),
):
    existing = db.query(StockItem).filter(StockItem.name == payload.name).first()
    if existing:
        existing.qty        = payload.qty
        existing.pct        = payload.pct
        existing.age        = payload.age
        existing.emoji      = payload.emoji
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    item = StockItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=StockItemOut,
              summary="Partially update qty / pct / age for a stock item")
def update_stock_item(
    item_id: int,
    payload: StockItemUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_vendor),
):
    item = db.get(StockItem, item_id)
    if not item:
        raise HTTPException(404, "Stock item not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(item, field, val)
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204,
               summary="Remove a stock item")
def delete_stock_item(
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_vendor),
):
    item = db.get(StockItem, item_id)
    if not item:
        raise HTTPException(404, "Stock item not found")
    db.delete(item)
    db.commit()


# ── End-of-Day Stock Log (Screen 2) ─────────────────────────────────

@router.post("/log", response_model=StockLogOut, status_code=201,
             summary="Submit end-of-day stock entry (Screen 2 form)")
def log_stock(
    payload: StockLogCreate,
    db:      Session = Depends(get_db),
    vendor:  Vendor  = Depends(get_current_vendor),
):
    log = StockLog(vendor_id=vendor.id, **payload.model_dump())
    db.add(log)
    db.commit()

    # Auto-update the live stock snapshot
    snap = db.query(StockItem).filter(StockItem.name == payload.item_name).first()
    if snap:
        snap.qty        = payload.remaining_kg
        snap.updated_at = datetime.utcnow()
        db.commit()

    db.refresh(log)
    return log


@router.get("/log/history", response_model=list[StockLogOut],
            summary="Retrieve this vendor's stock log history")
def log_history(
    limit:  int = 50,
    db:     Session = Depends(get_db),
    vendor: Vendor  = Depends(get_current_vendor),
):
    return (
        db.query(StockLog)
        .filter(StockLog.vendor_id == vendor.id)
        .order_by(StockLog.logged_at.desc())
        .limit(limit)
        .all()
    )
