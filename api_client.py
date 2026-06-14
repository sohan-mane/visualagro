"""
api_client.py — HTTP client for VisualAgro FastAPI backend
FIXED: reduced timeouts (6s default, 3s for ping/login)
"""

from __future__ import annotations
from datetime import date
import os
from typing import Optional
import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_DEFAULT = 6      # was 10 — snappier failure detection
TIMEOUT_LOGIN   = 6      # login-specific
TIMEOUT_PING    = 2      # very quick reachability check
TIMEOUT_HEAVY   = 300    # was 120 — local LLM and voice operations on CPU can take longer


class VisualAgroAPI:
    """
    Thin wrapper around the VisualAgro FastAPI backend.
    Call .login() first — all subsequent calls attach the JWT automatically.
    """

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        # Do not set a default Content-Type header so requests can determine it dynamically (e.g. for multipart uploads)
        self.token: Optional[str] = None


    # ── Internal helpers ─────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _handle(self, response: requests.Response):
        """Raise a readable error or return parsed JSON/text."""
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            detail = ""
            try:
                data = response.json()
                if isinstance(data, dict):
                    detail = data.get("detail", "") or data.get("message", "")
                elif isinstance(data, list):
                    detail = str(data)
            except Exception:
                detail = response.text.strip()
            raise RuntimeError(f"API error {response.status_code}: {detail or str(e)}") from e

        if not response.content:
            return None

        try:
            return response.json()
        except ValueError:
            return response.text

    # ── Auth ─────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> str:
        """Login and store JWT. Must be called before any other method."""
        resp = self.session.post(
            self._url("/auth/login"),
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT_LOGIN,
        )
        data = self._handle(resp)
        token = data["access_token"]
        self.token = token
        self.session.headers["Authorization"] = f"Bearer {token}"
        return token

    def register(self, name: str, email: str, password: str, market: str = "") -> dict:
        resp = self.session.post(
            self._url("/auth/register"),
            json={"name": name, "email": email, "password": password, "market": market},
            timeout=TIMEOUT_DEFAULT,
        )
        return self._handle(resp)

    # ── Dashboard (Screen 1) ─────────────────────────────────────

    def get_dashboard_stats(self) -> dict:
        resp = self.session.get(self._url("/dashboard/stats"), timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def get_spoilage_alerts(self, resolved: bool = False) -> list:
        resp = self.session.get(
            self._url("/dashboard/alerts"),
            params={"resolved": str(resolved).lower()},
            timeout=TIMEOUT_DEFAULT,
        )
        return self._handle(resp)

    def resolve_alert(self, alert_id: int) -> dict:
        resp = self.session.patch(self._url(f"/dashboard/alerts/{alert_id}/resolve"), timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    # ── Stock (Screen 1 right + Screen 2) ────────────────────────

    def get_stock_items(self) -> list:
        resp = self.session.get(self._url("/stock/"), timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def upsert_stock_item(self, emoji: str, name: str, qty: float, pct: int, age: int) -> dict:
        resp = self.session.post(
            self._url("/stock/"),
            json={"emoji": emoji, "name": name, "qty": qty, "pct": pct, "age": age},
            timeout=TIMEOUT_DEFAULT,
        )
        return self._handle(resp)

    def submit_stock_log(
        self,
        item_name: str,
        emoji: str,
        remaining_kg: float,
        bought_today_kg: float,
        buy_price: float,
        sell_price: float,
        notes: str = "",
    ) -> dict:
        resp = self.session.post(
            self._url("/stock/log"),
            json={
                "item_name": item_name,
                "emoji": emoji,
                "remaining_kg": remaining_kg,
                "bought_today_kg": bought_today_kg,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "notes": notes,
            },
            timeout=TIMEOUT_DEFAULT,
        )
        return self._handle(resp)

    def submit_full_log(self, log_items: list) -> list:
        results = []
        for item in log_items:
            result = self.submit_stock_log(
                item_name=item.get("name", item.get("item_name", "")),
                emoji=item.get("emoji", ""),
                remaining_kg=float(item.get("qty", item.get("remaining_kg", 0))),
                bought_today_kg=float(item.get("bought", item.get("bought_today_kg", 0))),
                buy_price=float(item.get("buy", item.get("buy_price", 0))),
                sell_price=float(item.get("sell", item.get("sell_price", 0))),
                notes=item.get("notes", ""),
            )
            results.append(result)
        return results

    def get_stock_log_history(self, limit: int = 50) -> list:
        resp = self.session.get(self._url("/stock/log/history"), params={"limit": limit}, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    # ── Reorder / Buy List (Screen 3) ────────────────────────────

    def get_reorder_suggestions(self, for_date: str = None) -> list:
        params = {"for_date": for_date or date.today().isoformat()}
        resp = self.session.get(self._url("/reorder/"), params=params, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def get_share_text(self, for_date: str = None) -> dict:
        params = {"for_date": for_date or date.today().isoformat()}
        resp = self.session.get(self._url("/reorder/share"), params=params, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    # ── Insights (Screen 4) ───────────────────────────────────────

    def get_weekly_summary(self, week_start: str = None) -> dict:
        params = {}
        if week_start:
            params["week_start"] = week_start
        resp = self.session.get(self._url("/insights/weekly"), params=params, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def get_spoilage_losses(self, week_start: str = None) -> list:
        params = {}
        if week_start:
            params["week_start"] = week_start
        resp = self.session.get(self._url("/insights/spoilage"), params=params, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def get_best_sellers(self, week_start: str = None) -> list:
        params = {}
        if week_start:
            params["week_start"] = week_start
        resp = self.session.get(self._url("/insights/bestsellers"), params=params, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    # ── Phase 3: AI brain ────────────────────────────────────────

    def get_ai_status(self) -> dict:
        resp = self.session.get(self._url("/ai/status"), timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def train_ai(self) -> dict:
        resp = self.session.post(self._url("/ai/train"), timeout=TIMEOUT_HEAVY)
        return self._handle(resp)

    def predict_demand(self, item_name: str, horizon_days: int = 1) -> dict:
        resp = self.session.get(
            self._url("/ai/predict/demand"),
            params={"item_name": item_name, "horizon_days": horizon_days},
            timeout=TIMEOUT_DEFAULT,
        )
        return self._handle(resp)

    def predict_spoilage(self, item_name: str) -> dict:
        resp = self.session.get(
            self._url("/ai/predict/spoilage"),
            params={"item_name": item_name},
            timeout=TIMEOUT_DEFAULT,
        )
        return self._handle(resp)

    def refresh_ai_reorder(self, for_date: str = None) -> dict:
        params = {}
        if for_date:
            params["for_date"] = for_date
        resp = self.session.post(self._url("/ai/reorder/refresh"), params=params, timeout=TIMEOUT_HEAVY)
        return self._handle(resp)


    # ── Phase 4 smart inventory ──────────────────────────────────

    def detect_image(self, image_path: str | bytes, filename: str | None = None) -> list[dict]:
        if isinstance(image_path, bytes):
            files = {"file": (filename or "image.jpg", image_path, "image/jpeg")}
        else:
            with open(image_path, "rb") as fh:
                data = fh.read()
            files = {"file": (filename or os.path.basename(str(image_path)), data, "image/jpeg")}
        resp = self.session.post(self._url("/detect"), files=files, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def assess_freshness(self, image_path: str | bytes, item_name: str = "", filename: str | None = None) -> dict:
        if isinstance(image_path, bytes):
            files = {"file": (filename or "image.jpg", image_path, "image/jpeg")}
        else:
            with open(image_path, "rb") as fh:
                data = fh.read()
            files = {"file": (filename or os.path.basename(str(image_path)), data, "image/jpeg")}
        data = {"item_name": item_name}
        resp = self.session.post(self._url("/freshness"), data=data, files=files, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def predict_spoilage_phase4(
        self,
        item_name: str,
        freshness_score: float,
        temperature_c: float | None = None,
        humidity_pct: float | None = None,
        storage_days: int | None = None,
        quantity: float | None = None,
    ) -> dict:
        payload = {
            "item_name": item_name,
            "freshness_score": freshness_score,
            "temperature_c": temperature_c,
            "humidity_pct": humidity_pct,
            "storage_days": storage_days,
            "quantity": quantity,
        }
        resp = self.session.post(self._url("/spoilage"), json=payload, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def get_inventory(self, q: str | None = None) -> list:
        params = {"q": q} if q else None
        resp = self.session.get(self._url("/inventory"), params=params, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def upsert_inventory_item(self, payload: dict) -> dict:
        resp = self.session.post(self._url("/inventory"), json=payload, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)

    def forecast_consumption(self, item_name: str, series: list[float] | None = None, horizon_days: int = 7) -> dict:
        resp = self.session.post(
            self._url("/forecast"),
            json={"item_name": item_name, "series": series, "horizon_days": horizon_days},
            timeout=TIMEOUT_DEFAULT,
        )
        return self._handle(resp)

    def ask_copilot(self, query: str) -> dict:
        resp = self.session.post(self._url("/copilot"), json={"query": query}, timeout=TIMEOUT_HEAVY)
        return self._handle(resp)

    def voice_query(self, text: str = "", audio_path: str | None = None) -> dict:
        files = None
        data = {"text": text}
        if audio_path:
            with open(audio_path, "rb") as fh:
                audio = fh.read()
            files = {"file": (os.path.basename(str(audio_path)), audio, "audio/wav")}
        resp = self.session.post(self._url("/voice"), data=data, files=files, timeout=TIMEOUT_HEAVY)
        return self._handle(resp)

    def get_vision_summary(self, days: int = 7) -> dict:
        resp = self.session.get(self._url("/vision/summary"), params={"days": days}, timeout=TIMEOUT_DEFAULT)
        return self._handle(resp)


    # ── Health check ─────────────────────────────────────────────

    def ping(self) -> bool:
        """Quick reachability check — 2 second timeout, no auth needed."""
        try:
            resp = requests.get(self._url("/"), timeout=TIMEOUT_PING)
            return resp.status_code == 200
        except Exception:
            return False


api = VisualAgroAPI()
