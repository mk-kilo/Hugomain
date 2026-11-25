#!/usr/bin/env python3
"""Call Ofox chat completions once and record the result.

Reads OFOX_API_KEY from the environment. Never prints the key and never writes
it to ofox-smoke-status.json. With no key, exits 0 and leaves the status file
unchanged (overall stays unverified).

Accidental paste characters are removed before the request: Unicode whitespace
(space, tab, CR, LF, and other characters for which str.isspace() is true) and
an explicit set of invisible paste characters (BOM, zero-width space, and the
related marks listed in _INVISIBLE_PASTE). Other characters are not stripped
and are not converted. If a header prefix remains, or the remainder is empty
or not safe in an HTTP header, the script exits 2 and does not call Ofox.

A passing record is one HTTP 200 chat completion with non-empty message
content. Codex CLI, Claude Code, and Cursor are not launched and are not
marked passed.
"""
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.ofox.ai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-5.4"

# Invisible characters commonly introduced by editors, browsers, and chat
# apps. These are not Unicode whitespace, so str.strip() leaves them in place.
# The set is explicit on purpose: this does not strip every format character,
# does not remove punctuation, and does not apply NFKC or any other casefold.
_INVISIBLE_PASTE = frozenset({
    "\ufeff",  # BOM / ZERO WIDTH NO-BREAK SPACE
    "\u200b",  # ZERO WIDTH SPACE
    "\u200c",  # ZERO WIDTH NON-JOINER
    "\u200d",  # ZERO WIDTH JOINER
    "\u2060",  # WORD JOINER
    "\u180e",  # MONGOLIAN VOWEL SEPARATOR (not whitespace in Python 3)
    "\u200e",  # LEFT-TO-RIGHT MARK
    "\u200f",  # RIGHT-TO-LEFT MARK
    "\u202a",  # LEFT-TO-RIGHT EMBEDDING
    "\u202b",  # RIGHT-TO-LEFT EMBEDDING
    "\u202c",  # POP DIRECTIONAL FORMATTING
    "\u202d",  # LEFT-TO-RIGHT OVERRIDE
    "\u202e",  # RIGHT-TO-LEFT OVERRIDE
    "\u2066",  # LEFT-TO-RIGHT ISOLATE
    "\u2067",  # RIGHT-TO-LEFT ISOLATE
    "\u2068",  # FIRST STRONG ISOLATE
    "\u2069",  # POP DIRECTIONAL ISOLATE
})

# Detect a pasted Authorization / x-api-key header before whitespace is
# deleted, so "Bearer <token>" is rejected instead of concatenated.
_HEADER_PREFIX = re.compile(
    r"""^[\s"']*(?:bearer\s+|authorization\s*:|x-api-key\s*:)""",
    re.IGNORECASE,
)

REASON_PREFIX = "prefix included; supply the raw key"
REASON_EMPTY = "empty after removing accidental paste characters"
REASON_HEADER = "not safe for an HTTP header"
REASON_MASK = "could not register the derived token for log masking"

CURSOR_CHECK = {
    "status": "provider_marked_incompatible",
    "passedAt": None,
    "detail": "Ofox documents direct Cursor integration as unsuitable. Tab completion, Agent mode, and Auto do not follow a custom provider.",
    "source": "https://ofox.ai/docs/integrations/cursor",
    "sourceUpdated": "2026-10-16",
}


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def status_path():
    override = os.environ.get("OFOX_SMOKE_STATUS_PATH")
    if override:
        return pathlib.Path(override)
    return ROOT / "ofox-smoke-status.json"


class SecretFormatError(Exception):
    """The environment value must not be sent. `reason` is a fixed code.

    The raw and normalized token are never stored on this exception.
    """

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def _for_prefix_scan(raw):
    # Treat invisible paste marks as separators for prefix detection only.
    # "Bearer<ZWSP>sk-..." is a pasted header, not a token that contains a mark.
    return "".join(" " if char in _INVISIBLE_PASTE else char for char in raw)


def normalize_ofox_api_key(raw):
    """Return a header-safe token, or raise SecretFormatError.

    Removes Unicode whitespace and `_INVISIBLE_PASTE` anywhere in the value.
    A value that is already header-safe is returned unchanged. Punctuation is
    kept. Characters outside ASCII 0x21-0x7E, including smart quotes, soft
    hyphens, and fullwidth letters, are not converted; they fail the call.
    """
    if not isinstance(raw, str):
        raise SecretFormatError(REASON_EMPTY)
    if _HEADER_PREFIX.match(_for_prefix_scan(raw)):
        raise SecretFormatError(REASON_PREFIX)
    token = "".join(
        char for char in raw
        if char not in _INVISIBLE_PASTE and not char.isspace()
    )
    if token == "":
        raise SecretFormatError(REASON_EMPTY)
    # RFC 9110 field-vchar, with whitespace already removed. This also rejects
    # CR, LF, and NUL, so the value cannot split an HTTP header.
    if any(ord(char) < 33 or ord(char) > 126 for char in token):
        raise SecretFormatError(REASON_HEADER)
    return token


def mask_derived_secret(token):
    """Register the normalized token with GitHub Actions log masking.

    Actions masks the stored secret, not a derived value. Whitespace removal
    produces a different string, so an accidental later log of that string
    would not match the original mask. Emit one `add-mask` workflow command
    and nothing else, and only when this process is an Actions step. Local
    runs and unit tests do not print the token.
    """
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    if any(ord(char) < 33 or ord(char) > 126 for char in token):
        raise SecretFormatError(REASON_HEADER)
    # Match @actions/core escapeData so the runner stores the original token.
    escaped = token.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    try:
        sys.stdout.write("::add-mask::" + escaped + "\n")
        sys.stdout.flush()
    except Exception:
        # stdout errors can quote the text they failed to write. Drop that
        # context and do not send the request.
        raise SecretFormatError(REASON_MASK) from None


def load_status():
    path = status_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema": 2, "checks": {}}


def write_status(status, secrets):
    payload = json.dumps(status, ensure_ascii=False, indent=2) + "\n"
    for secret in secrets:
        if secret and secret in payload:
            print("REFUSING: status payload contained the API key. File not written.")
            return 1
    status_path().write_text(payload, encoding="utf-8")
    return 0


def record(secrets, model, http_status, latency_ms, ok, detail):
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
    wrote = write_status(status, secrets)
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
    raw_key = os.environ.get("OFOX_API_KEY", "")
    if raw_key == "":
        print("BLOCKED_NO_OFOX_API_KEY: status file left unchanged (overall stays unverified).")
        return 0
    try:
        key = normalize_ofox_api_key(raw_key)
        # Mask before the header is built. Request() can raise ValueError whose
        # message includes the header value; that text must never be logged.
        mask_derived_secret(key)
    except SecretFormatError as exc:
        print("INVALID_SECRET_FORMAT: request not sent (" + exc.reason + "). Status file left unchanged.")
        return 2

    secrets = (raw_key, key)
    model = os.environ.get("OFOX_CHAT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        "max_tokens": 16,
    }
    started = time.perf_counter()
    try:
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
        with urllib.request.urlopen(request, timeout=45) as response:
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw = response.read(65536)
            http_status = response.status
        try:
            parsed = json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return record(secrets, model, http_status, latency_ms, False, "HTTP 200 body was not JSON. Response body was not stored.")
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
        return record(secrets, model, http_status, latency_ms, ok, detail)
    except urllib.error.HTTPError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        # Do not read or print the body: some gateways echo request headers.
        # exc.reason and the body are intentionally unused.
        return record(
            secrets,
            model,
            exc.code,
            latency_ms,
            False,
            "Chat Completions returned HTTP " + str(exc.code) + ". Response body was not stored.",
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        # type(exc).__name__ only. str(exc) can contain the header value.
        return record(
            secrets,
            model,
            None,
            latency_ms,
            False,
            "Network error before a response: " + type(exc).__name__ + ". Details were not stored.",
        )


if __name__ == "__main__":
    sys.exit(main())
