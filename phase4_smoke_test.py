"""Integration smoke test for VisualAgro Phase 4 API endpoints."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure the app directories are on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import app

client = TestClient(app)
DEMO_EMAIL = "ramesh@visualagro.in"
DEMO_PASSWORD = "demo1234"
TEST_IMAGE_PATH = Path("C:/Users/sohan/OneDrive/Documents/VisualAgro Workspace/archive (1)/test/tomato/Image_1.jpg")


def main() -> int:
    print("1. Pinging Root Health Check...")
    resp = client.get("/")
    assert resp.status_code == 200, f"Root ping failed: {resp.text}"
    print(f"✅ Root Response: {resp.json()}")

    print("\n2. Logging in with demo user...")
    resp = client.post(
        "/auth/login",
        data={"username": DEMO_EMAIL, "password": DEMO_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token_data = resp.json()
    token = token_data["access_token"]
    print(f"✅ Login successful, received JWT: {token[:15]}...")

    headers = {"Authorization": f"Bearer {token}"}

    # Verify image classification
    print("\n3. Testing POST /detect with real image...")
    if not TEST_IMAGE_PATH.exists():
        print(f"❌ Test image not found at {TEST_IMAGE_PATH}")
        return 1

    with open(TEST_IMAGE_PATH, "rb") as f:
        files = {"file": ("Image_1.jpg", f.read(), "image/jpeg")}

    resp = client.post("/detect", files=files, headers=headers)
    assert resp.status_code == 200, f"POST /detect failed: {resp.text}"
    detections = resp.json()
    print("✅ POST /detect Response:")
    for d in detections:
        print(f"  - Item: {d['item_name']}, Conf: {d['confidence']}, Category: {d['category']}")
        if "top_k" in d and d["top_k"]:
            print(f"    Top K predictions: {d['top_k']}")

    # Verify vision summary
    print("\n4. Testing GET /vision/summary...")
    resp = client.get("/vision/summary?days=7", headers=headers)
    assert resp.status_code == 200, f"GET /vision/summary failed: {resp.text}"
    summary = resp.json()
    print(f"✅ GET /vision/summary Response:")
    print(f"  - Detected items count: {len(summary['detected_items'])}")
    print(f"  - Present items count: {len(summary['present_items'])}")
    print(f"  - Missing items count: {len(summary['missing_items'])}")
    print(f"  - Total detection events: {summary['detection_events']}")

    # Verify freshness assessment
    print("\n5. Testing POST /freshness...")
    with open(TEST_IMAGE_PATH, "rb") as f:
        files = {"file": ("Image_1.jpg", f.read(), "image/jpeg")}
    resp = client.post("/freshness", data={"item_name": "Tomato"}, files=files, headers=headers)
    assert resp.status_code == 200, f"POST /freshness failed: {resp.text}"
    freshness = resp.json()
    print("✅ POST /freshness Response:")
    print(f"  - Score: {freshness['freshness_score']}, Level: {freshness['freshness_level']}")

    # Verify spoilage prediction
    print("\n6. Testing POST /spoilage...")
    payload = {
        "item_name": "Tomato",
        "freshness_score": 85.0,
        "temperature_c": 24.0,
        "humidity_pct": 65.0,
        "storage_days": 2,
        "quantity": 10.0,
    }
    resp = client.post("/spoilage", json=payload, headers=headers)
    assert resp.status_code == 200, f"POST /spoilage failed: {resp.text}"
    spoilage = resp.json()
    print("✅ POST /spoilage Response:")
    print(f"  - Risk: {spoilage['spoilage_risk']}, Days Remaining: {spoilage['days_remaining']}")

    # Verify forecast consumption
    print("\n7. Testing POST /forecast...")
    payload = {
        "item_name": "Tomato",
        "series": [10.0, 12.0, 11.5, 9.0, 14.0, 13.0, 12.0],
        "horizon_days": 3,
    }
    resp = client.post("/forecast", json=payload, headers=headers)
    assert resp.status_code == 200, f"POST /forecast failed: {resp.text}"
    forecast = resp.json()
    print("✅ POST /forecast Response:")
    print(f"  - Future Demand: {forecast['future_demand']} kg, depletion: {forecast['depletion_date']}")

    # Verify copilot
    print("\n8. Testing POST /copilot...")
    resp = client.post("/copilot", json={"query": "Which items are at high risk of spoilage?"}, headers=headers)
    assert resp.status_code == 200, f"POST /copilot failed: {resp.text}"
    copilot = resp.json()
    print("✅ POST /copilot Response:")
    print(f"  - Answer: {copilot['answer']}")
    print(f"  - Actions: {copilot.get('actions')}")

    # Verify voice query
    print("\n9. Testing POST /voice...")
    resp = client.post("/voice", data={"text": "Tomato count"}, headers=headers)
    assert resp.status_code == 200, f"POST /voice failed: {resp.text}"
    voice = resp.json()
    print("✅ POST /voice Response:")
    print(f"  - Transcript: '{voice['transcript']}'")
    print(f"  - Response: '{voice['response_text']}'")
    print(f"  - Actions: {voice.get('actions')}")

    # Verify manual action execution (central smart database orchestration)
    print("\n10. Testing Smart database orchestration action...")
    resp = client.post("/copilot", json={"query": "Order 25 kg of Onions for tomorrow"}, headers=headers)
    assert resp.status_code == 200, f"Action POST failed: {resp.text}"
    action_res = resp.json()
    print("✅ Orchestrated Copilot Response:")
    print(f"  - Answer: {action_res['answer']}")
    print(f"  - Actions: {action_res.get('actions')}")

    print("\n🎉 All Phase 4 API endpoints verified successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
