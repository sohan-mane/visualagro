"""
Phase-4 inventory CRUD router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_vendor
from database import get_db

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=list[schemas.InventoryItemOut])
def list_inventory(
    q: str | None = Query(None, description="Search by item name"),
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    query = db.query(models.InventoryItem)
    if q:
        query = query.filter(models.InventoryItem.item_name.ilike(f"%{q}%"))
    return query.order_by(models.InventoryItem.updated_at.desc()).all()


@router.post("", response_model=schemas.InventoryItemOut, status_code=201)
def create_inventory_item(
    payload: schemas.InventoryItemCreate,
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    existing = db.query(models.InventoryItem).filter(models.InventoryItem.item_name.ilike(f"%{payload.item_name}%")).first()
    if existing:
        for field, val in payload.model_dump(exclude_none=True).items():
            setattr(existing, field, val)
        db.commit()
        db.refresh(existing)
        return existing
    item = models.InventoryItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=schemas.InventoryItemOut)
def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    item = db.get(models.InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.patch("/{item_id}", response_model=schemas.InventoryItemOut)
def update_inventory_item(
    item_id: int,
    payload: schemas.InventoryItemUpdate,
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    item = db.get(models.InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(item, field, val)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    item = db.get(models.InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    db.delete(item)
    db.commit()
