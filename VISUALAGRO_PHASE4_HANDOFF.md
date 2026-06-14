# VisualAgro Phase-4 Handoff

## 1) Architecture audit

### What existed
- FastAPI backend with JWT auth
- SQLite/SQLAlchemy persistence
- Desktop app in `visualagro_connected.py`
- Phase-3 AI brain for demand, spoilage, revenue, reorder
- Dashboard / stock / insights / alerts routers

### Reusable parts kept
- `database.py`, `auth.py`
- Existing `routers/*`
- Existing `ai/brain.py` forecasting and reorder logic
- Existing desktop client and API client
- Existing SQLite seed data and smoke tests

### Technical debt found
- No Phase-4 service layer
- No inventory CRUD table dedicated to freshness + shelf-life
- No image-based detection endpoints
- No copilot / voice abstraction
- No clean route for freshness/spoilage/forecast as first-class APIs
- Frontend had no Phase-4 entry point

### Bottlenecks removed / reduced
- Added modular service package under `phase4/`
- Added new routers for inventory and smart operations
- Added fallback heuristics for environments without YOLO / Whisper models
- Kept backward compatibility with the current Phase-3 routes

## 2) New folder structure

```text
visualagro_api_clean/
├── phase4/
│   ├── __init__.py
│   ├── utils.py
│   ├── vision.py
│   ├── freshness.py
│   ├── spoilage.py
│   ├── forecast.py
│   ├── reorder.py
│   ├── copilot.py
│   └── voice.py
├── routers/
│   ├── inventory.py
│   └── phase4.py
├── main.py
├── models.py
├── schemas.py
├── api_client.py
├── visualagro_connected.py
└── requirements.txt
```

## 3) File-by-file change log

### Modified
- `main.py`
  - Registered new routers: `inventory` and `phase4`
- `models.py`
  - Added Phase-4 tables:
    - `inventory_items`
    - `detection_events`
    - `freshness_assessments`
    - `spoilage_predictions`
    - `consumption_forecasts`
    - `smart_reorder_recommendations`
- `schemas.py`
  - Added Pydantic models for inventory, detection, freshness, spoilage, forecast, copilot, voice
  - Extended reorder response schema for future Phase-4 fields
- `api_client.py`
  - Added methods for detect, freshness, spoilage, inventory, forecast, copilot, voice
- `visualagro_connected.py`
  - Added a new `Phase4Screen`
  - Added the Phase-4 item in sidebar navigation
  - Added image detection, freshness scoring, copilot, and voice query actions
- `requirements.txt`
  - Added optional Phase-4 dependencies
- `main.py` / router wiring
  - Preserved all existing Phase-3 endpoints

### Added
- `phase4/__init__.py`
- `phase4/utils.py`
- `phase4/vision.py`
- `phase4/freshness.py`
- `phase4/spoilage.py`
- `phase4/forecast.py`
- `phase4/reorder.py`
- `phase4/copilot.py`
- `phase4/voice.py`
- `routers/inventory.py`
- `routers/phase4.py`

## 4) What the new code does

### Vision layer
- `POST /detect`
- Accepts image upload
- Uses YOLOv8 when a weights file is provided and `ultralytics` is installed
- Falls back to OpenCV heuristics if no model is present

### Freshness layer
- `POST /freshness`
- Produces:
  - freshness score
  - freshness level
  - color / texture / defect / mold / bruise sub-scores

### Spoilage layer
- `POST /spoilage`
- Predicts:
  - days remaining
  - spoilage risk
  - predicted spoilage date

### Inventory layer
- `GET /inventory`
- `POST /inventory`
- `GET /inventory/{id}`
- `PATCH /inventory/{id}`
- `DELETE /inventory/{id}`

### Forecasting layer
- `POST /forecast`
- Predicts consumption, depletion date, and future demand
- Uses ARIMA when enough history exists, with fallback to exponential smoothing / moving average

### Copilot layer
- `POST /copilot`
- Answers natural-language inventory questions using structured context

### Voice layer
- `POST /voice`
- Supports text-first voice flow
- STT/TTS are abstracted so real models can be plugged in later

## 5) New dependencies
Added as optional / production-targeted dependencies:
- `opencv-python-headless`
- `ultralytics`
- `faster-whisper`
- `edge-tts`

Existing stack retained:
- FastAPI
- SQLAlchemy
- scikit-learn
- statsmodels
- pandas / numpy
- requests
- CustomTkinter
- Matplotlib

## 6) Database schema

### New tables
- `inventory_items`
- `detection_events`
- `freshness_assessments`
- `spoilage_predictions`
- `consumption_forecasts`
- `smart_reorder_recommendations`

### Future migration readiness
- SQLite works locally now
- Tables are model-driven and can be migrated to PostgreSQL / Supabase later
- New tables are separate from legacy Phase-3 tables, so backward compatibility is preserved

## 7) API documentation

### Phase-4 endpoints
- `POST /detect`
- `POST /freshness`
- `POST /spoilage`
- `GET /inventory`
- `POST /inventory`
- `GET /inventory/{id}`
- `PATCH /inventory/{id}`
- `DELETE /inventory/{id}`
- `POST /forecast`
- `POST /copilot`
- `POST /voice`

### Existing endpoints preserved
- `/auth/*`
- `/dashboard/*`
- `/stock/*`
- `/reorder/*`
- `/insights/*`
- `/alerts/*`
- `/ai/*`

## 8) Integration guide

### Backend
- Run `Base.metadata.create_all(bind=engine)` on startup
- Start FastAPI normally
- Existing Phase-3 routes continue to work

### Desktop app
- Log in as before
- Open **Phase 4** from the sidebar
- Use:
  - image detection
  - freshness scoring
  - copilot query
  - voice query flow

### API client
- New methods were added to support the Phase-4 screen and external automation

## 9) Deployment guide

### Local
```bash
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload
```

### Production
- Set `DATABASE_URL` to PostgreSQL / Supabase
- Set `SECRET_KEY`
- Optionally provide:
  - YOLO weights path
  - Whisper / TTS backends
- Use `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Notes
- YOLO / Whisper are optional in this build
- If absent, the code falls back to heuristic detection and text-based voice flow

## 10) Future scaling recommendations
- Move from SQLite to PostgreSQL
- Add Alembic migrations for the new Phase-4 tables
- Store uploaded media in object storage
- Add real YOLO custom weights for vendor produce
- Add a trained spoilage model per item category
- Add WebSocket live refresh for dashboard panels
- Add mobile client after backend API stabilizes
- Add audit logs for vendor actions
- Add model version tracking and retraining jobs

## 11) Assumptions used
- No pretrained YOLO or Whisper model files were bundled in the ZIP
- Phase-4 endpoints must remain usable even without those heavy models
- Existing Phase-3 routes should stay intact
- Desktop app remains the primary frontend for now

## 12) Validation status
- Python syntax validated across the modified project
- Runtime import validation in this sandbox is limited by missing installed backend packages such as SQLAlchemy
