
"""
run_phase3.py — Start VisualAgro Phase 3 stack.

Flow:
1. Seed database
2. Start backend
3. Wait for server
4. Warm up the AI brain
5. Launch desktop app
"""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from api_client import VisualAgroAPI

PROJECT_DIR = Path(__file__).resolve().parent
BASE_URL = "http://127.0.0.1:8000"
DEMO_EMAIL = "ramesh@visualagro.in"
DEMO_PASSWORD = "demo1234"


def wait_for_backend(timeout: int = 60) -> None:
    deadline = time.time() + timeout
    last_error: str | None = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:
            last_error = str(exc)
            time.sleep(1)

    raise RuntimeError(f"Backend did not become ready within {timeout}s. Last error: {last_error}")


def main() -> None:
    print("VisualAgro Phase 3 - starting...")
    subprocess.check_call([sys.executable, "seed.py"], cwd=PROJECT_DIR)

    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(PROJECT_DIR),
    )

    try:
        wait_for_backend()
        api = VisualAgroAPI(BASE_URL)
        api.login(DEMO_EMAIL, DEMO_PASSWORD)

        print("Warming up AI brain...")
        try:
            api.train_ai()
        except Exception as exc:
            print(f"AI warm-up skipped: {exc}")

        try:
            api.refresh_ai_reorder()
        except Exception as exc:
            print(f"AI reorder refresh skipped: {exc}")

        from visualagro_connected import VisualAgroApp
        app = VisualAgroApp()
        app.mainloop()
    finally:
        if backend.poll() is None:
            backend.terminate()
            try:
                backend.wait(timeout=10)
            except Exception:
                backend.kill()


if __name__ == "__main__":
    main()
