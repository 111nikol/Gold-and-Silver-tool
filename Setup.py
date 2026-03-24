#!/usr/bin/env python3
"""Cross-platform installer for the Gold/Silver tracker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQ = ROOT / "requirements.txt"


def venv_python() -> Path:
    if sys.platform.startswith("win"):
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def main() -> int:
    if not REQ.exists():
        print(f"❌ requirements.txt not found: {REQ}")
        return 1

    print(f"[1/4] Creating virtual environment: {VENV_DIR}")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    py = venv_python()
    if not py.exists():
        print(f"❌ venv python not found: {py}")
        return 1

    print("[2/4] Upgrading pip")
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True)

    print("[3/4] Installing requirements")
    subprocess.run([str(py), "-m", "pip", "install", "-r", str(REQ)], check=True)

    print("[4/4] Done")
    print("✅ Setup complete")
    print()
    print("Next:")
    print("  - Launch GUI: python tracker_launcher.py")
    print("  - Use Snapshot button inside GUI for one-shot updates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
