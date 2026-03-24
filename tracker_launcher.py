#!/usr/bin/env python3
"""Compatibility launcher for the Qt GUI app."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUI_SCRIPT = ROOT / "gs_tracker_qt.py"
REQ_FILE = ROOT / "requirements.txt"
SETUP_SCRIPT = ROOT / "Setup.py"


def self_check() -> int:
    print("ROOT:", ROOT)
    print("Python:", sys.executable)
    print("requirements.txt exists:", REQ_FILE.exists())
    print("Setup.py exists:", SETUP_SCRIPT.exists())
    print("Qt GUI script exists:", GUI_SCRIPT.exists())
    return 0


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return self_check()

    from gs_tracker_qt import main as qt_main

    return qt_main()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
