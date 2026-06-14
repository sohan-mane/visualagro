"""
VisualAgro — AI Vendor Desktop App  (API-Connected Version · FIXED)
Theme: Soft Sage #ACC8A2 + Deep Olive #1A2517
Built with CustomTkinter + Matplotlib

FIXES applied:
  - Lazy screen loading: screens are created only when first visited (no startup lag)
  - Login: quick 2-second ping check before attempting auth, error shown immediately
  - Reduced all API timeouts to 6 s (was 10 s) for snappier feedback
  - Data caching: switching tabs does NOT re-fetch data (cache_ok flag)
  - Fixed run_async missing root= in share button (was silently crashing)
  - Emoji labels use 'Segoe UI Emoji' font on Windows to fix garbled icons
  - Login button re-enabled on error so user can retry without restart
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime
from pathlib import Path
import tempfile
import threading
import platform
import os
import wave

# ── Import the API client ─────────────────────────────────────────────
from api_client import api   # api_client.py must be in the same folder

# ── Theme & Colours ──────────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

C = {
    "olive900": "#0E1A0C", "olive800": "#1A2517", "olive700": "#243520",
    "olive600": "#2E4429", "olive500": "#3A5533",
    "sage500":  "#ACC8A2", "sage400":  "#BDD4B5", "sage300":  "#CDDFC8",
    "sage200":  "#DCE9D9", "sage100":  "#EBF3E8", "sage50":   "#F4F9F3",
    "text900":  "#0E1A0C", "text700":  "#2C3D29", "text500":  "#4A6244",
    "text300":  "#7A9B74", "text200":  "#A8C4A2",
    "amber500": "#D4A017", "amber200": "#F0E0A0", "amber700": "#8A6610",
    "red500":   "#C0392B", "red200":   "#F5C6C2", "red700":   "#922B21",
    "white":    "#FFFFFF", "card":     "#FAFCF9", "border":   "#D8E8D4",
    "divider":  "#E4EEE1", "bg":       "#F2F7F1",
    "sidebar":  "#1A2517", "sidebar2": "#243520", "sidebar3": "#2E4429",
    "siderbdr": "#2C3D29", "wa":       "#25D366",
}

FONT_TITLE   = ("Segoe UI", 22, "bold")
FONT_HEAD    = ("Segoe UI", 14, "bold")
FONT_SUBHEAD = ("Segoe UI", 12, "bold")
FONT_BODY    = ("Segoe UI", 11)
FONT_SMALL   = ("Segoe UI", 10)
FONT_LABEL   = ("Segoe UI", 9,  "bold")
FONT_NAV     = ("Segoe UI", 11, "bold")
FONT_STAT    = ("Segoe UI", 26, "bold")
FONT_STAT_S  = ("Segoe UI", 20, "bold")

# Use Segoe UI Emoji on Windows to avoid garbled icon rendering
FONT_EMOJI_LG = ("Segoe UI Emoji", 20) if platform.system() == "Windows" else ("Segoe UI", 22)
FONT_EMOJI_MD = ("Segoe UI Emoji", 18) if platform.system() == "Windows" else ("Segoe UI", 18)
FONT_EMOJI_SM = ("Segoe UI Emoji", 16) if platform.system() == "Windows" else ("Segoe UI", 16)

QUICK_ITEMS = ["🧅 Onions", "🥔 Potatoes", "🍅 Tomatoes", "🥕 Carrots",
               "🧄 Garlic",  "🌿 Coriander", "🥬 Spinach",  "🫑 Capsicum"]


# ════════════════════════════════════════════════════════════════════
#  HELPER — run API calls in a background thread so UI never freezes
# ════════════════════════════════════════════════════════════════════

def run_async(fn, callback=None, error_callback=None, root=None):
    def worker():
        try:
            result = fn()
            if callback and root:
                root.after(0, lambda res=result: callback(res))
            elif callback:
                callback(result)
        except Exception as e:
            err_msg = str(e)
            if error_callback and root:
                root.after(0, lambda msg=err_msg: error_callback(msg))
            elif error_callback:
                error_callback(err_msg)


    t = threading.Thread(target=worker, daemon=True)
    t.start()


def capture_webcam_frame(camera_index: int = 0) -> str:
    """Capture a single image from the laptop camera and store it in a temp file."""
    import cv2

    backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
    cap = cv2.VideoCapture(camera_index, backend)
    if not cap.isOpened():
        raise RuntimeError("Could not access the camera. Check permissions or camera index.")

    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        frame = None
        ok = False
        for _ in range(12):
            ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError("Camera did not return a frame.")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp.close()
        if not cv2.imwrite(tmp.name, frame):
            raise RuntimeError("Failed to save camera frame.")
        return tmp.name
    finally:
        cap.release()


def record_microphone_audio(seconds: int = 3, sample_rate: int = 16000) -> str:
    """Record a short mono WAV clip from the default microphone."""
    try:
        import sounddevice as sd
        import numpy as np
    except Exception as exc:
        raise RuntimeError(
            "Microphone recording needs the 'sounddevice' package. Install requirements and try again."
        ) from exc

    frames = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames.tobytes())
    return tmp.name


def play_tts_async(text, root=None):
    if not text:
        return

    def work():
        try:
            import edge_tts
            import asyncio
            import subprocess
            import tempfile
            import os

            # Use Hindi Neural for non-ascii characters (Hindi/Marathi), English neural for standard text
            is_hindi = any(ord(char) > 127 for char in text)
            voice = "hi-IN-SwaraNeural" if is_hindi else "en-IN-PrabhatNeural"

            async def generate():
                communicate = edge_tts.Communicate(text, voice)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                tmp.close()
                await communicate.save(tmp.name)
                return tmp.name

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            mp3_path = loop.run_until_complete(generate())

            # Use built-in Windows PowerShell media player to play MP3 asynchronously
            cmd = (
                f"[system.reflection.assembly]::loadwithpartialname('presentationcore') | Out-Null; "
                f"$m = New-Object System.Windows.Media.MediaPlayer; "
                f"$m.Open('{mp3_path}'); "
                f"$m.Play(); "
                f"while($m.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -m 50 }}; "
                f"Start-Sleep -s ($m.NaturalDuration.TimeSpan.TotalSeconds + 1); "
                f"Remove-Item '{mp3_path}' -ErrorAction SilentlyContinue"
            )
            subprocess.Popen(["powershell", "-Command", cmd], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"TTS playback error: {e}")

    import threading
    t = threading.Thread(target=work, daemon=True)
    t.start()


# ════════════════════════════════════════════════════════════════════
#  HELPER WIDGETS
# ════════════════════════════════════════════════════════════════════

def card(parent, **kw):
    defaults = dict(fg_color=C["card"], corner_radius=14,
                    border_width=1, border_color=C["border"])
    defaults.update(kw)
    return ctk.CTkFrame(parent, **defaults)

def section_title(parent, text):
    return ctk.CTkLabel(parent, text=text, font=FONT_HEAD,
                        text_color=C["olive800"])

def risk_badge(parent, risk):
    colours = {
        "HIGH": (C["red200"],   C["red700"]),
        "MED":  (C["amber200"], C["amber700"]),
        "LOW":  (C["sage200"],  C["olive600"]),
    }
    bg, fg = colours.get(risk, (C["sage100"], C["text500"]))
    return ctk.CTkLabel(parent, text=risk, font=FONT_LABEL,
                        fg_color=bg, text_color=fg,
                        corner_radius=6, width=50, height=22)

def conf_badge(parent, conf):
    return risk_badge(parent, conf)

def _loading_lbl(parent, text="⏳  Loading…"):
    return ctk.CTkLabel(parent, text=text, font=FONT_BODY, text_color=C["text300"])


# ════════════════════════════════════════════════════════════════════
#  LOGIN SCREEN  — with quick ping check before auth attempt
# ════════════════════════════════════════════════════════════════════

class LoginScreen(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self.on_success = on_success
        self._login_in_progress = False

        panel = card(self, width=400)
        panel.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(panel, text="🌿", font=("Segoe UI Emoji", 48)).pack(pady=(32, 4))
        ctk.CTkLabel(panel, text="VisualAgro",
                     font=("Segoe UI", 22, "bold"),
                     text_color=C["olive800"]).pack()
        ctk.CTkLabel(panel, text="Vendor Dashboard",
                     font=FONT_BODY, text_color=C["text300"]).pack(pady=(0, 24))

        # Server URL field
        ctk.CTkLabel(panel, text="BACKEND URL", font=FONT_LABEL,
                     text_color=C["text500"]).pack(anchor="w", padx=24)
        self.f_url = ctk.CTkEntry(panel, font=FONT_BODY, height=38, corner_radius=8,
                                   fg_color=C["sage50"], border_color=C["border"],
                                   text_color=C["text900"])
        self.f_url.insert(0, "http://127.0.0.1:8000")
        self.f_url.pack(fill="x", padx=24, pady=(2, 12))

        # Email
        ctk.CTkLabel(panel, text="EMAIL", font=FONT_LABEL,
                     text_color=C["text500"]).pack(anchor="w", padx=24)
        self.f_email = ctk.CTkEntry(panel, font=FONT_BODY, height=38, corner_radius=8,
                                     fg_color=C["sage50"], border_color=C["border"],
                                     text_color=C["text900"])
        self.f_email.insert(0, "ramesh@visualagro.in")
        self.f_email.pack(fill="x", padx=24, pady=(2, 12))

        # Password
        ctk.CTkLabel(panel, text="PASSWORD", font=FONT_LABEL,
                     text_color=C["text500"]).pack(anchor="w", padx=24)
        self.f_pass = ctk.CTkEntry(panel, font=FONT_BODY, height=38, corner_radius=8,
                                    fg_color=C["sage50"], border_color=C["border"],
                                    text_color=C["text900"], show="•")
        self.f_pass.insert(0, "demo1234")
        self.f_pass.pack(fill="x", padx=24, pady=(2, 16))
        # Allow Enter key to trigger login
        self.f_pass.bind("<Return>", lambda e: self._do_login())
        self.f_email.bind("<Return>", lambda e: self._do_login())

        self.err_lbl = ctk.CTkLabel(panel, text="", font=FONT_SMALL,
                                     text_color=C["red500"])
        self.err_lbl.pack(pady=(0, 4))

        self.status_lbl = ctk.CTkLabel(panel, text="", font=FONT_SMALL,
                                        text_color=C["text300"])
        self.status_lbl.pack()

        self.login_btn = ctk.CTkButton(
            panel, text="Login  →", font=("Segoe UI", 13, "bold"),
            fg_color=C["olive600"], hover_color=C["olive700"],
            height=46, corner_radius=10, command=self._do_login,
        )
        self.login_btn.pack(fill="x", padx=24, pady=(8, 32))

    def _set_status(self, msg, color=None):
        self.status_lbl.configure(text=msg, text_color=color or C["text300"])

    def _do_login(self):
        if self._login_in_progress:
            return

        url   = self.f_url.get().strip().rstrip("/")
        email = self.f_email.get().strip()
        pwd   = self.f_pass.get()

        if not url or not email or not pwd:
            self.err_lbl.configure(text="All fields are required.")
            return

        self._login_in_progress = True
        api.base_url = url
        self.login_btn.configure(state="disabled", text="Checking server…")
        self.err_lbl.configure(text="")
        self._set_status("🔍  Pinging backend…")

        # Step 1: quick 2-second ping check
        def ping_check():
            return api.ping()   # already uses timeout=3 internally

        def on_ping(reachable):
            if not reachable:
                self._login_in_progress = False
                self.login_btn.configure(state="normal", text="Login  →")
                self._set_status("")
                self.err_lbl.configure(
                    text=f"❌  Cannot reach server at {url}\n"
                         "Check that the backend is running."
                )
                return
            # Step 2: server is up — now do auth
            self._set_status("🔑  Authenticating…")
            self.login_btn.configure(text="Logging in…")

            def do_auth():
                api.login(email, pwd)

            def on_ok(_=None):
                self._login_in_progress = False
                self._set_status("✅  Success!", C["olive600"])
                self.after(300, self.on_success)   # brief flash of success before transition

            def on_err(msg):
                self._login_in_progress = False
                self.login_btn.configure(state="normal", text="Login  →")
                self._set_status("")
                self.err_lbl.configure(text=f"❌  {msg}")

            run_async(do_auth, callback=on_ok, error_callback=on_err, root=self)

        def on_ping_err(msg):
            self._login_in_progress = False
            self.login_btn.configure(state="normal", text="Login  →")
            self._set_status("")
            self.err_lbl.configure(text=f"❌  Server unreachable: {msg}")

        run_async(ping_check, callback=on_ping, error_callback=on_ping_err, root=self)


# ════════════════════════════════════════════════════════════════════
#  SCREEN 1 — DASHBOARD  (lazy + cached)
# ════════════════════════════════════════════════════════════════════

class DashboardScreen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self._data_loaded = False

        hdr = ctk.CTkFrame(self, fg_color=C["olive800"], corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="VisualAgro  🌿",
                     font=("Segoe UI", 20, "bold"),
                     text_color=C["white"]).pack(side="left", padx=24, pady=18)
        ctk.CTkLabel(hdr, text=f"📅  {datetime.now().strftime('%A, %d %b %Y')}",
                     font=FONT_BODY, text_color=C["sage400"]).pack(side="right", padx=24)

        ctk.CTkFrame(self, fg_color=C["sage500"], corner_radius=0, height=4).pack(fill="x")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg"], corner_radius=0)
        self.scroll.pack(fill="both", expand=True)

        self.loading_lbl = _loading_lbl(self.scroll, "⏳  Loading data from backend…")
        self.loading_lbl.pack(pady=40)

    def load_if_needed(self):
        if self._data_loaded:
            return
        self._data_loaded = True
        run_async(
            fn=lambda: (
                api.get_dashboard_stats(),
                api.get_spoilage_alerts(),
                api.get_stock_items(),
            ),
            callback=self._render,
            error_callback=lambda e: self.loading_lbl.configure(
                text=f"⚠️  Could not reach backend:\n{e}", text_color=C["red500"]
            ),
            root=self,
        )

    def _render(self, data):
        stats, alerts, stock_items = data
        self.loading_lbl.destroy()

        # ── Stat cards ──────────────────────────────────────────
        stat_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        stat_row.pack(fill="x", padx=24, pady=(20, 0))
        stat_row.columnconfigure((0, 1, 2, 3), weight=1, uniform="stat")

        stat_data = [
            ("💰 Today's Revenue", stats["today_revenue"],  stats["revenue_change"],    C["olive600"]),
            ("🗑️  Waste Cost",      stats["waste_cost"],     stats["waste_change"],      C["olive600"]),
            ("📦 Items in Stock",  str(stats["items_in_stock"]),
             f"{stats['critically_low']} critically low",                                C["amber700"]),
            ("🤖 AI Forecast",     stats["ai_forecast"],    stats.get("forecast_label", "Expected tomorrow"), C["text300"]),
        ]
        for col, (lbl, val, sub, sub_c) in enumerate(stat_data):
            c_ = card(stat_row)
            c_.grid(row=0, column=col, padx=6, pady=0, sticky="nsew", ipady=12)
            ctk.CTkLabel(c_, text=lbl, font=FONT_SMALL,
                         text_color=C["text300"]).pack(anchor="w", padx=14, pady=(12, 0))
            ctk.CTkLabel(c_, text=val, font=FONT_STAT,
                         text_color=C["olive800"]).pack(anchor="w", padx=14)
            ctk.CTkLabel(c_, text=sub, font=FONT_SMALL,
                         text_color=sub_c).pack(anchor="w", padx=14, pady=(0, 12))

        # ── Two columns ─────────────────────────────────────────
        cols = ctk.CTkFrame(self.scroll, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=24, pady=16)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # LEFT — Alerts
        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        section_title(left, "⚠️  Spoilage Alerts").pack(anchor="w", pady=(0, 8))

        if not alerts:
            ctk.CTkLabel(left, text="✅  No active alerts",
                         font=FONT_BODY, text_color=C["text300"]).pack(pady=20)
        for a in alerts:
            ac = card(left)
            ac.pack(fill="x", pady=4)
            stripe_c = C["red500"] if a["risk"] == "HIGH" else C["amber500"]
            ctk.CTkFrame(ac, width=4, fg_color=stripe_c, corner_radius=0).pack(side="left", fill="y")
            ico_bg = C["red200"] if a["risk"] == "HIGH" else C["amber200"]
            ico = ctk.CTkFrame(ac, width=44, height=44, fg_color=ico_bg, corner_radius=10)
            ico.pack(side="left", padx=10, pady=10)
            ico.pack_propagate(False)
            ctk.CTkLabel(ico, text=a["emoji"], font=FONT_EMOJI_MD).pack(expand=True)
            txt = ctk.CTkFrame(ac, fg_color="transparent")
            txt.pack(side="left", fill="both", expand=True, pady=10)
            ctk.CTkLabel(txt, text=a["name"],   font=FONT_SUBHEAD, text_color=C["text900"]).pack(anchor="w")
            ctk.CTkLabel(txt, text=a["detail"], font=FONT_SMALL,   text_color=C["text300"]).pack(anchor="w")
            risk_badge(ac, a["risk"]).pack(side="right", padx=14)

        # RIGHT — Stock
        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        section_title(right, "📦  Current Stock").pack(anchor="w", pady=(0, 8))
        sc = card(right)
        sc.pack(fill="x")

        for i, item in enumerate(stock_items):
            row = ctk.CTkFrame(sc, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=6)
            ctk.CTkLabel(row, text=item["emoji"], font=FONT_EMOJI_MD, width=30).pack(side="left")
            name_f = ctk.CTkFrame(row, fg_color="transparent", width=100)
            name_f.pack(side="left", padx=(8, 0))
            name_f.pack_propagate(False)
            ctk.CTkLabel(name_f, text=item["name"],
                         font=FONT_SUBHEAD, text_color=C["text900"]).pack(anchor="w")
            ctk.CTkLabel(name_f, text=f"{item['qty']} kg",
                         font=FONT_SMALL, text_color=C["text300"]).pack(anchor="w")
            bar_c = (C["red500"] if item["pct"] < 20
                     else C["amber500"] if item["pct"] < 40
                     else C["sage500"])
            pb = ctk.CTkProgressBar(row, width=120, height=8, corner_radius=4,
                                     fg_color=C["sage200"], progress_color=bar_c)
            pb.set(item["pct"] / 100)
            pb.pack(side="right", padx=(0, 8))
            ctk.CTkLabel(row, text=f'{item["pct"]}%', font=FONT_LABEL,
                         text_color=bar_c, width=32).pack(side="right")
            if i < len(stock_items) - 1:
                ctk.CTkFrame(sc, height=1, fg_color=C["divider"]).pack(fill="x", padx=14)


# ════════════════════════════════════════════════════════════════════
#  SCREEN 2 — STOCK ENTRY  (submits to backend)
# ════════════════════════════════════════════════════════════════════

class StockEntryScreen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self._built = False

    def load_if_needed(self):
        if self._built:
            return
        self._built = True
        self._build_ui()

    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color=C["olive800"], corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="📋  End-of-Day Stock Entry",
                     font=("Segoe UI", 18, "bold"),
                     text_color=C["white"]).pack(side="left", padx=24, pady=18)
        ctk.CTkLabel(hdr, text="⏱  Takes less than 2 minutes",
                     font=FONT_BODY, text_color=C["sage400"]).pack(side="right", padx=24)

        ctk.CTkFrame(self, fg_color=C["sage500"], corner_radius=0, height=4).pack(fill="x")

        scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg"], corner_radius=0)
        scroll.pack(fill="both", expand=True)

        main = ctk.CTkFrame(scroll, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=16)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        section_title(left, "➕  Log New Item").pack(anchor="w", pady=(0, 10))
        form_card = card(left)
        form_card.pack(fill="x")

        ctk.CTkLabel(form_card, text="QUICK SELECT", font=FONT_LABEL,
                     text_color=C["text300"]).pack(anchor="w", padx=16, pady=(14, 6))
        chips_f = ctk.CTkFrame(form_card, fg_color="transparent")
        chips_f.pack(fill="x", padx=16, pady=(0, 10))
        self.selected_chip = tk.StringVar(value="🍅 Tomatoes")
        self.chip_buttons  = {}
        row_f = None
        for i, item in enumerate(QUICK_ITEMS):
            if i % 4 == 0:
                row_f = ctk.CTkFrame(chips_f, fg_color="transparent")
                row_f.pack(fill="x", pady=2)
            btn = ctk.CTkButton(
                row_f, text=item, font=FONT_SMALL,
                fg_color=C["sage100"], text_color=C["olive700"],
                hover_color=C["sage300"], corner_radius=999,
                height=30, border_width=1, border_color=C["sage400"],
                command=lambda x=item: self._select_chip(x),
            )
            btn.pack(side="left", padx=3)
            self.chip_buttons[item] = btn

        ctk.CTkFrame(form_card, height=1, fg_color=C["divider"]).pack(fill="x", padx=16, pady=4)

        fields_grid = ctk.CTkFrame(form_card, fg_color="transparent")
        fields_grid.pack(fill="x", padx=16, pady=8)
        fields_grid.columnconfigure((0, 1), weight=1)

        self.f_name   = self._field(fields_grid, "Item Name",         "Tomatoes", 0, 0, colspan=2)
        self.f_remain = self._field(fields_grid, "Remaining (kg)",    "3.2",      1, 0)
        self.f_bought = self._field(fields_grid, "Bought Today (kg)", "5",        1, 1)
        self.f_buy_p  = self._field(fields_grid, "Buy Price (₹/kg)",  "28",       2, 0)
        self.f_sell_p = self._field(fields_grid, "Sell Price (₹/kg)", "50",       2, 1)

        btn_row = ctk.CTkFrame(form_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(4, 16))
        ctk.CTkButton(
            btn_row, text="🎙  Voice Input (Hindi / Marathi)",
            font=FONT_BODY, fg_color=C["sage100"], text_color=C["text500"],
            hover_color=C["sage200"], height=36, corner_radius=8,
            border_width=1, border_color=C["border"],
            command=self._voice_input,
        ).pack(fill="x", pady=(0, 8))
        self.voice_hint = ctk.CTkLabel(btn_row, text="Voice helper ready", font=FONT_SMALL, text_color=C["text300"])
        self.voice_hint.pack(anchor="w", pady=(0, 6))
        ctk.CTkButton(
            btn_row, text="✓  Add to Today's Log",
            font=("Segoe UI", 12, "bold"), fg_color=C["olive600"],
            hover_color=C["olive700"], height=42, corner_radius=10,
            command=self._add_item,
        ).pack(fill="x")

        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        section_title(right, "📝  Logged Today").pack(anchor="w", pady=(0, 10))
        self.logged_card = card(right)
        self.logged_card.pack(fill="both", expand=True)

        self.log_count_lbl = ctk.CTkLabel(
            self.logged_card, text="0 ITEMS LOGGED",
            font=FONT_LABEL, text_color=C["text300"],
        )
        self.log_count_lbl.pack(anchor="w", padx=16, pady=(12, 8))

        self.log_inner = ctk.CTkFrame(self.logged_card, fg_color="transparent")
        self.log_inner.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.log_items = []
        self._render_log()

        self.submit_btn = ctk.CTkButton(
            right, text="📤  Submit End-of-Day Log",
            font=("Segoe UI", 13, "bold"), fg_color=C["olive800"],
            hover_color=C["olive700"], height=46, corner_radius=12,
            command=self._submit,
        )
        self.submit_btn.pack(fill="x", pady=(10, 0))

    def _field(self, parent, lbl_text, default, row, col, colspan=1):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, columnspan=colspan,
               padx=(0, 6) if col == 0 else (6, 0), pady=4, sticky="ew")
        parent.columnconfigure(col, weight=1)
        ctk.CTkLabel(f, text=lbl_text, font=FONT_LABEL,
                     text_color=C["text500"]).pack(anchor="w")
        e = ctk.CTkEntry(f, font=FONT_BODY, fg_color=C["sage50"],
                         border_color=C["border"], height=36, corner_radius=8,
                         text_color=C["text900"])
        e.insert(0, default)
        e.pack(fill="x", pady=(2, 0))
        return e

    def _select_chip(self, item):
        self.selected_chip.set(item)
        name = item.split(" ", 1)[1] if " " in item else item
        self.f_name.delete(0, "end")
        self.f_name.insert(0, name)

    def _voice_input(self):
        self._voice_btn_busy = True
        try:
            self._set_voice_status("Recording for 3 seconds...")
            wav_path = record_microphone_audio(seconds=3)
        except Exception as exc:
            self._set_voice_status("Voice input unavailable")
            messagebox.showerror("Voice Input", str(exc))
            return

        self._set_voice_status("Transcribing...")
        def work():
            try:
                return api.voice_query(audio_path=wav_path)
            finally:
                try:
                    os.unlink(wav_path)
                except Exception:
                    pass

        def ok(data):
            transcript = (data.get("transcript") or "").strip()
            response = (data.get("response_text") or "").strip()
            self._set_voice_status("Voice captured")
            if transcript:
                self.f_name.delete(0, "end")
                self.f_name.insert(0, transcript[:80])
            messagebox.showinfo(
                "Voice Input",
                f"Transcript:\n{transcript or 'No speech detected'}\n\nResponse:\n{response or 'No response'}",
            )
            if response:
                play_tts_async(response, self)


        def err(msg):
            self._set_voice_status("Voice failed")
            messagebox.showerror("Voice Input", msg)

        run_async(work, callback=ok, error_callback=err, root=self)

    def _set_voice_status(self, text):
        try:
            self.voice_hint.configure(text=text)
        except Exception:
            pass

    def _add_item(self):
        name = self.f_name.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Please enter an item name.")
            return
        try:
            qty    = float(self.f_remain.get())
            bought = float(self.f_bought.get())
            buy_p  = float(self.f_buy_p.get())
            sell_p = float(self.f_sell_p.get())
        except ValueError:
            messagebox.showwarning("Invalid", "Please enter valid numbers.")
            return
        chip  = self.selected_chip.get()
        emoji = chip.split(" ")[0] if chip else "🥦"
        self.log_items.append({
            "emoji": emoji, "name": name,
            "qty": qty, "bought": bought,
            "buy": buy_p, "sell": sell_p,
        })
        self._render_log()

    def _render_log(self):
        for w in self.log_inner.winfo_children():
            w.destroy()
        self.log_count_lbl.configure(text=f"{len(self.log_items)} ITEMS LOGGED")
        for i, item in enumerate(self.log_items):
            row = ctk.CTkFrame(self.log_inner, fg_color=C["sage100"],
                               corner_radius=10, border_width=1,
                               border_color=C["sage300"])
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=item["emoji"], font=FONT_EMOJI_MD).pack(side="left", padx=10)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, pady=8)
            ctk.CTkLabel(info, text=item["name"], font=FONT_SUBHEAD,
                         text_color=C["olive800"]).pack(anchor="w")
            detail = (f"Rem: {item['qty']} kg  ·  Bought: {item['bought']} kg"
                      f"  ·  ₹{item['buy']} → ₹{item['sell']}/kg")
            ctk.CTkLabel(info, text=detail, font=FONT_SMALL,
                         text_color=C["text500"]).pack(anchor="w")
            ctk.CTkButton(
                row, text="✕", width=28, height=28,
                fg_color="transparent", hover_color=C["red200"],
                text_color=C["text300"], font=("Segoe UI", 12, "bold"),
                corner_radius=6,
                command=lambda x=i: self._delete_item(x),
            ).pack(side="right", padx=8)

    def _delete_item(self, idx):
        self.log_items.pop(idx)
        self._render_log()

    def _submit(self):
        if not self.log_items:
            messagebox.showwarning("Empty", "Add at least one item before submitting.")
            return

        self.submit_btn.configure(state="disabled", text="⏳  Submitting…")

        def do():
            return api.submit_full_log(self.log_items)

        def on_ok(results):
            self.submit_btn.configure(state="normal", text="📤  Submit End-of-Day Log")
            messagebox.showinfo(
                "✅ Submitted",
                f"{len(results)} items submitted to backend!\n"
                "ML engine will update spoilage predictions & tomorrow's forecast.",
            )
            self.log_items.clear()
            self._render_log()

        def on_err(msg):
            self.submit_btn.configure(state="normal", text="📤  Submit End-of-Day Log")
            messagebox.showerror("Submit Failed", f"Could not reach backend:\n{msg}")

        run_async(do, callback=on_ok, error_callback=on_err, root=self)


# ════════════════════════════════════════════════════════════════════
#  SCREEN 3 — REORDER  (lazy + cached, fixed share button)
# ════════════════════════════════════════════════════════════════════

class ReorderScreen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self._data_loaded = False
        self._reorder_data = []

        hdr = ctk.CTkFrame(self, fg_color=C["olive800"], corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="🛒  AI Buy List — Tomorrow",
                     font=("Segoe UI", 18, "bold"),
                     text_color=C["white"]).pack(side="left", padx=24, pady=18)
        self.date_lbl = ctk.CTkLabel(hdr, text="", font=FONT_BODY,
                                      text_color=C["sage400"])
        self.date_lbl.pack(side="right", padx=24)

        ctk.CTkFrame(self, fg_color=C["sage500"], corner_radius=0, height=4).pack(fill="x")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg"], corner_radius=0)
        self.scroll.pack(fill="both", expand=True)

        self.loading_lbl = _loading_lbl(self.scroll, "⏳  Loading buy list…")
        self.loading_lbl.pack(pady=40)

    def load_if_needed(self):
        if self._data_loaded:
            return
        self._data_loaded = True
        run_async(
            fn=api.get_reorder_suggestions,
            callback=self._render,
            error_callback=lambda e: self.loading_lbl.configure(
                text=f"⚠️  {e}", text_color=C["red500"]
            ),
            root=self,
        )

    def _render(self, items):
        self._reorder_data = items
        try:
            self.loading_lbl.destroy()
        except Exception:
            pass
        self.date_lbl.configure(text=datetime.now().strftime("%a, %d %b"))

        inner = ctk.CTkFrame(self.scroll, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=16)

        total_cost = sum(i["cost"] for i in items)
        sum_row = ctk.CTkFrame(inner, fg_color="transparent")
        sum_row.pack(fill="x", pady=(0, 16))
        sum_row.columnconfigure((0, 1, 2), weight=1)
        for col, (lbl, val) in enumerate([
            ("💰 Estimated Buy Cost", f"₹{total_cost:,}"),
            ("📦 Total Items",        f"{len(items)} items"),
            ("📈 Projected Margin",   "42%"),
        ]):
            sc = card(sum_row, fg_color=C["olive800"], border_color=C["olive700"])
            sc.grid(row=0, column=col, padx=6, sticky="ew", ipady=8)
            ctk.CTkLabel(sc, text=lbl, font=FONT_SMALL,
                         text_color=C["sage400"]).pack(anchor="w", padx=16, pady=(12, 0))
            ctk.CTkLabel(sc, text=val, font=FONT_STAT_S,
                         text_color=C["white"]).pack(anchor="w", padx=16, pady=(0, 12))

        hdr_row = ctk.CTkFrame(inner, fg_color=C["sage100"], corner_radius=8,
                               border_width=1, border_color=C["border"])
        hdr_row.pack(fill="x", pady=(0, 6))
        for txt, w in [("Item", 220), ("Details", 0), ("Qty", 60), ("Cost", 80), ("Confidence", 100)]:
            ctk.CTkLabel(hdr_row, text=txt, font=FONT_LABEL, text_color=C["text500"],
                         width=w if w else 0, anchor="w").pack(
                side="left", padx=10, pady=8,
                fill="x" if not w else "none", expand=not w,
            )

        self.checked = {}
        for item in items:
            self._reorder_row(inner, item)

        ctk.CTkButton(
            inner,
            text="📲  Share Shopping List (WhatsApp / Copy)",
            font=("Segoe UI", 13, "bold"),
            fg_color=C["wa"], hover_color="#1ebe5a",
            height=48, corner_radius=12,
            command=self._share,
        ).pack(fill="x", pady=(16, 4))

        ctk.CTkLabel(
            inner,
            text="🤖  Powered by Exponential Smoothing + Random Forest · Updated daily",
            font=FONT_SMALL, text_color=C["text300"],
        ).pack(pady=4)

    def _reorder_row(self, parent, item):
        row = card(parent)
        row.pack(fill="x", pady=4)
        var = tk.BooleanVar()
        self.checked[item["name"]] = var
        ctk.CTkCheckBox(row, text="", variable=var, width=20,
                        fg_color=C["olive600"], hover_color=C["sage500"],
                        border_color=C["sage300"]).pack(side="left", padx=12)
        ctk.CTkLabel(row, text=item["emoji"], font=FONT_EMOJI_LG, width=36).pack(side="left")
        info = ctk.CTkFrame(row, fg_color="transparent", width=200)
        info.pack(side="left", fill="y", pady=10, padx=8)
        info.pack_propagate(False)
        ctk.CTkLabel(info, text=item["name"], font=FONT_SUBHEAD,
                     text_color=C["text900"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=item["detail"], font=FONT_SMALL,
                     text_color=C["text500"], anchor="w", wraplength=190).pack(anchor="w")
        ctk.CTkFrame(row, fg_color="transparent").pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(row, text=f"{item['qty']} kg", font=FONT_BODY,
                     text_color=C["text700"], width=60).pack(side="left")
        ctk.CTkLabel(row, text=f"₹{item['cost']}", font=("Segoe UI", 13, "bold"),
                     text_color=C["olive600"], width=70).pack(side="left")
        conf_badge(row, item["conf"]).pack(side="left", padx=12)

    def _share(self):
        """Share button — fixed: now passes root=self to run_async."""
        def do():
            return api.get_share_text()

        def on_ok(share_data):
            msg = share_data["text"]
            self.clipboard_clear()
            self.clipboard_append(msg)
            messagebox.showinfo("✅ Copied!", "Shopping list copied to clipboard!\nPaste it into WhatsApp.")

        def on_err(e):
            lines = [f"{i['emoji']} {i['name']} — {i['qty']} kg — ₹{i['cost']}"
                     for i in self._reorder_data]
            total = sum(i["cost"] for i in self._reorder_data)
            msg = ("🌿 VisualAgro Buy List — Tomorrow\n\n" + "\n".join(lines)
                   + f"\n\n💰 Total: ₹{total}\nProjected margin: 42%\n\nGenerated by VisualAgro AI")
            self.clipboard_clear()
            self.clipboard_append(msg)
            messagebox.showinfo("✅ Copied!", "Shopping list copied to clipboard!")

        # FIX: was missing root=self — callback was never scheduled on main thread
        run_async(do, callback=on_ok, error_callback=on_err, root=self)


# ════════════════════════════════════════════════════════════════════
#  SCREEN 4 — INSIGHTS  (lazy + cached)
# ════════════════════════════════════════════════════════════════════

class InsightsScreen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self._data_loaded = False

        hdr = ctk.CTkFrame(self, fg_color=C["olive800"], corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="📊  Profit Insights",
                     font=("Segoe UI", 18, "bold"),
                     text_color=C["white"]).pack(side="left", padx=24, pady=18)
        self.week_lbl = ctk.CTkLabel(hdr, text="", font=FONT_BODY,
                                      text_color=C["sage400"])
        self.week_lbl.pack(side="right", padx=24)

        ctk.CTkFrame(self, fg_color=C["sage500"], corner_radius=0, height=4).pack(fill="x")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg"], corner_radius=0)
        self.scroll.pack(fill="both", expand=True)

        self.loading_lbl = _loading_lbl(self.scroll, "⏳  Loading insights…")
        self.loading_lbl.pack(pady=40)

    def load_if_needed(self):
        if self._data_loaded:
            return
        self._data_loaded = True
        run_async(
            fn=lambda: (
                api.get_weekly_summary(),
                api.get_spoilage_losses(),
                api.get_best_sellers(),
            ),
            callback=self._render,
            error_callback=lambda e: self.loading_lbl.configure(
                text=f"⚠️  {e}", text_color=C["red500"]
            ),
            root=self,
        )

    def _render(self, data):
        summary, spoilage, best_sellers = data
        try:
            self.loading_lbl.destroy()
        except Exception:
            pass

        self.week_lbl.configure(text="Last 7 days")

        inner = ctk.CTkFrame(self.scroll, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=16)

        kpi_row = ctk.CTkFrame(inner, fg_color="transparent")
        kpi_row.pack(fill="x", pady=(0, 16))
        kpi_row.columnconfigure((0, 1, 2, 3), weight=1)

        total_rev   = summary["total_revenue"]
        total_waste = summary["total_waste"]
        kpis = [
            ("💰", "Revenue",     f"₹{total_rev // 1000}.{(total_rev % 1000) // 100}K",
             "↑ 18% vs last week", C["olive600"]),
            ("🗑️",  "Waste Cost",  f"₹{total_waste}",
             "↓ 31% saved",        C["olive600"]),
            ("📈", "Avg / Day",   f"₹{summary['avg_daily']}",
             "Net of waste",       C["text300"]),
            ("✨", "Best Margin", summary["best_margin_note"],
             "This week",          C["amber700"]),
        ]
        for col, (ico, lbl, val, sub, sc_) in enumerate(kpis):
            kc = card(kpi_row)
            kc.grid(row=0, column=col, padx=6, sticky="ew", ipady=6)
            ctk.CTkLabel(kc, text=ico, font=FONT_EMOJI_LG).pack(anchor="w", padx=14, pady=(12, 0))
            ctk.CTkLabel(kc, text=lbl, font=FONT_LABEL,
                         text_color=C["text300"]).pack(anchor="w", padx=14)
            ctk.CTkLabel(kc, text=val, font=("Segoe UI", 18, "bold"),
                         text_color=C["olive800"]).pack(anchor="w", padx=14)
            ctk.CTkLabel(kc, text=sub, font=FONT_SMALL,
                         text_color=sc_).pack(anchor="w", padx=14, pady=(0, 10))

        charts_row = ctk.CTkFrame(inner, fg_color="transparent")
        charts_row.pack(fill="both", expand=True, pady=(0, 16))
        charts_row.columnconfigure(0, weight=3)
        charts_row.columnconfigure(1, weight=2)

        lc = card(charts_row)
        lc.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        ctk.CTkLabel(lc, text="Revenue vs Waste — Last 7 Days",
                     font=FONT_SUBHEAD, text_color=C["olive800"]).pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(lc, text="Daily breakdown (₹)",
                     font=FONT_SMALL, text_color=C["text300"]).pack(anchor="w", padx=16, pady=(0, 8))
        self._revenue_chart(lc, summary)

        rc = card(charts_row)
        rc.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        ctk.CTkLabel(rc, text="Spoilage by Item",
                     font=FONT_SUBHEAD, text_color=C["olive800"]).pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(rc, text="This week (₹ loss)",
                     font=FONT_SMALL, text_color=C["text300"]).pack(anchor="w", padx=16, pady=(0, 8))
        self._spoilage_chart(rc, spoilage)

        section_title(inner, "🏆  Best Sellers This Week").pack(anchor="w", pady=(0, 10))
        bs_card = card(inner)
        bs_card.pack(fill="x")

        th = ctk.CTkFrame(bs_card, fg_color=C["sage100"], corner_radius=0)
        th.pack(fill="x", padx=2, pady=(2, 0))
        for txt, w, anchor in [("#", 30, "center"), ("", 30, "center"), ("Item", 160, "w"),
                                ("Kg Sold", 90, "center"), ("Days", 60, "center"), ("Revenue", 100, "e")]:
            ctk.CTkLabel(th, text=txt, font=FONT_LABEL, text_color=C["text300"],
                         width=w if w else 0, anchor=anchor).pack(
                side="left", padx=8, pady=8,
                fill="x" if not w else "none", expand=not w,
            )

        rank_colors = [C["amber500"], C["text300"], C["amber700"], C["text300"], C["text300"]]
        for item in best_sellers:
            rw = ctk.CTkFrame(bs_card, fg_color="transparent")
            rw.pack(fill="x", padx=2)
            rank = item["rank"]
            ctk.CTkLabel(rw, text=f"#{rank}", font=("Segoe UI", 14, "bold"),
                         text_color=rank_colors[min(rank - 1, 4)],
                         width=30, anchor="center").pack(side="left", padx=8, pady=10)
            ctk.CTkLabel(rw, text=item["emoji"],  font=FONT_EMOJI_MD, width=30).pack(side="left")
            ctk.CTkLabel(rw, text=item["name"],   font=FONT_SUBHEAD, text_color=C["text900"],
                         width=160, anchor="w").pack(side="left", padx=8)
            ctk.CTkLabel(rw, text=f'{item["sold"]} kg', font=FONT_BODY,
                         text_color=C["text700"], width=90, anchor="center").pack(side="left")
            ctk.CTkLabel(rw, text=f'{item["days"]} days', font=FONT_BODY,
                         text_color=C["text300"], width=60, anchor="center").pack(side="left")
            ctk.CTkLabel(rw, text=f'₹{item["revenue"]:,}', font=("Segoe UI", 13, "bold"),
                         text_color=C["olive600"], width=100, anchor="e").pack(side="left", padx=16)
            if rank < len(best_sellers):
                ctk.CTkFrame(bs_card, height=1, fg_color=C["divider"]).pack(fill="x", padx=12)

        ctk.CTkLabel(inner,
                     text="🤖  ML models retrained nightly · Data from end-of-day logs",
                     font=FONT_SMALL, text_color=C["text300"]).pack(pady=(12, 4))

    def _revenue_chart(self, parent, summary):
        labels  = summary.get("labels",  [])
        revenue = summary.get("revenue", [])
        waste   = summary.get("waste",   [])

        fig = Figure(figsize=(6, 3), dpi=96, facecolor=C["card"])
        ax  = fig.add_subplot(111)
        fig.subplots_adjust(left=0.1, right=0.97, top=0.92, bottom=0.14)
        ax.set_facecolor(C["card"])
        x     = range(len(labels))
        width = 0.38
        ax.bar([i - width / 2 for i in x], revenue, width,
               color=C["olive600"], label="Revenue", zorder=3)
        ax.bar([i + width / 2 for i in x], waste, width,
               color=C["red500"], alpha=0.7, label="Waste", zorder=3)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=10, color=C["text500"])
        ax.yaxis.set_tick_params(labelsize=9, labelcolor=C["text300"])
        ax.tick_params(axis="both", which="both", length=0)
        ax.spines[:].set_visible(False)
        ax.yaxis.grid(True, color=C["sage200"], linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"₹{int(v / 1000)}K" if v >= 1000 else f"₹{int(v)}")
        )
        leg = ax.legend(fontsize=9, frameon=False, loc="upper right", ncol=2)
        for txt in leg.get_texts():
            txt.set_color(C["text500"])
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(0, 12))

    def _spoilage_chart(self, parent, spoilage):
        names  = [s["name"]  for s in spoilage]
        values = [s["value"] for s in spoilage]
        colours = [C["red500"], "#C0602B", C["amber500"], C["olive500"], C["sage500"]]

        fig = Figure(figsize=(4, 3), dpi=96, facecolor=C["card"])
        ax  = fig.add_subplot(111)
        fig.subplots_adjust(left=0.28, right=0.88, top=0.92, bottom=0.12)
        ax.set_facecolor(C["card"])
        bars = ax.barh(names, values, color=colours[:len(names)], alpha=0.85, height=0.55)
        ax.tick_params(axis="both", which="both", length=0)
        ax.spines[:].set_visible(False)
        ax.xaxis.grid(True, color=C["sage200"], linewidth=0.8)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"₹{int(v)}"))
        ax.tick_params(axis="y", labelsize=10, labelcolor=C["text500"])
        ax.tick_params(axis="x", labelsize=9,  labelcolor=C["text300"])
        for bar, val in zip(bars, values):
            ax.text(val + 8, bar.get_y() + bar.get_height() / 2,
                    f"₹{val}", va="center", ha="left",
                    fontsize=9, fontweight="bold", color=C["text500"])
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(0, 12))


# ════════════════════════════════════════════════════════════════════
#  SCREEN 5 — PHASE 4 LAB (vision + freshness + copilot)
# ════════════════════════════════════════════════════════════════════

class Phase4Screen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self._data_loaded = False

        # Header
        hdr = ctk.CTkFrame(self, fg_color=C["olive800"], corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Phase 4 — Smart Inventory Lab", font=("Segoe UI", 20, "bold"), text_color=C["white"]).pack(side="left", padx=24, pady=18)
        self.status = ctk.CTkLabel(hdr, text="Ready", font=FONT_BODY, text_color=C["sage400"])
        self.status.pack(side="right", padx=24)

        # Main Workspace Container split into Left (Controls) and Right (Live Camera Preview)
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        # Left Column for Controls and Text Output (70% width)
        self.left_col = ctk.CTkFrame(main_container, fg_color="transparent")
        self.left_col.pack(side="left", fill="both", expand=True, padx=(18, 9), pady=16)

        self.scroll = ctk.CTkScrollableFrame(self.left_col, fg_color=C["bg"], corner_radius=0)
        self.scroll.pack(fill="both", expand=True)

        # Right Column for Live Camera / Image Preview (30% width)
        self.right_col = ctk.CTkFrame(main_container, fg_color="transparent", width=340)
        self.right_col.pack(side="right", fill="both", padx=(9, 18), pady=16)
        self.right_col.pack_propagate(False)

        # Build Visual Preview Block in the Right Column
        preview_card = card(self.right_col)
        preview_card.pack(fill="both", expand=True)

        ctk.CTkLabel(preview_card, text="📸 VISUAL PREVIEW & STATUS", font=FONT_SUBHEAD, text_color=C["olive800"]).pack(anchor="w", padx=16, pady=(14, 4))
        
        # A container for the image
        self.preview_image_lbl = ctk.CTkLabel(
            preview_card, 
            text="No Image Captured\n\nClick 'Capture & Detect'\nor 'Detect Item' to start.", 
            font=FONT_SMALL, 
            text_color=C["text300"], 
            fg_color=C["sage50"], 
            corner_radius=10, 
            height=260
        )
        self.preview_image_lbl.pack(fill="x", padx=16, pady=8)

        # A container for detection status/highlights
        self.preview_status_card = ctk.CTkFrame(preview_card, fg_color=C["sage100"], corner_radius=10, height=130)
        self.preview_status_card.pack(fill="x", padx=16, pady=8)
        self.preview_status_card.pack_propagate(False)

        self.preview_highlight_lbl = ctk.CTkLabel(self.preview_status_card, text="Status: Idle", font=FONT_SUBHEAD, text_color=C["olive800"])
        self.preview_highlight_lbl.pack(anchor="w", padx=12, pady=(10, 2))

        self.preview_detail_lbl = ctk.CTkLabel(self.preview_status_card, text="Waiting for visual input...", font=FONT_SMALL, text_color=C["text500"])
        self.preview_detail_lbl.pack(anchor="w", padx=12)
        
        self.preview_topk_lbl = ctk.CTkLabel(self.preview_status_card, text="", font=FONT_SMALL, text_color=C["text300"])
        self.preview_topk_lbl.pack(anchor="w", padx=12)

        # Populate the Left Column Scroll View
        top = ctk.CTkFrame(self.scroll, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=16)
        top.columnconfigure((0,1,2), weight=1)

        self.detect_btn = ctk.CTkButton(top, text="📷 Detect Item", height=42, fg_color=C["olive600"], command=self._detect_image)
        self.detect_btn.grid(row=0, column=0, padx=6, sticky="ew")
        self.fresh_btn = ctk.CTkButton(top, text="🧪 Freshness Check", height=42, fg_color=C["amber500"], text_color=C["olive900"], command=self._freshness_image)
        self.fresh_btn.grid(row=0, column=1, padx=6, sticky="ew")
        self.voice_btn = ctk.CTkButton(top, text="🎙  Voice Query", height=42, fg_color=C["sage500"], command=self._voice_text)
        self.voice_btn.grid(row=0, column=2, padx=6, sticky="ew")

        quick = ctk.CTkFrame(self.scroll, fg_color="transparent")
        quick.pack(fill="x", padx=18, pady=(0, 8))
        quick.columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(quick, text="📸 Capture & Detect", height=38, fg_color=C["olive700"], command=self._detect_from_camera).grid(row=0, column=0, padx=6, sticky="ew")
        ctk.CTkButton(quick, text="🧪 Capture & Score", height=38, fg_color=C["amber500"], text_color=C["olive900"], command=self._freshness_from_camera).grid(row=0, column=1, padx=6, sticky="ew")
        ctk.CTkButton(quick, text="🗣 Record & Ask", height=38, fg_color=C["sage500"], command=self._voice_from_mic).grid(row=0, column=2, padx=6, sticky="ew")

        panel = card(self.scroll)
        panel.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        ctk.CTkLabel(panel, text="Copilot Query", font=FONT_SUBHEAD, text_color=C["olive800"]).pack(anchor="w", padx=16, pady=(14, 4))
        self.query = ctk.CTkEntry(panel, height=40, placeholder_text="Ask: Which items expire this week?")
        self.query.pack(fill="x", padx=16, pady=(0, 10))
        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=16)
        ctk.CTkButton(btn_row, text="Ask Copilot", command=self._ask_copilot).pack(side="left")
        ctk.CTkButton(btn_row, text="Refresh Snapshot", fg_color=C["sidebar2"], command=self.load_if_needed).pack(side="left", padx=8)

        ctk.CTkLabel(panel, text="Output", font=FONT_SUBHEAD, text_color=C["olive800"]).pack(anchor="w", padx=16, pady=(16, 4))
        self.output = ctk.CTkTextbox(panel, height=280, wrap="word")
        self.output.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._write("Phase 4 tools are ready. Pick an image or ask a question.")

    def _write(self, text):
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)

    def _append(self, text):
        self.output.insert("end", "\n" + text)
        self.output.see("end")

    def display_preview_image(self, path):
        try:
            from PIL import Image
            img = Image.open(path)
            img.thumbnail((300, 260))
            ctk_img = ctk.CTkImage(light_image=img, size=img.size)
            self.preview_image_lbl.configure(image=ctk_img, text="")
            self.preview_image_lbl.image = ctk_img
        except Exception as e:
            print(f"Failed to display preview image: {e}")

    def load_if_needed(self):
        if self._data_loaded:
            return
        self._data_loaded = True
        self.status.configure(text="Loading snapshot…")
        def work():
            return {
                "inventory": api.get_inventory(),
                "reorder": api.get_reorder_suggestions(),
                "vision": api.get_vision_summary(),
            }
        def ok(data):
            vision = data.get("vision", {})
            detected = vision.get("detected_items", [])
            present = vision.get("present_items", [])
            missing = vision.get("missing_items", [])
            self.status.configure(
                text=f"Loaded: {len(data['inventory'])} inventory · {len(data['reorder'])} reorder · {len(detected)} vision hits"
            )
            self._write(
                "Inventory snapshot:\n"
                + "\n".join(f"• {i['item_name']} — {i['quantity']} {i['unit']} — {i['freshness_level']}" for i in data["inventory"][:10])
                + "\n\nVision snapshot:\n"
                + "\n".join(f"• {i['item_name']} — seen {i['count']}x — conf {i['avg_confidence']}" for i in detected[:5])
                + "\n\nPresent items:\n"
                + "\n".join(f"• {i['item_name']} — {i['quantity']} {i.get('unit','kg')}" for i in present[:8])
                + "\n\nMissing / at-risk items:\n"
                + "\n".join(f"• {i['item_name']} — {i.get('reason','unknown')}" for i in missing[:8])
                + "\n\nReorder snapshot:\n"
                + "\n".join(f"• {r['name']} — {r['qty']} kg — {r['conf']}" for r in data["reorder"][:10])
            )
        def err(msg):
            self.status.configure(text="Load failed")
            self._write(f"Failed to load snapshot:\n{msg}")
        run_async(work, callback=ok, error_callback=err, root=self)

    def _pick_image(self):
        path = filedialog.askopenfilename(title="Select image", filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp"), ("All files", "*.*")])
        return path or None

    def _capture_image(self):
        try:
            camera_index = int(os.getenv("VISION_CAPTURE_INDEX", "0"))
        except Exception:
            camera_index = 0
        return capture_webcam_frame(camera_index=camera_index)

    def _detect_from_camera(self):
        self.status.configure(text="Opening camera…")
        self.preview_highlight_lbl.configure(text="📷 Camera: Initializing...")
        self.preview_detail_lbl.configure(text="Capturing frame, warming up...")
        self.preview_topk_lbl.configure(text="")
        try:
            path = self._capture_image()
            self.display_preview_image(path)
            self.preview_highlight_lbl.configure(text="📷 Camera: Captured")
            self.preview_detail_lbl.configure(text="Analyzing frame with MobileNetV3...")
        except Exception as exc:
            self.status.configure(text="Camera unavailable")
            self.preview_highlight_lbl.configure(text="❌ Camera Error")
            self.preview_detail_lbl.configure(text=str(exc))
            messagebox.showerror("Camera", str(exc))
            return
            
        self.status.configure(text="Detecting camera frame…")
        def work():
            try:
                return api.detect_image(path)
            finally:
                try:
                    os.unlink(path)
                except Exception:
                    pass
        def ok(data):
            self.status.configure(text=f"Detected {len(data)} object(s)")
            self._write("Camera detection results:\n" + "\n".join(f"• {d['item_name']} | conf={d['confidence']} | qty={d['quantity_detected']}" for d in data))
            
            if data:
                d = data[0]
                item_name = d['item_name']
                conf = d['confidence']
                cat = d['category']
                
                if item_name == "uncertain":
                    self.preview_status_card.configure(fg_color=C["red200"])
                    self.preview_highlight_lbl.configure(text="⚠️ UNCERTAIN PRODUCE", text_color=C["red700"])
                    self.preview_detail_lbl.configure(text="Confidence below threshold (<0.35)", text_color=C["red700"])
                else:
                    self.preview_status_card.configure(fg_color=C["sage100"])
                    self.preview_highlight_lbl.configure(text=f"🍎 {item_name.upper()}", text_color=C["olive800"])
                    self.preview_detail_lbl.configure(text=f"Type: {cat.upper()} | Conf: {conf*100:.1f}%", text_color=C["text700"])
                
                top_k = d.get("top_k", [])
                if top_k:
                    top_k_str = ", ".join(f"{x['item_name']} ({x['confidence']*100:.0f}%)" for x in top_k)
                    self.preview_topk_lbl.configure(text=f"Guesses: {top_k_str}")
                else:
                    self.preview_topk_lbl.configure(text="")
                    
        def err(msg):
            self.status.configure(text="Detection failed")
            self.preview_highlight_lbl.configure(text="❌ Detection Failed")
            self.preview_detail_lbl.configure(text=msg)
            self._write(msg)
        run_async(work, callback=ok, error_callback=err, root=self)

    def _freshness_from_camera(self):
        self.status.configure(text="Opening camera…")
        self.preview_highlight_lbl.configure(text="📷 Camera: Initializing...")
        self.preview_detail_lbl.configure(text="Capturing frame, warming up...")
        self.preview_topk_lbl.configure(text="")
        try:
            path = self._capture_image()
            self.display_preview_image(path)
            self.preview_highlight_lbl.configure(text="📷 Camera: Captured")
            self.preview_detail_lbl.configure(text="Assessing freshness...")
        except Exception as exc:
            self.status.configure(text="Camera unavailable")
            self.preview_highlight_lbl.configure(text="❌ Camera Error")
            self.preview_detail_lbl.configure(text=str(exc))
            messagebox.showerror("Camera", str(exc))
            return
            
        self.status.configure(text="Scoring camera frame…")
        def work():
            try:
                return api.assess_freshness(path, item_name="camera_capture")
            finally:
                try:
                    os.unlink(path)
                except Exception:
                    pass
        def ok(data):
            score = data['freshness_score']
            level = data['freshness_level']
            self.status.configure(text=f"Freshness: {score}/100")
            self._write(
                "Camera freshness result:\n"
                f"• Item: {data['item_name']}\n"
                f"• Score: {score}\n"
                f"• Level: {level}\n"
                f"• Color: {data['color_score']} · Texture: {data['texture_score']}\n"
                f"• Defect: {data['defect_score']} · Mold: {data['mold_score']} · Bruise: {data['bruise_score']}"
            )
            
            fg = C["sage100"] if score >= 80 else C["amber200"] if score >= 50 else C["red200"]
            text_c = C["olive600"] if score >= 80 else C["amber700"] if score >= 50 else C["red700"]
            
            self.preview_status_card.configure(fg_color=fg)
            self.preview_highlight_lbl.configure(text=f"🧪 FRESHNESS: {score}/100", text_color=text_c)
            self.preview_detail_lbl.configure(text=f"Level: {level.upper()} | Bruise: {data['bruise_score']} | Mold: {data['mold_score']}", text_color=text_c)
            self.preview_topk_lbl.configure(text="")
            
        def err(msg):
            self.status.configure(text="Freshness failed")
            self.preview_status_card.configure(fg_color=C["red200"])
            self.preview_highlight_lbl.configure(text="❌ Freshness Failed")
            self.preview_detail_lbl.configure(text=msg)
            self._write(msg)
        run_async(work, callback=ok, error_callback=err, root=self)

    def _voice_from_mic(self):
        self.status.configure(text="Recording microphone…")
        try:
            wav_path = record_microphone_audio(seconds=3)
        except Exception as exc:
            self.status.configure(text="Voice unavailable")
            messagebox.showerror("Voice", str(exc))
            return
        self.status.configure(text="Transcribing voice…")
        def work():
            try:
                return api.voice_query(audio_path=wav_path)
            finally:
                try:
                    os.unlink(wav_path)
                except Exception:
                    pass
        def ok(data):
            self.status.configure(text=data.get("mode", "voice"))
            transcript = data.get('transcript', '')
            response = data.get('response_text', '')
            actions = data.get("actions", [])
            actions_str = ""
            if actions:
                actions_str = "\n\n⚡ Smart Actions Orchestrated:\n" + "\n".join(f"✔ {a['type'].replace('_', ' ').title()}: {a.get('parameters', {})}" for a in actions)
            self._write(f"Transcript: {transcript}\n\nResponse: {response}{actions_str}")
            if response:
                play_tts_async(response, self)
        def err(msg):
            self.status.configure(text="Voice failed")
            self._write(msg)
        run_async(work, callback=ok, error_callback=err, root=self)

    def _detect_image(self):
        path = self._pick_image()
        if not path:
            return
        self.display_preview_image(path)
        self.preview_highlight_lbl.configure(text="🖼 Image Uploaded")
        self.preview_detail_lbl.configure(text="Analyzing image...")
        self.preview_topk_lbl.configure(text="")
        
        self.status.configure(text="Detecting…")
        def work():
            return api.detect_image(path)
        def ok(data):
            self.status.configure(text=f"Detected {len(data)} object(s)")
            self._write("Detection results:\n" + "\n".join(f"• {d['item_name']} | conf={d['confidence']} | qty={d['quantity_detected']}" for d in data))
            
            if data:
                d = data[0]
                item_name = d['item_name']
                conf = d['confidence']
                cat = d['category']
                
                if item_name == "uncertain":
                    self.preview_status_card.configure(fg_color=C["red200"])
                    self.preview_highlight_lbl.configure(text="⚠️ UNCERTAIN PRODUCE", text_color=C["red700"])
                    self.preview_detail_lbl.configure(text="Confidence below threshold (<0.35)", text_color=C["red700"])
                else:
                    self.preview_status_card.configure(fg_color=C["sage100"])
                    self.preview_highlight_lbl.configure(text=f"🍎 {item_name.upper()}", text_color=C["olive800"])
                    self.preview_detail_lbl.configure(text=f"Type: {cat.upper()} | Conf: {conf*100:.1f}%", text_color=C["text700"])
                
                top_k = d.get("top_k", [])
                if top_k:
                    top_k_str = ", ".join(f"{x['item_name']} ({x['confidence']*100:.0f}%)" for x in top_k)
                    self.preview_topk_lbl.configure(text=f"Guesses: {top_k_str}")
                else:
                    self.preview_topk_lbl.configure(text="")
        def err(msg):
            self.status.configure(text="Detection failed")
            self.preview_highlight_lbl.configure(text="❌ Detection Failed")
            self.preview_detail_lbl.configure(text=msg)
            self._write(msg)
        run_async(work, callback=ok, error_callback=err, root=self)

    def _freshness_image(self):
        path = self._pick_image()
        if not path:
            return
        self.display_preview_image(path)
        self.preview_highlight_lbl.configure(text="🖼 Image Uploaded")
        self.preview_detail_lbl.configure(text="Assessing freshness...")
        self.preview_topk_lbl.configure(text="")
        
        self.status.configure(text="Scoring freshness…")
        def work():
            return api.assess_freshness(path, item_name=Path(path).stem)
        def ok(data):
            score = data['freshness_score']
            level = data['freshness_level']
            self.status.configure(text=f"Freshness: {score}/100")
            self._write(
                "Freshness result:\n"
                f"• Item: {data['item_name']}\n"
                f"• Score: {score}\n"
                f"• Level: {level}\n"
                f"• Color: {data['color_score']} · Texture: {data['texture_score']}\n"
                f"• Defect: {data['defect_score']} · Mold: {data['mold_score']} · Bruise: {data['bruise_score']}"
            )
            
            fg = C["sage100"] if score >= 80 else C["amber200"] if score >= 50 else C["red200"]
            text_c = C["olive600"] if score >= 80 else C["amber700"] if score >= 50 else C["red700"]
            
            self.preview_status_card.configure(fg_color=fg)
            self.preview_highlight_lbl.configure(text=f"🧪 FRESHNESS: {score}/100", text_color=text_c)
            self.preview_detail_lbl.configure(text=f"Level: {level.upper()} | Bruise: {data['bruise_score']} | Mold: {data['mold_score']}", text_color=text_c)
            self.preview_topk_lbl.configure(text="")
        def err(msg):
            self.status.configure(text="Freshness failed")
            self.preview_status_card.configure(fg_color=C["red200"])
            self.preview_highlight_lbl.configure(text="❌ Freshness Failed")
            self.preview_detail_lbl.configure(text=msg)
            self._write(msg)
        from pathlib import Path
        run_async(work, callback=ok, error_callback=err, root=self)

    def _ask_copilot(self):
        q = self.query.get().strip()
        if not q:
            return
        self.status.configure(text="Thinking…")
        def work():
            return api.ask_copilot(q)
        def ok(data):
            self.status.configure(text=data.get("intent", "copilot"))
            response = data.get('answer','')
            actions = data.get("actions", [])
            actions_str = ""
            if actions:
                actions_str = "\n\n⚡ Smart Actions Orchestrated:\n" + "\n".join(f"✔ {a['type'].replace('_', ' ').title()}: {a.get('parameters', {})}" for a in actions)
            self._write(f"Answer:\n{response}{actions_str}\n\nEvidence:\n" + "\n".join(str(e) for e in data.get("evidence", [])))
            if response:
                play_tts_async(response, self)
        def err(msg):
            self.status.configure(text="Copilot failed")
            self._write(msg)
        run_async(work, callback=ok, error_callback=err, root=self)

    def _voice_text(self):
        q = self.query.get().strip() or "Show inventory risk"
        self.status.configure(text="Voice processing…")
        def work():
            return api.voice_query(text=q)
        def ok(data):
            self.status.configure(text=data.get("mode", "voice"))
            response = data.get('response_text','')
            actions = data.get("actions", [])
            actions_str = ""
            if actions:
                actions_str = "\n\n⚡ Smart Actions Orchestrated:\n" + "\n".join(f"✔ {a['type'].replace('_', ' ').title()}: {a.get('parameters', {})}" for a in actions)
            self._write(f"Transcript: {data.get('transcript','')}\n\nResponse: {response}{actions_str}")
            if response:
                play_tts_async(response, self)
        def err(msg):
            self.status.configure(text="Voice failed")
            self._write(msg)
        run_async(work, callback=ok, error_callback=err, root=self)


# ════════════════════════════════════════════════════════════════════
#  MAIN APP — Login gate → Sidebar + Lazy Navigation
# ════════════════════════════════════════════════════════════════════

class VisualAgroApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VisualAgro — AI Vendor Dashboard")
        self.geometry("1200x750")
        self.minsize(1000, 650)
        self.configure(fg_color=C["bg"])
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self._show_login()

    def _show_login(self):
        self.login_screen = LoginScreen(self, on_success=self._on_login_success)
        self.login_screen.pack(fill="both", expand=True)

    def _on_login_success(self):
        self.login_screen.destroy()
        self._build_layout()

    def _build_layout(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0,
                                    fg_color=C["sidebar"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkFrame(self.sidebar, fg_color=C["sage500"],
                     corner_radius=0, height=5).pack(fill="x")

        logo_f = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=90)
        logo_f.pack(fill="x", pady=(0, 4))
        logo_f.pack_propagate(False)
        ctk.CTkLabel(logo_f, text="🌿", font=("Segoe UI Emoji", 32)).pack(pady=(14, 0))
        ctk.CTkLabel(logo_f, text="VisualAgro",
                     font=("Segoe UI", 17, "bold"),
                     text_color=C["white"]).pack()
        ctk.CTkLabel(logo_f, text="Vendor Dashboard",
                     font=("Segoe UI", 10),
                     text_color=C["sage400"]).pack()

        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color=C["siderbdr"]).pack(fill="x", padx=16, pady=12)

        self.nav_btns = {}
        nav_items = [
            ("🏠", "Dashboard", DashboardScreen),
            ("📋", "Log Stock",  StockEntryScreen),
            ("🛒", "Buy List",   ReorderScreen),
            ("📊", "Insights",   InsightsScreen),
            ("🧠", "Phase 4",    Phase4Screen),
        ]

        self.screens = {}
        self.screen_classes = {name: cls for _, name, cls in nav_items}
        self.current = tk.StringVar(value="Dashboard")

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        for ico, name, _ in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {ico}   {name}",
                anchor="w",
                font=FONT_NAV,
                fg_color="transparent",
                hover_color=C["sidebar2"],
                text_color=C["sage300"],
                height=44,
                corner_radius=10,
                command=lambda n=name: self._switch(n),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_btns[name] = btn

        # Vendor card at bottom
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(fill="both", expand=True)
        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color=C["siderbdr"]).pack(fill="x", padx=16, pady=8)
        vendor_f = ctk.CTkFrame(self.sidebar, fg_color=C["sidebar2"], corner_radius=10)
        vendor_f.pack(fill="x", padx=10, pady=(0, 16))
        av = ctk.CTkFrame(vendor_f, width=36, height=36, corner_radius=18,
                          fg_color=C["sage500"])
        av.pack(side="left", padx=10, pady=10)
        av.pack_propagate(False)
        ctk.CTkLabel(av, text="RB", font=("Segoe UI", 11, "bold"),
                     text_color=C["olive800"]).pack(expand=True)
        info = ctk.CTkFrame(vendor_f, fg_color="transparent")
        info.pack(side="left", fill="y", pady=8)
        ctk.CTkLabel(info, text="Ramesh Bhai", font=("Segoe UI", 11, "bold"),
                     text_color=C["white"]).pack(anchor="w")
        ctk.CTkLabel(info, text="Dadar Market, Mumbai",
                     font=("Segoe UI", 9),
                     text_color=C["sage400"]).pack(anchor="w")

        # Navigate to Dashboard first — lazy-loads only that screen
        self._switch("Dashboard")

    def _get_or_create_screen(self, name):
        """Lazy-create a screen the first time it's navigated to."""
        if name not in self.screens:
            cls = self.screen_classes[name]
            sc = cls(self.content)
            sc.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.screens[name] = sc
        return self.screens[name]

    def _switch(self, name):
        sc = self._get_or_create_screen(name)
        sc.lift()
        # Trigger data load (no-op if already loaded — cached)
        if hasattr(sc, "load_if_needed"):
            sc.load_if_needed()
        for n, btn in self.nav_btns.items():
            if n == name:
                btn.configure(fg_color=C["sidebar3"], text_color=C["sage500"])
            else:
                btn.configure(fg_color="transparent", text_color=C["sage300"])
        self.current.set(name)


# ── Entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app = VisualAgroApp()
    app.mainloop()
