#!/usr/bin/env python3
"""Exit non-zero unless pricing-snapshots.json contains only verified monthly observations.

Mirrors the gates in scripts/refresh_prices.py. The refresh workflow runs this
before any commit so a bad snapshot is not published.
"""
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "pricing-snapshots.json"


def problems(row):
    if not isinstance(row, dict):
        return ["not-object"]
    found = []
    if str(row.get("status", "")).lower() in ("demo", "placeholder", "unverified", "rejected"):
        found.append("status")
    if row.get("is_demo") is True or row.get("demo") is True or row.get("is_placeholder") is True:
        found.append("demo")
    if not str(row.get("source") or "").startswith("https://"):
        found.append("source")
    try:
        usd = float(row.get("usd"))
        if not 0 < usd < 5000:
            found.append("usd")
    except (TypeError, ValueError):
        found.append("usd")
    if row.get("unit") != "USD/月":
        found.append("unit")
    try:
        datetime.date.fromisoformat(str(row.get("date") or "")[:10])
    except ValueError:
        found.append("date")
    for key in ("id", "plan", "code", "channel", "product"):
        if not row.get(key):
            found.append(key)
    return found


def main():
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print("SNAPSHOT_UNREADABLE", type(exc).__name__)
        return 1
    rows = data.get("rows") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        print("NO_VERIFIED_ROWS")
        return 1
    bad = 0
    for index, row in enumerate(rows):
        found = problems(row)
        if found:
            bad += 1
            if bad <= 12:
                print("BAD_ROW", index, ",".join(found))
    if bad:
        print("REJECTED", bad, "rows. Refresh will not commit this snapshot.")
        return 1
    print("Verified monthly observations only:", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
