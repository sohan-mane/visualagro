"""
phase2_smoke_test.py — Verify Phase 2 end-to-end integration.

Checks:
  - backend reachability
  - login with demo credentials
  - dashboard stats + stock snapshot fetch
  - stock log submit
  - stock log history fetch
"""

from __future__ import annotations

import sys
from pprint import pprint

from api_client import VisualAgroAPI, BASE_URL


DEMO_EMAIL = "ramesh@visualagro.in"
DEMO_PASSWORD = "demo1234"


def main() -> int:
    api = VisualAgroAPI(BASE_URL)

    print(f"Checking backend at {BASE_URL} ...")
    if not api.ping():
        print("❌ Backend is not reachable.")
        return 1
    print("✅ Backend reachable")

    print("Logging in with demo credentials ...")
    api.login(DEMO_EMAIL, DEMO_PASSWORD)
    print("✅ Login successful")

    stats = api.get_dashboard_stats()
    print("✅ Dashboard stats:")
    pprint(stats)

    stock = api.get_stock_items()
    print(f"✅ Stock snapshot loaded ({len(stock)} items)")
    tomatoes = next((item for item in stock if item["name"].lower() == "tomatoes"), stock[0])

    print(f"Submitting one test stock log for: {tomatoes['name']} ...")
    result = api.submit_stock_log(
        item_name=tomatoes["name"],
        emoji=tomatoes.get("emoji", "🍅"),
        remaining_kg=float(tomatoes["qty"]),
        bought_today_kg=1.0,
        buy_price=28.0,
        sell_price=50.0,
        notes="Phase 2 smoke test",
    )
    print("✅ Stock log submitted:")
    pprint(result)

    history = api.get_stock_log_history(limit=5)
    print(f"✅ History fetched ({len(history)} entries)")
    if not history:
        print("❌ History is empty after submission.")
        return 1

    latest = history[0]
    print("Latest history entry:")
    pprint(latest)

    print("\n🎉 Phase 2 smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
