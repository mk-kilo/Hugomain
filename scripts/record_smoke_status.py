#!/usr/bin/env python3
"""Update ofox-smoke-status.json only after a real passing smoke run.

This script does not call Ofox. The workflow runs it only after tests/ofox_smoke.py
exits 0. It refuses to write the repository status file unless all of these hold:
- OFOX_SMOKE_PASSED=1
- OFOX_API_KEY is non-empty (the key is never printed or stored)
- GITHUB_ACTIONS=true

Codex CLI and Claude Code are never marked passed. The smoke test does not launch
those clients. Cursor stays "provider_marked_incompatible".
"""
import datetime
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "ofox-smoke-status.json"


def load(path):
    if not path.exists():
        return {
            "schema": 1,
            "overall": "unverified",
            "updatedAt": None,
            "source": "tests/ofox_smoke.py",
            "note": "No successful authenticated run is recorded.",
            "checks": {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    path = pathlib.Path(os.environ.get("OFOX_SMOKE_STATUS_PATH") or DEFAULT_PATH)
    writing_repo_file = path.resolve() == DEFAULT_PATH.resolve()
    key = os.environ.get("OFOX_API_KEY", "")
    if os.environ.get("OFOX_SMOKE_PASSED") != "1":
        print("REFUSING: OFOX_SMOKE_PASSED is not 1. Status file left unchanged.")
        return 2
    if not key.strip():
        print("REFUSING: OFOX_API_KEY is empty. Status file left unchanged.")
        return 2
    if writing_repo_file and os.environ.get("GITHUB_ACTIONS") != "true":
        print("REFUSING: the repo status file is only updated on GitHub Actions after smoke exits 0.")
        return 2
    if key != key.strip() or key.lower().startswith(("bearer ", "authorization:", "x-api-key:")):
        print("REFUSING: key failed the same format checks as tests/ofox_smoke.py. Status file left unchanged.")
        return 2

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    status = load(path)
    checks = status.setdefault("checks", {})
    passed_detail = "tests/ofox_smoke.py exited 0 on GitHub Actions. This is one authenticated call, not a latency, uptime, or client-tool result."
    checks["openai_responses"] = {"status": "passed", "passedAt": now, "detail": passed_detail}
    checks["anthropic_messages"] = {"status": "passed", "passedAt": now, "detail": passed_detail}
    checks["codex_cli"] = {
        "status": "unverified",
        "passedAt": None,
        "detail": "tests/ofox_smoke.py does not launch Codex CLI. An API smoke pass does not verify Codex.",
    }
    checks["claude_code"] = {
        "status": "unverified",
        "passedAt": None,
        "detail": "tests/ofox_smoke.py does not launch Claude Code. An API smoke pass does not verify Claude Code.",
    }
    checks["cursor_direct"] = {
        "status": "provider_marked_incompatible",
        "passedAt": None,
        "detail": "Ofox documents direct Cursor integration as unsuitable.",
        "source": "https://ofox.ai/docs/integrations/cursor",
        "sourceUpdated": "2026-10-16",
    }
    for name, check in checks.items():
        if name not in ("openai_responses", "anthropic_messages") and check.get("status") == "passed":
            print("REFUSING: attempted to mark", name, "passed")
            return 2
    status.update({
        "schema": 1,
        "overall": "api_smoke_passed",
        "updatedAt": now,
        "source": "tests/ofox_smoke.py",
        "recordedBy": "scripts/record_smoke_status.py",
        "note": "OpenAI Responses and Anthropic Messages smoke calls passed. Codex CLI and Claude Code remain unverified. No latency or success-rate figures are included.",
    })
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Recorded API smoke pass at", now, "for openai_responses and anthropic_messages only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
