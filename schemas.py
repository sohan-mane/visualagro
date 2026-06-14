"""
schemas.py — Pydantic v2 request / response models
One In + one Out schema per resource; keeps API contract explicit.
"""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


# ── Vendor / Auth ────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name:     str
    market:   Optional[str] = None
    email:    EmailStr
    password: str

class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    name:       str
    market:     Optional[str]
    email:      EmailStr
    is_active:  bool
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type:   str = "bearer"

class TokenData(BaseModel):
    vendor_id: Optional[int] = None


# ── Stock Items ──────────────────────────────────────────────────────

class StockItemCreate(BaseModel):
    emoji: str
    name:  str
    qty:   float
    pct:   int
    age:   int

class StockItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    emoji:      str
    name:       str
    qty:        float
    pct:        int
    age:        int
    updated_at: datetime

class StockItemUpdate(BaseModel):
    qty:   Optional[float] = None
    pct:   Optional[int]   = None
    age:   Optional[int]   = None


# ── Spoilage Alerts ──────────────────────────────────────────────────

class SpoilageAlertCreate(BaseModel):
    emoji:  str
    name:   str
    detail: str
    risk:   str   # HIGH | MED | LOW

class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    emoji:      str
    name:       str
    detail:     str
    risk:       str
    resolved:   bool
    created_at: datetime

# Backwards-compatible name used by older code
SpoilageAlertOut = AlertOut


# ── Reorder Suggestions ──────────────────────────────────────────────

class ReorderSuggestionCreate(BaseModel):
    emoji:    str
    name:     str
    detail:   str
    qty:      float
    cost:     int
    conf:     str
    for_date: Optional[date] = None

class ReorderSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:       int
    emoji:    str
    name:     str
    detail:   str
    qty:      float
    cost:     int
    conf:     str
    for_date: date
    priority: Optional[str] = None
    reason: Optional[str] = None
    confidence: Optional[float] = None


# ── Best Sellers ─────────────────────────────────────────────────────

class BestSellerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    rank:       int
    emoji:      str
    name:       str
    sold:       float
    days:       int
    revenue:    int
    week_start: date


# ── Weekly Metrics ───────────────────────────────────────────────────

class WeeklyMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:          int
    day_label:   str
    metric_date: date
    revenue:     int
    waste:       int

class WeeklySummary(BaseModel):
    """Aggregated weekly summary used by the Insights KPI row."""
    total_revenue:    int
    total_waste:      int
    avg_daily:        int
    best_margin_note: str
    labels:  list[str]
    revenue: list[int]
    waste:   list[int]


# ── Spoilage Loss ────────────────────────────────────────────────────

class SpoilageLossOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    emoji:      str
    name:       str
    value:      int
    week_start: date


# ── Stock Log (End-of-Day Entry) ─────────────────────────────────────

class StockLogCreate(BaseModel):
    item_name:       str
    emoji:           Optional[str] = None
    remaining_kg:    float
    bought_today_kg: float
    buy_price:       float
    sell_price:      float
    notes:           Optional[str] = None

class StockLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              int
    item_name:       str
    emoji:           Optional[str]
    remaining_kg:    float
    bought_today_kg: float
    buy_price:       float
    sell_price:      float
    notes:           Optional[str]
    logged_at:       datetime


# ── Dashboard Stats ──────────────────────────────────────────────────

class DashboardStats(BaseModel):
    today_revenue:   str
    revenue_change:   str
    waste_cost:       str
    waste_change:     str
    items_in_stock:   int
    critically_low:   int
    ai_forecast:      str
    forecast_label:   str



# ── Phase 4 / Smart Inventory ───────────────────────────────────────

class InventoryItemCreate(BaseModel):
    item_name: str
    category: str = "produce"
    quantity: float
    unit: str = "kg"
    freshness_score: int = 100
    freshness_level: str = "Fresh"
    shelf_life_days: int = 0
    expiry_date: Optional[date] = None
    usage_history: Optional[str] = None
    storage_temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    source: str = "manual"

class InventoryItemUpdate(BaseModel):
    item_name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    freshness_score: Optional[int] = None
    freshness_level: Optional[str] = None
    shelf_life_days: Optional[int] = None
    expiry_date: Optional[date] = None
    usage_history: Optional[str] = None
    storage_temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    source: Optional[str] = None

class InventoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_name: str
    category: str
    quantity: float
    unit: str
    freshness_score: int
    freshness_level: str
    shelf_life_days: int
    expiry_date: Optional[date]
    usage_history: Optional[str]
    storage_temp_c: Optional[float]
    humidity_pct: Optional[float]
    source: str
    created_at: datetime
    updated_at: datetime

class DetectionOut(BaseModel):
    item_name: str
    confidence: float
    quantity_detected: int
    timestamp: str
    category: str = "inventory_object"
    top_k: Optional[list[dict]] = None


class FreshnessAssessmentOut(BaseModel):
    item_name: str
    freshness_score: int
    freshness_level: str
    timestamp: str
    color_score: float
    texture_score: float
    defect_score: float
    mold_score: float
    bruise_score: float

class SpoilagePredictRequest(BaseModel):
    item_name: str
    freshness_score: float
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    storage_days: Optional[int] = None
    quantity: Optional[float] = None

class SpoilagePredictionOut(BaseModel):
    item_name: str
    days_remaining: int
    spoilage_risk: str
    predicted_spoilage_date: str
    confidence: float
    method: str
    timestamp: str

class ForecastRequest(BaseModel):
    item_name: str
    series: Optional[list[float]] = None
    horizon_days: int = 7

class ForecastOut(BaseModel):
    item_name: str
    predicted_consumption: float
    depletion_date: str
    future_demand: float
    method: str
    confidence: float
    timestamp: str

class CopilotRequest(BaseModel):
    query: str

class CopilotResponse(BaseModel):
    intent: str
    answer: str
    evidence: list[dict]
    timestamp: str
    actions: Optional[list[dict]] = None

class VoiceResponse(BaseModel):
    mode: str
    transcript: str
    response_text: str
    stt_available: bool
    tts_available: bool
    actions: Optional[list[dict]] = None

class SmartReorderRecommendationOut(BaseModel):
    item: str
    reorder_now: bool
    recommended_quantity: float
    priority: str
    reason: str
    confidence: float
    timestamp: str


class VisionSummaryOut(BaseModel):
    generated_at: str
    window_days: int
    detected_items: list[dict]
    present_items: list[dict]
    missing_items: list[dict]
    top_selling_items: list[dict]
    detection_events: int
    inventory_items: int
    stock_logs: int
