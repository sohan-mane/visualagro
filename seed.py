"""
seed.py — Populate the database with the exact mock data from visualagro_sage.py
Run once:  python seed.py
"""

from datetime import date, timedelta
from database import engine, SessionLocal, Base
from models   import (
    StockItem, SpoilageAlert, ReorderSuggestion,
    BestSeller, WeeklyMetric, SpoilageLoss, Vendor,
)
from auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# ── Demo vendor ──────────────────────────────────────────────────────
if not db.query(Vendor).filter_by(email="ramesh@visualagro.in").first():
    db.add(Vendor(
        name="Ramesh Bhai",
        market="Dadar Market, Mumbai",
        email="ramesh@visualagro.in",
        hashed_password=hash_password("demo1234"),
    ))
    db.commit()
    print("[OK] Demo vendor created -> email: ramesh@visualagro.in | password: demo1234")

# ── Stock Items ──────────────────────────────────────────────────────
STOCK_ITEMS = [
    {"emoji":"🧅","name":"Onions",    "qty":12.0,"pct":80,"age":1},
    {"emoji":"🥔","name":"Potatoes",  "qty":8.0, "pct":55,"age":2},
    {"emoji":"🍅","name":"Tomatoes",  "qty":3.2, "pct":22,"age":2},
    {"emoji":"🥕","name":"Carrots",   "qty":4.0, "pct":40,"age":3},
    {"emoji":"🌿","name":"Coriander", "qty":0.8, "pct":12,"age":3},
    {"emoji":"🧄","name":"Garlic",    "qty":1.5, "pct":60,"age":1},
    {"emoji":"🥬","name":"Spinach",   "qty":1.5, "pct":30,"age":3},
    {"emoji":"🫑","name":"Capsicum",  "qty":2.0, "pct":45,"age":2},
]
for s in STOCK_ITEMS:
    if not db.query(StockItem).filter_by(name=s["name"]).first():
        db.add(StockItem(**s))
db.commit()
print(f"[OK] {len(STOCK_ITEMS)} stock items seeded")

# ── Spoilage Alerts ──────────────────────────────────────────────────
ALERTS = [
    {"emoji":"🍅","name":"Tomatoes",  "detail":"3.2 kg · 2 days on shelf · temp rising","risk":"HIGH"},
    {"emoji":"🌿","name":"Coriander", "detail":"0.8 kg · soft leaves detected",          "risk":"MED"},
    {"emoji":"🥬","name":"Spinach",   "detail":"1.5 kg · 3 days old",                    "risk":"MED"},
]
for a in ALERTS:
    if not db.query(SpoilageAlert).filter_by(name=a["name"], resolved=False).first():
        db.add(SpoilageAlert(**a))
db.commit()
print(f"[OK] {len(ALERTS)} spoilage alerts seeded")

# ── Reorder Suggestions ──────────────────────────────────────────────
REORDER = [
    {"emoji":"🧅","name":"Onions",    "detail":"15 kg · running low · festival demand",       "qty":15,"cost":300,"conf":"HIGH"},
    {"emoji":"🍅","name":"Tomatoes",  "detail":"6 kg · restock critical · discount old stock","qty":6, "cost":168,"conf":"HIGH"},
    {"emoji":"🥔","name":"Potatoes",  "detail":"10 kg · steady demand",                       "qty":10,"cost":180,"conf":"HIGH"},
    {"emoji":"🥬","name":"Spinach",   "detail":"3 kg · weekend boost predicted",              "qty":3, "cost":90, "conf":"MED"},
    {"emoji":"🧄","name":"Garlic",    "detail":"2 kg · slow week · buy less",                 "qty":2, "cost":200,"conf":"MED"},
    {"emoji":"🌿","name":"Coriander", "detail":"1 kg · high turnover daily",                  "qty":1, "cost":40, "conf":"HIGH"},
    {"emoji":"🫑","name":"Capsicum",  "detail":"2 kg · uncertain demand",                     "qty":2, "cost":160,"conf":"LOW"},
    {"emoji":"🥕","name":"Carrots",   "detail":"5 kg · mid-week dip predicted",               "qty":5, "cost":110,"conf":"MED"},
]
today = date.today()
for r in REORDER:
    if not db.query(ReorderSuggestion).filter_by(name=r["name"], for_date=today).first():
        db.add(ReorderSuggestion(**r, for_date=today))
db.commit()
print(f"[OK] {len(REORDER)} reorder suggestions seeded")

# ── Best Sellers ─────────────────────────────────────────────────────
BESTSELLERS = [
    {"rank":1,"emoji":"🧅","name":"Onions",   "sold":82,"days":6,"revenue":2870},
    {"rank":2,"emoji":"🥔","name":"Potatoes", "sold":64,"days":7,"revenue":1920},
    {"rank":3,"emoji":"🍅","name":"Tomatoes", "sold":38,"days":5,"revenue":1900},
    {"rank":4,"emoji":"🥕","name":"Carrots",  "sold":30,"days":7,"revenue":1200},
    {"rank":5,"emoji":"🧄","name":"Garlic",   "sold":18,"days":4,"revenue":1800},
]
week_start = today - timedelta(days=today.weekday())
for b in BESTSELLERS:
    if not db.query(BestSeller).filter_by(name=b["name"], week_start=week_start).first():
        db.add(BestSeller(**b, week_start=week_start))
db.commit()
print(f"[OK] {len(BESTSELLERS)} best sellers seeded")

# ── Weekly Metrics ───────────────────────────────────────────────────
WEEKLY_DATA = [
    ("Mon", 1400, 280), ("Tue", 1620, 240), ("Wed", 1380, 380),
    ("Thu", 1840, 220), ("Fri", 2100, 180), ("Sat", 1880, 200), ("Sun", 1200, 120),
]
base_date = today - timedelta(days=6)
for i, (label, rev, waste) in enumerate(WEEKLY_DATA):
    d = base_date + timedelta(days=i)
    if not db.query(WeeklyMetric).filter_by(metric_date=d).first():
        db.add(WeeklyMetric(day_label=label, metric_date=d, revenue=rev, waste=waste))
db.commit()
print("[OK] 7 weekly metrics seeded")

# ── Spoilage Losses ──────────────────────────────────────────────────
SPOILAGE = [
    {"emoji":"🍅","name":"Tomatoes",  "value":420},
    {"emoji":"🥬","name":"Spinach",   "value":310},
    {"emoji":"🌿","name":"Coriander", "value":220},
    {"emoji":"🫑","name":"Capsicum",  "value":190},
    {"emoji":"🥕","name":"Carrots",   "value":100},
]
for sp in SPOILAGE:
    if not db.query(SpoilageLoss).filter_by(name=sp["name"], week_start=week_start).first():
        db.add(SpoilageLoss(**sp, week_start=week_start))
db.commit()
print(f"[OK] {len(SPOILAGE)} spoilage loss records seeded")

db.close()
print("\nVisualAgro database ready!")
