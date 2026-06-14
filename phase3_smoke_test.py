
"""
phase3_smoke_test.py — Verify the Phase 3 AI brain end-to-end.
"""

from __future__ import annotations

from pprint import pprint
import sys

from api_client import VisualAgroAPI, BASE_URL

DEMO_EMAIL = "ramesh@visualagro.in"
DEMO_PASSWORD = "demo1234"


def main() -> int:
    api = VisualAgroAPI(BASE_URL)

    print(f"Checking backend at {BASE_URL} ...")
    if not api.ping():
        print("❌ Backend is not reachable.")
        return 1

    print("Logging in ...")
    api.login(DEMO_EMAIL, DEMO_PASSWORD)
    print("✅ Login successful")

    status = api.get_ai_status()
    print("✅ AI status:")
    pprint(status)

    trained = api.train_ai()
    print("✅ AI trained / refreshed:")
    pprint(trained)

    stock = api.get_stock_items()
    item = stock[0]["name"]
    print(f"Predicting demand for {item} ...")
    demand = api.predict_demand(item)
    pprint(demand)

    print(f"Predicting spoilage for {item} ...")
    spoilage = api.predict_spoilage(item)
    pprint(spoilage)

    refresh = api.refresh_ai_reorder()
    print("✅ Reorder refreshed:")
    pprint(refresh)

    reorder = api.get_reorder_suggestions()
    print(f"✅ Reorder list fetched ({len(reorder)} items)")
    if not reorder:
        print("❌ Reorder list is empty")
        return 1

    print("\n🎉 Phase 3 smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
