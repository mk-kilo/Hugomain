#!/usr/bin/env python3
"""Record a small set of Ofox public catalog prices. No API key.

Writes ofox-public-prices.json only after HTTP 200 and a JSON model list.
Models that are absent, or that lack a finite non-negative per-token prompt
and completion rate, are listed under "missing" and are not given a price.
Zero prompt and zero completion (non-token products in this catalog) are omitted.
Never fills gaps with guesses.
"""
import datetime
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "ofox-public-prices.json"
URL = "https://api.ofox.ai/v1/models"
REQUESTED = [
    "openai/gpt-5.4",
    "openai/gpt-5.2",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "anthropic/claude-sonnet-4.6",
]


def main():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "JXZNE-public-catalog/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status != 200:
                print("CATALOG_HTTP", response.status)
                return 1
            data = json.loads(response.read())
    except Exception as exc:
        print("CATALOG_FETCH_FAILED", type(exc).__name__)
        return 1
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        print("CATALOG_SHAPE_INVALID")
        return 1
    by_id = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            by_id[row["id"]] = row
    models = []
    missing = []
    for model_id in REQUESTED:
        row = by_id.get(model_id)
        pricing = row.get("pricing") if isinstance(row, dict) and isinstance(row.get("pricing"), dict) else None
        if pricing is None:
            missing.append(model_id)
            continue
        try:
            prompt = float(pricing.get("prompt"))
            completion = float(pricing.get("completion"))
        except (TypeError, ValueError):
            missing.append(model_id)
            continue
        if prompt < 0 or completion < 0 or prompt != prompt or completion != completion:
            missing.append(model_id)
            continue
        if prompt == 0 and completion == 0:
            missing.append(model_id)
            continue
        endpoints = row.get("supported_endpoints")
        models.append({
            "id": model_id,
            "promptPerToken": prompt,
            "completionPerToken": completion,
            "promptPerMillion": round(prompt * 1_000_000, 6),
            "completionPerMillion": round(completion * 1_000_000, 6),
            "endpoints": endpoints if isinstance(endpoints, list) else [],
        })
    if not models:
        print("NO_PRICES_RECORDED: existing file left untouched")
        return 1
    payload = {
        "source": URL,
        "fetchedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "catalogCount": len(rows),
        "note": "Observed unauthenticated public catalog rates. USD per million tokens = per-token rate × 1,000,000. Omitted models were not in this response or had no usable per-token text price. Not an invoice and not a promise that the signed-in price matches.",
        "requested": REQUESTED,
        "missing": missing,
        "models": models,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Wrote", OUT.name, "models", len(models), "missing", ",".join(missing) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
