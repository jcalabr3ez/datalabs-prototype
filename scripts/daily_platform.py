#!/usr/bin/env python3
"""One daily file pass for the whole platform.

Runs the existing refresh scripts. Does not invent figures.
Does not scrape the wealth-tax atlas or the Florida register: those
are editorial and live in scripts/daily_platform_pass.md.

Never pushes to main. Designed to run from the daily-platform Action
or from the daily Cursor Automation.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (label, argv, required). Reliability can miss when the MBTA portal is down.
STEPS = [
    ("DL-03 ridership and cost", ["python3", "scripts/refresh_dl03.py"], True),
    ("DL-03 service", ["python3", "scripts/refresh_dl03_service.py"], True),
    ("DL-03 reliability", ["python3", "scripts/refresh_dl03_reliability.py"], False),
    ("DL-05 CTHRU retirees", ["python3", "scripts/refresh_dl05.py"], True),
    ("suite DL-06 to DL-34", ["python3", "scripts/refresh_suite.py"], True),
]


def run(label, argv, required):
    print(f"daily_platform: {label}")
    try:
        subprocess.check_call(argv, cwd=ROOT)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"daily_platform: FAIL {label} exit {exc.returncode}")
        if required:
            raise
        return False


def main():
    today = date.today()
    failed = []
    for label, argv, required in STEPS:
        try:
            ok = run(label, argv, required)
        except subprocess.CalledProcessError:
            sys.exit(1)
        if not ok:
            failed.append(label)

    force_dl04 = os.environ.get("DATALABS_FORCE_DL04") == "1"
    if today.month == 10 or force_dl04:
        run("DL-04 electricity (yearly file)", ["python3", "scripts/refresh_dl04.py"], True)
    else:
        print("daily_platform: skip DL-04 (yearly October; DATALABS_FORCE_DL04=1 to force)")

    subprocess.check_call(["python3", "scripts/inject_data.py"], cwd=ROOT)
    print("daily_platform: file half done")
    if failed:
        print("daily_platform: optional steps missed: " + "; ".join(failed))
        print("daily_platform: keep the last verified figure for those")


if __name__ == "__main__":
    main()
