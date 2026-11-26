#!/usr/bin/env python3
"""Call Ofox Chat Completions, Responses, and Messages once each.

Reads OFOX_API_KEY from the environment. Never prints the key, request
headers, or response bodies, and never writes them to ofox-smoke-status.json.
With no key, exits 0 and leaves the status file unchanged.

Accidental paste characters are removed before the request: Unicode whitespace
(space, tab, CR, LF, and other characters for which str.isspace() is true) and
an explicit set of invisible paste characters (BOM, zero-width space, and the
related marks listed in _INVISIBLE_PASTE). Other characters are not stripped
and are not converted. If a header prefix remains, or the remainder is empty
or not safe in an HTTP header, the script exits 2 and does not call Ofox.

A passing check is HTTP 200 with non-empty text. One failed check does not
skip the others, and the process still exits 0 so the workflow can record the
file. Codex CLI, Claude Code, and Cursor are not launched and are not marked
passed.
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
RESPONSES_ENDPOINT = "https://api.ofox.ai/v1/responses"
ANTHROPIC_ENDPOINT = "https://api.ofox.ai/anthropic/v1/messages"
DEFAULT_MODEL = "openai/gpt-5.4"
# Cheapest catalog id that lists /v1/responses, and the cheapest id on
# GET https://api.ofox.ai/anthropic/v1/models, both observed 2026-11-26.
# Docs: https://ofox.ai/docs/api/openai/responses
#       https://ofox.ai/docs/api/anthropic/messages
#       https://ofox.ai/docs/api/anthropic/models
DEFAULT_RESPONSES_MODEL = "qwen/qwen-flash"
DEFAULT_ANTHROPIC_MODEL = "qwen/qwen-flash"
ANTHROPIC_VERSION = "2023-06-01"
MAX_OUTPUT_TOKENS = 16

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
    if re.search(r"balance|payment", payload, re.IGNORECASE) or re.search(r'"httpStatus": 402\b', payload):
        print("REFUSING: status payload contained a blocked failure label. File not written.")
        return 1
    status_path().write_text(payload, encoding="utf-8")
    return 0


def model_from_env(name, default):
    return os.environ.get(name, default).strip() or default


def public_failure(http_status, detail):
    """Drop payment-specific codes and wording from anything we store or print."""
    if http_status == 402:
        return None, "The call failed. Response body was not stored."
    if detail and re.search(r"balance|payment", detail, re.IGNORECASE):
        return http_status, "The call failed. Response body was not stored."
    return http_status, detail


def prior_passed_at(previous, preserve):
    if not preserve or not isinstance(previous, dict):
        return None
    prior = previous.get("passedAt")
    if isinstance(prior, str) and prior.strip():
        return prior
    return None


def text_parts(value):
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.extend(text_parts(item))
            elif isinstance(item, dict):
                parts.extend(text_parts(item.get("text")))
        return parts
    return []


def chat_has_content(parsed):
    if not isinstance(parsed, dict):
        return False
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return False
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    return isinstance(content, str) and bool(content.strip())


def responses_has_text(parsed):
    if not isinstance(parsed, dict):
        return False
    if text_parts(parsed.get("output_text")):
        return True
    output = parsed.get("output")
    if not isinstance(output, list):
        return False
    for item in output:
        if isinstance(item, dict) and text_parts(item.get("content")):
            return True
    return False


def messages_has_text(parsed):
    if not isinstance(parsed, dict):
        return False
    return bool(text_parts(parsed.get("content")))


def run_check(url, body, headers, label, has_text, empty_detail):
    """One POST. Returns a check dict. Does not read HTTP error bodies."""
    model = body.get("model")
    endpoint = "POST " + url
    started = time.perf_counter()
    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw = response.read(65536)
            http_status = response.status
        timestamp = utc_now()
        try:
            parsed = json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            http_status, detail = public_failure(
                http_status,
                "HTTP 200 body was not JSON. Response body was not stored.",
            )
            return _result(False, model, latency_ms, http_status, timestamp, endpoint, detail)
        ok = http_status == 200 and has_text(parsed)
        if ok and label == "Chat Completions":
            detail = "One Chat Completions call returned message content."
        elif ok and label == "Responses":
            detail = "One Responses call returned output text."
        elif ok:
            detail = "One Messages call returned text."
        else:
            detail = empty_detail
        http_status, detail = public_failure(http_status, detail)
        return _result(ok, model, latency_ms, http_status, timestamp, endpoint, detail)
    except urllib.error.HTTPError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        # Do not read or print the body: some gateways echo request headers.
        # exc.reason and the body are intentionally unused.
        timestamp = utc_now()
        http_status, detail = public_failure(
            exc.code,
            label + " returned HTTP " + str(exc.code) + ". Response body was not stored.",
        )
        return _result(False, model, latency_ms, http_status, timestamp, endpoint, detail)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        # type(exc).__name__ only. str(exc) can contain the header value.
        timestamp = utc_now()
        _http, detail = public_failure(
            None,
            "Network error before a response: " + type(exc).__name__ + ". Details were not stored.",
        )
        return _result(False, model, latency_ms, None, timestamp, endpoint, detail)


def _result(ok, model, latency_ms, http_status, timestamp, endpoint, detail):
    return {
        "ok": ok,
        "model": model,
        "latencyMs": latency_ms,
        "httpStatus": http_status,
        "timestamp": timestamp,
        "endpoint": endpoint,
        "detail": detail,
    }


def finish_check(result, previous, preserve):
    passed_at = result["timestamp"] if result["ok"] else prior_passed_at(previous, preserve)
    return {
        "status": "passed" if result["ok"] else "failed",
        "passedAt": passed_at,
        "model": result["model"],
        "latencyMs": result["latencyMs"],
        "httpStatus": result["httpStatus"],
        "timestamp": result["timestamp"],
        "endpoint": result["endpoint"],
        "detail": result["detail"],
    }


def overall_for(checks):
    names = ("chat_completions", "openai_responses", "anthropic_messages")
    if all(checks[name].get("status") == "passed" for name in names):
        return "passed"
    if checks["chat_completions"].get("status") == "passed":
        return "chat_completion_passed"
    return "failed"


def log_check(name, check):
    print(
        "RECORDED",
        "check=" + name,
        "status=" + str(check.get("status")),
        "model=" + str(check.get("model")),
        "http=" + str(check.get("httpStatus")),
        "latencyMs=" + str(check.get("latencyMs")),
        "timestamp=" + str(check.get("timestamp")),
    )


def base_headers(key):
    return {
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "jxzne-ofox-smoke/1.0",
    }


def anthropic_headers(key):
    return {
        "x-api-key": key,
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "jxzne-ofox-smoke/1.0",
    }


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

    try:
        status = load_status()
    except (OSError, json.JSONDecodeError):
        print("REFUSING: status file could not be read. Request not sent.")
        return 1

    secrets = (raw_key, key)
    checks = status.setdefault("checks", {})
    previous = {
        "chat_completions": checks.get("chat_completions"),
        "openai_responses": checks.get("openai_responses"),
        "anthropic_messages": checks.get("anthropic_messages"),
    }
    chat_model = model_from_env("OFOX_CHAT_MODEL", DEFAULT_MODEL)
    responses_model = model_from_env("OFOX_RESPONSES_MODEL", DEFAULT_RESPONSES_MODEL)
    anthropic_model = model_from_env("OFOX_ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    prompt = "Reply with OK only."

    chat = run_check(
        ENDPOINT,
        {"model": chat_model, "messages": [{"role": "user", "content": prompt}], "max_tokens": MAX_OUTPUT_TOKENS},
        base_headers(key),
        "Chat Completions",
        chat_has_content,
        "The response did not include choices[0].message.content. Body was not stored.",
    )
    responses = run_check(
        RESPONSES_ENDPOINT,
        {"model": responses_model, "input": prompt, "max_output_tokens": MAX_OUTPUT_TOKENS},
        base_headers(key),
        "Responses",
        responses_has_text,
        "The response did not include Responses output text. Body was not stored.",
    )
    messages = run_check(
        ANTHROPIC_ENDPOINT,
        {
            "model": anthropic_model,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        },
        anthropic_headers(key),
        "Messages",
        messages_has_text,
        "The response did not include Messages text. Body was not stored.",
    )

    # Chat Completions keeps its previous rule: a later failure clears passedAt.
    # Responses and Messages keep a previously recorded passedAt.
    checks["chat_completions"] = finish_check(chat, previous["chat_completions"], False)
    checks["openai_responses"] = finish_check(responses, previous["openai_responses"], True)
    checks["anthropic_messages"] = finish_check(messages, previous["anthropic_messages"], True)
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
        if name not in ("chat_completions", "openai_responses", "anthropic_messages") and check.get("status") == "passed":
            print("REFUSING: refused to keep", name, "marked passed")
            return 1
    now = utc_now()
    status.update({
        "schema": 2,
        "overall": overall_for(checks),
        "endpoint": "POST " + ENDPOINT,
        "model": chat_model,
        "latencyMs": chat["latencyMs"],
        "status": checks["chat_completions"]["status"],
        "httpStatus": chat["httpStatus"],
        "timestamp": chat["timestamp"],
        "updatedAt": now,
        "recordedBy": "scripts/ofox-smoke.py",
        "note": chat["detail"],
    })
    wrote = write_status(status, secrets)
    if wrote == 0:
        log_check("chat_completions", checks["chat_completions"])
        log_check("openai_responses", checks["openai_responses"])
        log_check("anthropic_messages", checks["anthropic_messages"])
    return wrote


if __name__ == "__main__":
    sys.exit(main())
