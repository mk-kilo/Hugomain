#!/usr/bin/env python3
"""Refresh a public, unauthenticated Ofox model price snapshot.
No credentials, top-ups, or billable model calls. A failed response never overwrites
the previous known-good snapshot. Prices are observations, not quotes.
"""
import datetime as dt
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ofox-public-prices.json"
SOURCE = "https://api.ofox.ai/v1/models"

def valid_rate(value):
    try:
        if isinstance(value, bool): return None
        n = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not (0 <= n <= 0.01): return None
    return n

def main():
    request = urllib.request.Request(SOURCE, headers={
        "Accept": "application/json",
        "User-Agent": "JXZNE-public-pricing-research/1.0"
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read(4_000_000))
    models = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise ValueError("Unexpected Ofox public catalog format")
    selected = []
    for model in models:
        if not isinstance(model, dict) or not isinstance(model.get("pricing"), dict):
            continue
        name = model.get("id")
        if not isinstance(name, str) or not (1 <= len(name) <= 150):
            continue
        rates = model["pricing"]
        prompt = valid_rate(rates.get("prompt"))
        completion = valid_rate(rates.get("completion"))
        if prompt is None or completion is None or prompt + completion <= 0:
            continue
        selected.append({
            "id": name,
            "promptPerToken": prompt,
            "completionPerToken": completion,
            "promptPerMillion": round(prompt * 1_000_000, 6),
            "completionPerMillion": round(completion * 1_000_000, 6),
            "endpoints": [x for x in model.get("endpoints", []) if isinstance(x, str)][:8]
        })
    selected.sort(key=lambda x: x["id"])
    if len(selected) < 5:
        raise ValueError("Fewer than 5 validated public rates; existing file preserved")
    previous = json.loads(OUTPUT.read_text("utf-8")) if OUTPUT.exists() else {}
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    result = {
        "source": SOURCE,
        "fetchedAt": now,
        "catalogCount": len(models),
        "note": "Public unauthenticated catalog prices observed at fetchedAt. USD per million tokens. Not a transaction quote, invoice, confirmation of model compatibility, or guarantee that checkout matches.",
        "requested": previous.get("requested", []),
        "missing": [i for i in previous.get("requested", []) if i not in {x["id"] for x in selected}],
        "models": selected
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("Saved", len(selected), "verified public rate pairs from", len(models), "catalog models")
if __name__ == "__main__":
    main()
