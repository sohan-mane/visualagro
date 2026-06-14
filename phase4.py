
"""
Phase-4 smart inventory router.
Provides /detect, /freshness, /spoilage, /forecast, /copilot, /voice, /vision/summary.
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile, Query
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_vendor
from database import get_db
from phase4 import VisionEngine, FreshnessEngine, SpoilageEngine, ForecastEngine, CopilotEngine, VoiceAssistant
from phase4.analytics import VisionAnalyticsEngine

router = APIRouter(tags=["Phase4"])

vision = VisionEngine()
freshness_engine = FreshnessEngine()
spoilage_engine = SpoilageEngine()
forecast_engine = ForecastEngine()
copilot_engine = CopilotEngine()
voice_assistant = VoiceAssistant()
vision_analytics = VisionAnalyticsEngine()


@router.post("/detect", response_model=list[schemas.DetectionOut])
async def detect(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    data = await file.read()
    detections = vision.detect(data)
    _save_detections(db, detections)
    return detections


@router.post("/freshness", response_model=schemas.FreshnessAssessmentOut)
async def freshness(
    file: UploadFile = File(...),
    item_name: str = Form(""),
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    data = await file.read()
    result = freshness_engine.assess(data, item_name=item_name or file.filename or "unknown")
    _save_freshness(db, result)
    return result


@router.post("/spoilage", response_model=schemas.SpoilagePredictionOut)
def spoilage(
    payload: schemas.SpoilagePredictRequest,
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    result = spoilage_engine.predict(
        item_name=payload.item_name,
        freshness_score=payload.freshness_score,
        temperature_c=payload.temperature_c,
        humidity_pct=payload.humidity_pct,
        storage_days=payload.storage_days,
        quantity=payload.quantity,
    )
    _save_spoilage(db, result)
    return result


@router.post("/forecast", response_model=schemas.ForecastOut)
def forecast(
    payload: schemas.ForecastRequest,
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    series = payload.series or _series_from_inventory(db, payload.item_name)
    result = forecast_engine.forecast(series, payload.item_name, payload.horizon_days)
    _save_forecast(db, result)
    return result


@router.post("/copilot", response_model=schemas.CopilotResponse)
def copilot(
    payload: schemas.CopilotRequest,
    db: Session = Depends(get_db),
    vendor: models.Vendor = Depends(get_current_vendor),
):
    context = _build_copilot_context(db)
    context["timestamp"] = datetime.utcnow().isoformat()
    res = copilot_engine.respond(payload.query, context)
    actions = res.get("actions", [])
    if actions:
        _execute_copilot_actions(db, actions, vendor.id)
    return res


@router.post("/voice", response_model=schemas.VoiceResponse)
async def voice(
    file: UploadFile | None = File(None),
    text: str = Form(""),
    db: Session = Depends(get_db),
    vendor: models.Vendor = Depends(get_current_vendor),
):
    audio = await file.read() if file else None
    result = voice_assistant.transcribe(audio_bytes=audio, text_fallback=text)
    if result.get("transcript"):
        context = _build_copilot_context(db)
        context["timestamp"] = datetime.utcnow().isoformat()
        c = copilot_engine.respond(result["transcript"], context)
        result["response_text"] = c["answer"]
        result["mode"] = "voice_query"
        result["actions"] = c.get("actions", [])
        if result["actions"]:
            _execute_copilot_actions(db, result["actions"], vendor.id)
    return result


@router.get("/vision/summary", response_model=schemas.VisionSummaryOut)
def vision_summary(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: models.Vendor = Depends(get_current_vendor),
):
    return vision_analytics.summarize(db, days=days)


def _save_detections(db: Session, detections: list[dict]):
    for det in detections:
        db.add(
            models.DetectionEvent(
                item_name=det["item_name"],
                confidence=float(det.get("confidence", 0)),
                quantity_detected=int(det.get("quantity_detected", 1)),
                category=det.get("category", "inventory_object"),
                source_type="image",
                raw_payload=str(det),
            )
        )
    db.commit()


def _save_freshness(db: Session, result: dict):
    db.add(
        models.FreshnessAssessment(
            item_name=result.get("item_name", "unknown"),
            freshness_score=int(result.get("freshness_score", 0)),
            freshness_level=result.get("freshness_level", "Unknown"),
            color_score=float(result.get("color_score", 0)),
            texture_score=float(result.get("texture_score", 0)),
            defect_score=float(result.get("defect_score", 0)),
            mold_score=float(result.get("mold_score", 0)),
            bruise_score=float(result.get("bruise_score", 0)),
            raw_payload=str(result),
        )
    )
    db.commit()


def _save_spoilage(db: Session, result: dict):
    predicted = result.get("predicted_spoilage_date")
    try:
        predicted_date = date.fromisoformat(predicted) if predicted else None
    except Exception:
        predicted_date = None
    db.add(
        models.SpoilagePrediction(
            item_name=result.get("item_name", "unknown"),
            days_remaining=int(result.get("days_remaining", 0)),
            spoilage_risk=result.get("spoilage_risk", "LOW"),
            predicted_spoilage_date=predicted_date,
            confidence=float(result.get("confidence", 0)),
            method=result.get("method", "rules"),
            raw_payload=str(result),
        )
    )
    db.commit()


def _save_forecast(db: Session, result: dict):
    depletion = result.get("depletion_date")
    try:
        depletion_date = date.fromisoformat(depletion) if depletion else None
    except Exception:
        depletion_date = None
    db.add(
        models.ConsumptionForecast(
            item_name=result.get("item_name", "unknown"),
            predicted_consumption=float(result.get("predicted_consumption", 0)),
            depletion_date=depletion_date,
            future_demand=float(result.get("future_demand", 0)),
            method=result.get("method", "moving_average"),
            confidence=float(result.get("confidence", 0)),
            raw_payload=str(result),
        )
    )
    db.commit()


def _series_from_inventory(db: Session, item_name: str) -> list[float]:
    item = db.query(models.InventoryItem).filter(models.InventoryItem.item_name.ilike(f"%{item_name}%")).first()
    if item and item.usage_history:
        try:
            import json
            data = json.loads(item.usage_history)
            if isinstance(data, list):
                return [float(x) for x in data if x is not None]
        except Exception:
            pass
    logs = db.query(models.StockLog).filter(models.StockLog.item_name.ilike(f"%{item_name}%")).order_by(models.StockLog.logged_at.asc()).all()
    if logs:
        return [max(float(l.bought_today_kg) - float(l.remaining_kg), 0.0) for l in logs]
    return [0.0, 0.0, 0.0]


def _build_copilot_context(db: Session) -> dict:
    inventory = [i.to_phase4_dict() for i in db.query(models.InventoryItem).all()]
    if not inventory:
        inventory = [
            {
                "item_name": s.name,
                "quantity": s.qty,
                "unit": "kg",
                "freshness_score": max(0, min(100, int(s.pct))),
                "freshness_level": "Fresh" if s.pct >= 80 else "Good" if s.pct >= 60 else "Aging" if s.pct >= 35 else "Near Spoilage",
            }
            for s in db.query(models.StockItem).all()
        ]

    freshness = [x.to_dict() for x in db.query(models.FreshnessAssessment).order_by(models.FreshnessAssessment.timestamp.desc()).limit(10).all()]
    spoilage = [x.to_dict() for x in db.query(models.SpoilagePrediction).order_by(models.SpoilagePrediction.timestamp.desc()).limit(10).all()]
    forecast = [x.to_dict() for x in db.query(models.ConsumptionForecast).order_by(models.ConsumptionForecast.timestamp.desc()).limit(10).all()]
    smart = db.query(models.SmartReorderRecommendation).order_by(models.SmartReorderRecommendation.timestamp.desc()).limit(10).all()
    if smart:
        reorder = [x.to_dict() for x in smart]
    else:
        reorder = [x.to_dict() for x in db.query(models.ReorderSuggestion).order_by(models.ReorderSuggestion.for_date.desc()).limit(10).all()]

    vision_context = vision_analytics.summarize(db, days=7, top_n=5)
    
    last_det = db.query(models.DetectionEvent).order_by(models.DetectionEvent.timestamp.desc()).first()
    last_fresh = db.query(models.FreshnessAssessment).order_by(models.FreshnessAssessment.timestamp.desc()).first()
    
    last_scan = {}
    if last_det:
        last_scan["detected_item"] = last_det.item_name
        last_scan["detection_confidence"] = last_det.confidence
        last_scan["detection_time"] = last_det.timestamp.isoformat() if last_det.timestamp else None
    if last_fresh:
        last_scan["freshness_item"] = last_fresh.item_name
        last_scan["freshness_score"] = last_fresh.freshness_score
        last_scan["freshness_level"] = last_fresh.freshness_level
        last_scan["freshness_time"] = last_fresh.timestamp.isoformat() if last_fresh.timestamp else None

    return {
        "inventory": inventory,
        "freshness": freshness,
        "spoilage": spoilage,
        "forecast": forecast,
        "reorder": reorder,
        "vision": vision_context,
        "last_scan": last_scan,
    }


def _execute_copilot_actions(db: Session, actions: list[dict], vendor_id: int):
    for action in actions:
        try:
            a_type = action.get("type")
            params = action.get("parameters", {})
            if not params:
                continue
            
            if a_type == "create_reorder_suggestion":
                db.add(models.ReorderSuggestion(
                    emoji=params.get("emoji", "🥦"),
                    name=params.get("item_name", "Unknown Item"),
                    detail=params.get("detail", "AI recommended reorder"),
                    qty=float(params.get("qty", 10.0)),
                    cost=int(params.get("cost", 0) or (float(params.get("qty", 10.0)) * 30)),
                    conf=params.get("conf", params.get("risk", "HIGH")),
                    for_date=date.today()
                ))
                
            elif a_type == "update_inventory":
                item_name = params.get("item_name")
                if item_name:
                    inv_item = db.query(models.InventoryItem).filter(models.InventoryItem.item_name.ilike(f"%{item_name}%")).first()
                    if inv_item:
                        if "qty" in params:
                            inv_item.quantity = float(params["qty"])
                        if "freshness_score" in params:
                            inv_item.freshness_score = int(params["freshness_score"])
                            inv_item.freshness_level = params.get("freshness_level", "Fresh" if inv_item.freshness_score >= 80 else "Good" if inv_item.freshness_score >= 60 else "Aging" if inv_item.freshness_score >= 35 else "Near Spoilage")
                    else:
                        db.add(models.InventoryItem(
                            item_name=item_name,
                            category=params.get("category", "produce"),
                            quantity=float(params.get("qty", 0.0)),
                            unit=params.get("unit", "kg"),
                            freshness_score=int(params.get("freshness_score", 100)),
                            freshness_level=params.get("freshness_level", "Fresh"),
                            shelf_life_days=int(params.get("shelf_life_days", 5)),
                            expiry_date=date.today()
                        ))
                    stock_item = db.query(models.StockItem).filter(models.StockItem.name.ilike(f"%{item_name}%")).first()
                    if stock_item:
                        if "qty" in params:
                            stock_item.qty = float(params["qty"])
                            stock_item.pct = min(100, int((stock_item.qty / 100.0) * 100))
                    else:
                        db.add(models.StockItem(
                            emoji=params.get("emoji", "🥦"),
                            name=item_name,
                            qty=float(params.get("qty", 0.0)),
                            pct=min(100, int((float(params.get("qty", 0.0)) / 100.0) * 100)),
                            age=0
                        ))
                        
            elif a_type == "resolve_alert":
                item_name = params.get("item_name")
                if item_name:
                    alerts = db.query(models.SpoilageAlert).filter(
                        models.SpoilageAlert.name.ilike(f"%{item_name}%"),
                        models.SpoilageAlert.resolved == False
                    ).all()
                    for alert in alerts:
                        alert.resolved = True
                        
            elif a_type == "create_spoilage_alert":
                db.add(models.SpoilageAlert(
                    emoji=params.get("emoji", "🥦"),
                    name=params.get("item_name", "Unknown Item"),
                    detail=params.get("detail", "Alert triggered by smart assistant"),
                    risk=params.get("risk", "HIGH"),
                    resolved=False
                ))
                
            elif a_type == "log_stock":
                db.add(models.StockLog(
                    vendor_id=vendor_id,
                    item_name=params.get("item_name", "Unknown Item"),
                    emoji=params.get("emoji", "🥦"),
                    remaining_kg=float(params.get("remaining_kg", 0.0)),
                    bought_today_kg=float(params.get("bought_today_kg", 0.0)),
                    buy_price=float(params.get("buy_price", 30.0)),
                    sell_price=float(params.get("sell_price", 50.0)),
                    notes=params.get("notes", "Logged by AI Copilot")
                ))
                
            db.commit()
        except Exception as exc:
            db.rollback()
            print(f"Failed to execute action {action}: {exc}")
