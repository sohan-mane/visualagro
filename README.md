# 🌿 VisualAgro — FastAPI Backend

Compatible backend for `visualagro_sage.py` (CustomTkinter desktop app).

## Stack
- **FastAPI** + Uvicorn  
- **SQLAlchemy** ORM — SQLite (dev) → PostgreSQL (prod), zero code change  
- **Pydantic v2** schemas  
- **JWT Auth** (HS256, 24 h tokens)  
- **Alembic** migrations ready

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed database with mock data from the desktop app
python seed.py

# 3. Run dev server
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for interactive Swagger UI.

## Demo credentials (created by seed.py)
| Field    | Value                    |
|----------|--------------------------|
| Email    | ramesh@visualagro.in     |
| Password | demo1234                 |

## Project Structure
```
visualagro_api/
├── main.py          ← FastAPI app + CORS + router registration
├── database.py      ← SQLAlchemy engine (SQLite ↔ PostgreSQL toggle)
├── models.py        ← ORM models mirroring all desktop app data
├── schemas.py       ← Pydantic v2 request/response schemas
├── auth.py          ← JWT helpers + password hashing + get_current_vendor
├── seed.py          ← Pre-loads all mock data from visualagro_sage.py
├── alembic.ini      ← Alembic migration config
├── .env.example     ← Environment variable template
└── routers/
    ├── auth.py      ← POST /auth/register  POST /auth/login
    ├── dashboard.py ← GET  /dashboard/stats  /dashboard/alerts
    ├── stock.py     ← CRUD /stock/  +  POST /stock/log
    ├── reorder.py   ← GET  /reorder/  GET /reorder/share
    └── insights.py  ← GET  /insights/weekly  /spoilage  /bestsellers
```

## API Endpoints

| Method | Path | Screen |
|--------|------|--------|
| POST | `/auth/register` | — |
| POST | `/auth/login` | — |
| GET | `/dashboard/stats` | Screen 1 — stat cards |
| GET | `/dashboard/alerts` | Screen 1 — spoilage alerts |
| PATCH | `/dashboard/alerts/{id}/resolve` | Screen 1 |
| GET | `/stock/` | Screen 1 — stock list |
| POST | `/stock/` | Upsert stock item |
| PATCH | `/stock/{id}` | Update qty/pct/age |
| DELETE | `/stock/{id}` | Remove item |
| POST | `/stock/log` | Screen 2 — end-of-day form |
| GET | `/stock/log/history` | Screen 2 — log history |
| GET | `/reorder/` | Screen 3 — buy list |
| POST | `/reorder/` | Add/refresh suggestion |
| GET | `/reorder/share` | Screen 3 — WhatsApp text |
| GET | `/insights/weekly` | Screen 4 — KPIs + chart arrays |
| GET | `/insights/weekly/days` | Screen 4 — raw daily rows |
| GET | `/insights/spoilage` | Screen 4 — spoilage chart |
| GET | `/insights/bestsellers` | Screen 4 — best sellers table |

## Production Deploy (Railway / Render)

```bash
# Set env vars in platform dashboard:
DATABASE_URL=postgresql://user:pass@host/db
SECRET_KEY=your-32-char-secret
TOKEN_EXPIRE_MINUTES=1440

# Start command:
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Upgrade to PostgreSQL
Just change `DATABASE_URL` — SQLAlchemy ORM handles the rest, no code changes needed.

## Phase 2 — Run both together

You now have a one-command launcher plus a smoke test:

```bash
# From the visualagro_api_clean folder
python run_phase2.py
```

That script:
1. seeds the SQLite database
2. starts the FastAPI backend
3. waits for `/` to become reachable
4. opens the desktop app connected to the live API

To verify the full flow manually:

```bash
python phase2_smoke_test.py
```

The smoke test logs in with:
- `ramesh@visualagro.in`
- `demo1234`

It then checks dashboard stats, stock fetch, stock log submit, and history retrieval.



## Phase 4

New APIs are available for:
- /inventory
- /detect
- /freshness
- /spoilage
- /forecast
- /copilot
- /voice

The desktop app also includes a new Phase 4 lab screen for image-based detection, freshness scoring, copilot prompts, and voice-query flow.

## Phase 4 Upgrade

New capabilities added:
- Laptop camera capture for detection and freshness checks
- Real microphone recording for voice queries
- Vision summary endpoint for present / missing / moving / selling items
- Copilot answers that understand vision context
- Optional YOLO + OpenCV + Whisper + edge-tts stack with safe fallbacks

### Train the produce classifier

The bundled archive contains isolated `train`, `validation`, and `test` splits for 36
fruit and vegetable classes. Train the classifier once from this directory:

```bash
python train_vision_model.py --epochs 8
```

This writes the model, JSON history, and accuracy/loss chart to `ai_artifacts/`.
`POST /detect` loads `ai_artifacts/produce_classifier.pt` automatically. Set
`VISION_CLASSIFIER_PATH` to use another checkpoint or `VISION_YOLO_WEIGHTS` to use a
custom YOLO detector ahead of the classifier.

### Phase 4 UI flow
- **Detect Item**: image upload
- **Capture & Detect**: webcam snapshot → detection
- **Freshness Check**: image upload
- **Capture & Score**: webcam snapshot → freshness
- **Voice Query**: typed query or microphone recording
- **Record & Ask**: microphone → transcription → copilot response

### Suggested installs for full voice support
- `sounddevice` for microphone recording
- `faster-whisper` for offline STT
- `edge-tts` for TTS
