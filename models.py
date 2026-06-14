"""
models.py — SQLAlchemy ORM models
Mirrors every data structure used in visualagro_sage.py:
  StockItem, SpoilageAlert, ReorderSuggestion, BestSeller,
  WeeklyMetric, StockLog, Vendor (user)
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Date, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from database import Base


class Vendor(Base):
    """Authenticated vendor / user account."""
    __tablename__ = "vendors"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(120), nullable=False)
    market        = Column(String(200), nullable=True)           # e.g. "Dadar Market, Mumbai"
    email         = Column(String(200), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    stock_logs    = relationship("StockLog",   back_populates="vendor", cascade="all,delete")


class StockItem(Base):
    """Current in-store stock snapshot (latest per item name)."""
    __tablename__ = "stock_items"

    id        = Column(Integer, primary_key=True, index=True)
    emoji     = Column(String(10),  nullable=False)
    name      = Column(String(100), nullable=False, unique=True, index=True)
    qty       = Column(Float,  nullable=False)     # kg remaining
    pct       = Column(Integer, nullable=False)    # % of capacity
    age       = Column(Integer, nullable=False)    # days on shelf
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpoilageAlert(Base):
    """Active spoilage / freshness alerts shown on dashboard."""
    __tablename__ = "spoilage_alerts"

    id        = Column(Integer, primary_key=True, index=True)
    emoji     = Column(String(10),  nullable=False)
    name      = Column(String(100), nullable=False)
    detail    = Column(String(300), nullable=False)
    risk      = Column(String(10),  nullable=False)    # HIGH | MED | LOW
    resolved  = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReorderSuggestion(Base):
    """AI-generated daily reorder list (Exponential Smoothing + Random Forest)."""
    __tablename__ = "reorder_suggestions"

    id        = Column(Integer, primary_key=True, index=True)
    emoji     = Column(String(10),  nullable=False)
    name      = Column(String(100), nullable=False)
    detail    = Column(String(300), nullable=False)
    qty       = Column(Float,  nullable=False)     # kg to buy
    cost      = Column(Integer, nullable=False)    # ₹ estimated cost
    conf      = Column(String(10),  nullable=False)   # HIGH | MED | LOW
    for_date  = Column(Date, default=date.today)


class BestSeller(Base):
    """Weekly best-seller rankings."""
    __tablename__ = "best_sellers"

    id        = Column(Integer, primary_key=True, index=True)
    rank      = Column(Integer, nullable=False)
    emoji     = Column(String(10),  nullable=False)
    name      = Column(String(100), nullable=False)
    sold      = Column(Float,  nullable=False)    # kg sold
    days      = Column(Integer, nullable=False)   # days tracked
    revenue   = Column(Integer, nullable=False)   # ₹ revenue
    week_start = Column(Date, default=date.today)


class WeeklyMetric(Base):
    """Daily revenue + waste figures (feeds bar chart in Insights screen)."""
    __tablename__ = "weekly_metrics"

    id        = Column(Integer, primary_key=True, index=True)
    day_label = Column(String(10), nullable=False)   # Mon, Tue …
    metric_date = Column(Date, nullable=False, index=True)
    revenue   = Column(Integer, nullable=False)
    waste     = Column(Integer, nullable=False)


class SpoilageLoss(Base):
    """Per-item spoilage ₹ loss totals used in the donut/bar chart."""
    __tablename__ = "spoilage_losses"

    id        = Column(Integer, primary_key=True, index=True)
    emoji     = Column(String(10),  nullable=False)
    name      = Column(String(100), nullable=False)
    value     = Column(Integer, nullable=False)    # ₹ loss
    week_start = Column(Date, default=date.today)


class StockLog(Base):
    """End-of-day stock entry submitted from the Stock Entry screen."""
    __tablename__ = "stock_logs"

    id          = Column(Integer, primary_key=True, index=True)
    vendor_id   = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    item_name   = Column(String(100), nullable=False)
    emoji       = Column(String(10),  nullable=True)
    remaining_kg = Column(Float, nullable=False)
    bought_today_kg = Column(Float, nullable=False)
    buy_price   = Column(Float, nullable=False)    # ₹/kg
    sell_price  = Column(Float, nullable=False)    # ₹/kg
    notes       = Column(Text,  nullable=True)
    logged_at   = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="stock_logs")



# ── Phase 4 / Smart Inventory ───────────────────────────────────────

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(120), unique=True, index=True, nullable=False)
    category = Column(String(80), default="produce")
    quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String(20), default="kg")
    freshness_score = Column(Integer, default=100)
    freshness_level = Column(String(30), default="Fresh")
    shelf_life_days = Column(Integer, default=0)
    expiry_date = Column(Date, nullable=True)
    usage_history = Column(Text, nullable=True)
    storage_temp_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    source = Column(String(30), default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_phase4_dict(self):
        return {
            "id": self.id,
            "item_name": self.item_name,
            "category": self.category,
            "quantity": self.quantity,
            "unit": self.unit,
            "freshness_score": self.freshness_score,
            "freshness_level": self.freshness_level,
            "shelf_life_days": self.shelf_life_days,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "usage_history": self.usage_history,
            "storage_temp_c": self.storage_temp_c,
            "humidity_pct": self.humidity_pct,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(120), index=True, nullable=False)
    confidence = Column(Float, nullable=False)
    quantity_detected = Column(Integer, nullable=False, default=1)
    category = Column(String(40), default="inventory_object")
    source_type = Column(String(20), default="image")
    raw_payload = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "item_name": self.item_name,
            "confidence": self.confidence,
            "quantity_detected": self.quantity_detected,
            "category": self.category,
            "source_type": self.source_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "raw_payload": self.raw_payload,
        }


class FreshnessAssessment(Base):
    __tablename__ = "freshness_assessments"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(120), index=True, nullable=False)
    freshness_score = Column(Integer, nullable=False)
    freshness_level = Column(String(30), nullable=False)
    color_score = Column(Float, nullable=False)
    texture_score = Column(Float, nullable=False)
    defect_score = Column(Float, nullable=False)
    mold_score = Column(Float, nullable=False)
    bruise_score = Column(Float, nullable=False)
    raw_payload = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "item_name": self.item_name,
            "freshness_score": self.freshness_score,
            "freshness_level": self.freshness_level,
            "color_score": self.color_score,
            "texture_score": self.texture_score,
            "defect_score": self.defect_score,
            "mold_score": self.mold_score,
            "bruise_score": self.bruise_score,
            "raw_payload": self.raw_payload,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class SpoilagePrediction(Base):
    __tablename__ = "spoilage_predictions"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(120), index=True, nullable=False)
    days_remaining = Column(Integer, nullable=False)
    spoilage_risk = Column(String(10), nullable=False)
    predicted_spoilage_date = Column(Date, nullable=True)
    confidence = Column(Float, nullable=False)
    method = Column(String(80), nullable=False)
    raw_payload = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "item_name": self.item_name,
            "days_remaining": self.days_remaining,
            "spoilage_risk": self.spoilage_risk,
            "predicted_spoilage_date": self.predicted_spoilage_date.isoformat() if self.predicted_spoilage_date else None,
            "confidence": self.confidence,
            "method": self.method,
            "raw_payload": self.raw_payload,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class ConsumptionForecast(Base):
    __tablename__ = "consumption_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(120), index=True, nullable=False)
    predicted_consumption = Column(Float, nullable=False)
    depletion_date = Column(Date, nullable=True)
    future_demand = Column(Float, nullable=False)
    method = Column(String(80), nullable=False)
    confidence = Column(Float, nullable=False)
    raw_payload = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "item_name": self.item_name,
            "predicted_consumption": self.predicted_consumption,
            "depletion_date": self.depletion_date.isoformat() if self.depletion_date else None,
            "future_demand": self.future_demand,
            "method": self.method,
            "confidence": self.confidence,
            "raw_payload": self.raw_payload,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class SmartReorderRecommendation(Base):
    __tablename__ = "smart_reorder_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    item = Column(String(120), index=True, nullable=False)
    reorder_now = Column(Boolean, default=True)
    recommended_quantity = Column(Float, nullable=False)
    priority = Column(String(20), nullable=False)
    reason = Column(String(500), nullable=False)
    confidence = Column(Float, nullable=False)
    raw_payload = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "item": self.item,
            "reorder_now": self.reorder_now,
            "recommended_quantity": self.recommended_quantity,
            "priority": self.priority,
            "reason": self.reason,
            "confidence": self.confidence,
            "raw_payload": self.raw_payload,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
