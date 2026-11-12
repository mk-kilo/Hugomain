#!/usr/bin/env python3
"""Call Ofox chat completions once and record the result.

Reads OFOX_API_KEY from the environment. Never prints the key and never writes
it to ofox-smoke-status.json. With no key, exits 0 and leaves the status file
unchanged (overall stays unverified).

A passing record is one HTTP 200 chat completion with non-empty message
content. Codex CLI, Claude Code, and Cursor are not launched and are not
marked passed.
"""
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATUS_PATH = pathlib.Path(os.environ.get("OFOX_SMOKE_STATUS_PATH") or (ROOT / "ofox-smoke-status.json"))
ENDPOINT = "https://api.ofox.ai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-5.4"

CURSOR_CHECK = {
    "status": "provider_marked_incompatible",
    "passedAt": None,
    "detail": "Ofox documents direct Cursor integration as unsuitable. Tab completion, Agent mode, and Auto do not follow a custom provider.",
    "source": "https://ofox.ai/docs/integrations/cursor",
    "sourceUpdated": "2026-10-16",
}


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def key_problem(key):
    if key != key.strip():
        return "leading or trailing whitespace"
    if key.lower().startswith(("bearer ", "authorization:", "x-api-key:")):
        return "prefix included; supply the raw key"
    if any(ord(char) < 33 or ord(char) > 126 for char in key):
        return "whitespace or control character"
    return ""


def load_status():
    if STATUS_PATH.exists():
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    return {"schema": 2, "checks": {}}


def write_status(status, key):
    payload = json.dumps(status, ensure_ascii=False, indent=2) + "\n"
    if key and key in payload:
        print("REFUSING: status payload contained the API key. File not written.")
        return 1
    STATUS_PATH.write_text(payload, encoding="utf-8")
    return 0


def record(key, model, http_status, latency_ms, ok, detail):
    now = utc_now()
    status = load_status()
    checks = status.setdefault("checks", {})
    checks["chat_completions"] = {
        "status": "passed" if ok else "failed",
        "passedAt": now if ok else None,
        "model": model,
        "latencyMs": latency_ms,
        "httpStatus": http_status,
        "timestamp": now,
        "detail": detail,
    }
    checks.setdefault("openai_responses", {
        "status": "unverified",
        "passedAt": None,
        "detail": "scripts/ofox-smoke.py calls Chat Completions only. It does not call the Responses API.",
    })
    checks.setdefault("anthropic_messages", {
        "status": "unverified",
        "passedAt": None,
        "detail": "scripts/ofox-smoke.py does not call the Anthropic Messages API.",
    })
    checks["codex_cli"] = {
        "status": "unverified",
        "passedAt": None,
        "detail": "scripts/ofox-smoke.py does not launch Codex CLI. Ofox publishes a Codex guide, and this run does not verify it.",
    }
    checks["claude_code"] = {
        "status": "unverified",
        "passedAt": None,
        "detail": "scripts/ofox-smoke.py does not launch Claude Code. Ofox publishes a Claude Code guide, and this run does not verify it.",
    }
    checks["cursor_direct"] = CURSOR_CHECK
    for name, check in checks.items():
        if name != "chat_completions" and check.get("status") == "passed":
            print("REFUSING: refused to keep", name, "marked passed")
            return 1
    status.update({
        "schema": 2,
        "overall": "chat_completion_passed" if ok else "failed",
        "endpoint": "POST " + ENDPOINT,
        "model": model,
        "latencyMs": latency_ms,
        "status": "passed" if ok else "failed",
        "httpStatus": http_status,
        "timestamp": now,
        "updatedAt": now,
        "recordedBy": "scripts/ofox-smoke.py",
        "note": detail,
    })
    wrote = write_status(status, key)
    if wrote == 0:
        print(
            "RECORDED",
            "status=" + status["status"],
            "model=" + model,
            "http=" + str(http_status),
            "latencyMs=" + str(latency_ms),
            "timestamp=" + now,
        )
    return wrote


def main():
    key = os.environ.get("OFOX_API_KEY", "")
    if not key:
        print("BLOCKED_NO_OFOX_API_KEY: status file left unchanged (overall stays unverified).")
        return 0
    problem = key_problem(key)
    if problem:
        print("INVALID_SECRET_FORMAT: request not sent (" + problem + "). Status file left unchanged.")
        return 2

    model = os.environ.get("OFOX_CHAT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        "max_tokens": 16,
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "jxzne-ofox-smoke/1.0",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw = response.read(65536)
            http_status = response.status
        try:
            parsed = json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return record(key, model, http_status, latency_ms, False, "HTTP 200 body was not JSON. Response body was not stored.")
        content = ""
        choices = parsed.get("choices") if isinstance(parsed, dict) else None
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                content = message["content"].strip()
        ok = http_status == 200 and bool(content)
        detail = (
            "One Chat Completions call returned message content."
            if ok
            else "The response did not include choices[0].message.content. Body was not stored."
        )
        return record(key, model, http_status, latency_ms, ok, detail)
    except urllib.error.HTTPError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        # Do not read or print the body: some gateways echo request headers.
        return record(
            key,
            model,
            exc.code,
            latency_ms,
            False,
            "Chat Completions returned HTTP " + str(exc.code) + ". Response body was not stored.",
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return record(
            key,
            model,
            None,
            latency_ms,
            False,
            "Network error before a response: " + type(exc).__name__ + ". Details were not stored.",
        )


if __name__ == "__main__":
    sys.exit(main())
