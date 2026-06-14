"""
run_phase2.py — Start the VisualAgro Phase 2 stack.

What it does:
  1. Seeds the database
  2. Starts the FastAPI backend
  3. Waits until the API is reachable
  4. Launches the desktop app

Run:
  python run_phase2.py
"""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
BASE_URL = "http://127.0.0.1:8000"


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


def run(cmd: list[str], *, cwd: Path, background: bool = False) -> subprocess.Popen | None:
    if background:
        return subprocess.Popen(cmd, cwd=str(cwd))
    subprocess.check_call(cmd, cwd=str(cwd))
    return None


def main() -> None:
    print("VisualAgro Phase 2 - starting...")
    print("1/3 Seeding database...")
    run([sys.executable, "seed.py"], cwd=PROJECT_DIR)

    print("2/3 Starting backend on http://127.0.0.1:8000 ...")
    backend = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
        ],
        cwd=str(PROJECT_DIR),
    )

    try:
        print("Waiting for backend to become reachable...")
        wait_for_backend()
        print("3/3 Launching desktop app...")

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
