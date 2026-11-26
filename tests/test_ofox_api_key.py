#!/usr/bin/env python3
"""Offline checks for OFOX_API_KEY paste normalization.

Fixtures are fake tokens. This file does not read a real secret, does not print
raw or normalized tokens, and blocks network access before any smoke call.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ofox-smoke.py"

spec = importlib.util.spec_from_file_location("ofox_smoke_script", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _contains_secret(haystack, secret):
    if not secret or not haystack:
        return False
    if secret in haystack:
        return True
    width = 8
    if len(secret) < width:
        return secret in haystack
    for index in range(len(secret) - width + 1):
        if secret[index:index + width] in haystack:
            return True
    return False


def _unescape_workflow_data(escaped):
    # Same order as the Actions runner: percent, then CR, then LF.
    return escaped.replace("%25", "%").replace("%0D", "\r").replace("%0A", "\n")


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    def read(self, _limit):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class OfoxApiKeyTests(unittest.TestCase):
    clean = "sk-test-fake-7f3a9c2e1b84d056"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.status_file = pathlib.Path(self.tmp.name) / "status.json"
        self.env = mock.patch.dict(
            os.environ,
            {
                "OFOX_SMOKE_STATUS_PATH": str(self.status_file),
                "OFOX_API_KEY": "",
                "OFOX_CHAT_MODEL": "",
                "OFOX_RESPONSES_MODEL": "",
                "OFOX_ANTHROPIC_MODEL": "",
                "GITHUB_ACTIONS": "",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.urlopen = mock.patch.object(
            mod.urllib.request,
            "urlopen",
            side_effect=AssertionError("unexpected network"),
        )
        self.urlopen_mock = self.urlopen.start()
        self.addCleanup(self.urlopen.stop)

    def assert_same(self, actual, expected, label):
        if actual != expected:
            raise AssertionError(label)

    def assert_absent(self, haystack, secret, label="secret material in output"):
        if isinstance(haystack, bytes):
            haystack = haystack.decode("utf-8", "replace")
        if _contains_secret(haystack, secret):
            raise AssertionError(label)

    def run_main(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = mod.main()
        except Exception as exc:
            raise AssertionError("main raised " + type(exc).__name__) from None
        return code, stdout.getvalue(), stderr.getvalue()

    def test_invisible_set_is_not_whitespace(self):
        for char in mod._INVISIBLE_PASTE:
            if char.isspace():
                raise AssertionError("U+%04X is whitespace" % ord(char))
            if ord(char) < 128:
                raise AssertionError("U+%04X is ASCII" % ord(char))

    def test_valid_key_is_unchanged(self):
        punctuation = "sk-test.fake_key~plus+slash/eq=!#$&'()*,;=?@[]^`{|}:"
        for label, key in (("plain", self.clean), ("punctuation", punctuation)):
            self.assert_same(mod.normalize_ofox_api_key(key), key, label)
            self.assert_same(mod.normalize_ofox_api_key(mod.normalize_ofox_api_key(key)), key, label + " idempotent")

    def test_quotes_and_inner_punctuation_are_not_stripped(self):
        quoted = '"' + self.clean + '"'
        self.assert_same(mod.normalize_ofox_api_key(quoted), quoted, "wrapping quotes kept")
        inner = self.clean[:8] + '"' + self.clean[8:]
        self.assert_same(mod.normalize_ofox_api_key(inner), inner, "inner quote kept")

    def test_whitespace_newlines_and_invisible_marks_normalize(self):
        internal_newline = self.clean[:8] + "\n" + self.clean[8:]
        internal_crlf = self.clean[:12] + "\r\n" + self.clean[12:]
        if internal_newline != internal_newline.strip() or internal_crlf != internal_crlf.strip():
            raise AssertionError("internal newline fixture was only outer whitespace")
        bom = "\ufeff" + self.clean
        if bom != bom.strip():
            raise AssertionError("BOM fixture was treated as outer whitespace")
        cases = {
            "leading space": "  " + self.clean,
            "trailing crlf": self.clean + "\r\n",
            "tabs": "\t" + self.clean + "\t",
            "vertical whitespace": "\v" + self.clean + "\f",
            "nbsp": "\u00a0" + self.clean + "\u00a0",
            "ideographic space": "\u3000" + self.clean,
            "line separator": self.clean[:5] + "\u2028" + self.clean[5:],
            "internal newline": internal_newline,
            "internal crlf": internal_crlf,
            "internal spaces": self.clean[:6] + "  " + self.clean[6:10] + "\t" + self.clean[10:],
            "bom": bom,
            "zwsp": self.clean[:7] + "\u200b" + self.clean[7:],
            "mixed paste": "\ufeff \t" + self.clean[:9] + "\u200b\r\n" + self.clean[9:] + " \u00a0",
        }
        for char in mod._INVISIBLE_PASTE:
            cases["U+%04X" % ord(char)] = char + self.clean[:4] + char + self.clean[4:] + char
        for label, raw in cases.items():
            self.assert_same(mod.normalize_ofox_api_key(raw), self.clean, label)
            self.assert_same(
                mod.normalize_ofox_api_key(mod.normalize_ofox_api_key(raw)),
                self.clean,
                label + " idempotent",
            )

    def test_empty_and_non_text_input_fails_closed(self):
        cases = {
            "empty": "",
            "spaces": " \t\r\n",
            "bom only": "\ufeff",
            "zwsp only": "\u200b\u200c\u200d",
            "mixed blank": " \ufeff\n\t\u200b",
            "nbsp only": "\u00a0",
        }
        for label, raw in cases.items():
            with self.assertRaises(mod.SecretFormatError) as caught:
                mod.normalize_ofox_api_key(raw)
            if caught.exception.reason != mod.REASON_EMPTY:
                raise AssertionError(label)
            if caught.exception.args != (mod.REASON_EMPTY,):
                raise AssertionError(label + " args")
        for label, raw in (("none", None), ("bytes", b"sk-test-fake")):
            with self.assertRaises(mod.SecretFormatError) as caught:
                mod.normalize_ofox_api_key(raw)
            if caught.exception.reason != mod.REASON_EMPTY:
                raise AssertionError(label)

    def test_remaining_malformed_characters_fail_without_conversion(self):
        cases = {
            "cjk": self.clean + "\u5bc6\u94a5",
            "smart quote": "\u201c" + self.clean + "\u201d",
            "soft hyphen": self.clean[:6] + "\u00ad" + self.clean[6:],
            "fullwidth": "\uff53" + self.clean,
            "variation selector": self.clean + "\ufe0f",
            "nul": self.clean[:4] + "\x00" + self.clean[4:],
            "del": self.clean + "\x7f",
            "bell": "\x07" + self.clean,
        }
        for label, raw in cases.items():
            with self.assertRaises(mod.SecretFormatError) as caught:
                mod.normalize_ofox_api_key(raw)
            if caught.exception.reason != mod.REASON_HEADER:
                raise AssertionError(label)
            text = str(caught.exception)
            self.assert_absent(text, self.clean, label)
            if raw in text:
                raise AssertionError(label + " raw in exception")

    def test_header_prefix_is_rejected_before_concatenation(self):
        cases = (
            "Bearer " + self.clean,
            "bearer\t" + self.clean,
            "  Authorization: Bearer " + self.clean,
            "x-api-key:" + self.clean,
            '"Bearer ' + self.clean + '"',
            "Bearer\u200b" + self.clean,
            "\nBearer " + self.clean,
            "Bearer \r\n" + self.clean,
        )
        for raw in cases:
            with self.assertRaises(mod.SecretFormatError) as caught:
                mod.normalize_ofox_api_key(raw)
            if caught.exception.reason != mod.REASON_PREFIX:
                raise AssertionError("prefix reason")
            self.assert_absent(str(caught.exception), self.clean)
        kept = (
            "bearer" + self.clean,
            "authorization" + self.clean,
            "x-api-key" + self.clean,
        )
        for key in kept:
            self.assert_same(mod.normalize_ofox_api_key(key), key, "prefix letters without separator stay")

    def test_main_empty_does_not_call_or_write(self):
        for value in ("", None):
            if value is None:
                os.environ.pop("OFOX_API_KEY", None)
            else:
                os.environ["OFOX_API_KEY"] = value
            code, out, err = self.run_main()
            if code != 0:
                raise AssertionError("empty exit")
            if "BLOCKED_NO_OFOX_API_KEY" not in out:
                raise AssertionError("empty message")
            if self.urlopen_mock.called:
                raise AssertionError("empty input called the network")
            if self.status_file.exists():
                raise AssertionError("empty input wrote status")
            if err:
                raise AssertionError("empty input wrote stderr")

    def test_main_invalid_does_not_call_or_leak(self):
        samples = {
            "blank": " \r\n\ufeff",
            "prefix": "Bearer " + self.clean,
            "zwsp prefix": "Bearer\u200b" + self.clean,
            "cjk": self.clean + "\u5bc6",
            "soft hyphen": self.clean + "\u00ad",
        }
        os.environ["GITHUB_ACTIONS"] = "true"
        for label, raw in samples.items():
            self.urlopen_mock.reset_mock()
            os.environ["OFOX_API_KEY"] = raw
            code, out, err = self.run_main()
            if code != 2:
                raise AssertionError(label + " exit")
            if self.urlopen_mock.called:
                raise AssertionError(label + " called the network")
            if self.status_file.exists():
                raise AssertionError(label + " wrote status")
            if "INVALID_SECRET_FORMAT" not in out:
                raise AssertionError(label + " message")
            if "::add-mask::" in out:
                raise AssertionError(label + " masked a rejected value")
            self.assert_absent(out, self.clean, label)
            self.assert_absent(err, self.clean, label)
            self.assert_absent(out, "Bearer" + self.clean, label)

    def _accept(self, body):
        self.requests = []
        bodies = {
            mod.ENDPOINT: body,
            mod.RESPONSES_ENDPOINT: b'{"output":[{"type":"message","content":[{"type":"output_text","text":"OK"}]}]}',
            mod.ANTHROPIC_ENDPOINT: b'{"content":[{"type":"text","text":"OK"}]}',
        }

        def _urlopen(request, timeout=None):
            self.requests.append((request, timeout))
            self.captured = request
            self.captured_timeout = timeout
            payload = bodies.get(request.full_url)
            if payload is None:
                raise AssertionError("unexpected url")
            return FakeResponse(200, payload)

        self.urlopen_mock.side_effect = _urlopen

    def assert_request_uses(self, token):
        matches = [item for item in self.requests if item[0].full_url == mod.ENDPOINT]
        if len(matches) != 1:
            raise AssertionError("chat request count")
        request, timeout = matches[0]
        auth = request.headers.get("Authorization")
        if auth != "Bearer " + token:
            raise AssertionError("Authorization header mismatch")
        if timeout != 45:
            raise AssertionError("timeout changed")
        self.assert_absent(request.data or b"", token)
        self.assert_absent(request.data or b"", self.clean)

    def test_main_sends_normalized_key_without_logging_it(self):
        raw = "\ufeff " + self.clean[:8] + "\r\n" + self.clean[8:] + " \u200b\t"
        os.environ["OFOX_API_KEY"] = raw
        os.environ["OFOX_CHAT_MODEL"] = "openai/gpt-5.4"
        self._accept(b'{"choices":[{"message":{"content":" OK "}}]}')
        code, out, err = self.run_main()
        if code != 0:
            raise AssertionError("success exit")
        if self.urlopen_mock.call_count != 3:
            raise AssertionError("urlopen call count")
        self.assert_request_uses(self.clean)
        if "::add-mask::" in out:
            raise AssertionError("masked outside GitHub Actions")
        self.assert_absent(out, self.clean)
        self.assert_absent(out, raw)
        self.assert_absent(err, self.clean)
        text = self.status_file.read_text(encoding="utf-8")
        self.assert_absent(text, self.clean)
        self.assert_absent(text, raw)
        status = json.loads(text)
        if status["status"] != "passed" or status["httpStatus"] != 200:
            raise AssertionError("status was not a passing chat completion")
        if "RECORDED" not in out or "model=openai/gpt-5.4" not in out:
            raise AssertionError("recorded line")

    def test_unchanged_key_uses_the_same_header(self):
        os.environ["OFOX_API_KEY"] = self.clean
        self._accept(b'{"choices":[{"message":{"content":"OK"}}]}')
        code, out, _err = self.run_main()
        if code != 0:
            raise AssertionError("unchanged exit")
        self.assert_request_uses(self.clean)
        self.assert_absent(out, self.clean)

    def test_actions_masks_derived_token_only(self):
        token = self.clean + "%ZZ"
        raw = "\ufeff" + token[:10] + "\n" + token[10:] + " "
        os.environ["OFOX_API_KEY"] = raw
        os.environ["GITHUB_ACTIONS"] = "true"
        self._accept(b'{"choices":[{"message":{"content":"OK"}}]}')
        code, out, err = self.run_main()
        if code != 0:
            raise AssertionError("mask exit")
        self.assert_request_uses(token)
        lines = out.splitlines()
        masks = [line for line in lines if line.startswith("::add-mask::")]
        if len(masks) != 1:
            raise AssertionError("add-mask count")
        payload = _unescape_workflow_data(masks[0][len("::add-mask::"):])
        self.assert_same(payload, token, "add-mask payload mismatch")
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != hashlib.sha256(token.encode("utf-8")).hexdigest():
            raise AssertionError("add-mask hash mismatch")
        other = "\n".join(line for line in lines if not line.startswith("::add-mask::"))
        self.assert_absent(other, token)
        self.assert_absent(other, raw)
        self.assert_absent(err, token)
        self.assert_absent(self.status_file.read_text(encoding="utf-8"), token)

    def test_header_and_body_errors_do_not_log_the_token(self):
        os.environ["OFOX_API_KEY"] = "\n" + self.clean + "\n"

        def raise_value_error(request, timeout=None):
            auth = request.headers.get("Authorization")
            raise ValueError("Invalid header value %r" % (auth,))

        self.urlopen_mock.side_effect = raise_value_error
        code, out, err = self.run_main()
        if code != 0:
            raise AssertionError("value error exit")
        if self.urlopen_mock.call_count != 3:
            raise AssertionError("value error did not attempt every check")
        text = self.status_file.read_text(encoding="utf-8")
        self.assert_absent(out, self.clean)
        self.assert_absent(err, self.clean)
        self.assert_absent(text, self.clean)
        if "ValueError" not in text or "Details were not stored." not in text:
            raise AssertionError("value error detail")
        if "Invalid header value" in text or "Invalid header value" in out:
            raise AssertionError("header value was stored")

        self.status_file.unlink()

        def raise_http_error(request, timeout=None):
            auth = request.headers.get("Authorization") or ""
            raise mod.urllib.error.HTTPError(
                mod.ENDPOINT,
                401,
                auth,
                None,
                io.BytesIO(b"echo " + auth.encode("utf-8")),
            )

        self.urlopen_mock.reset_mock()
        self.urlopen_mock.side_effect = raise_http_error
        code, out, err = self.run_main()
        if code != 0:
            raise AssertionError("http error exit")
        if self.urlopen_mock.call_count != 3:
            raise AssertionError("http error did not attempt every check")
        text = self.status_file.read_text(encoding="utf-8")
        self.assert_absent(out, self.clean)
        self.assert_absent(err, self.clean)
        self.assert_absent(text, self.clean)
        if "HTTP 401" not in text or "Response body was not stored." not in text:
            raise AssertionError("http error detail")

    def test_status_file_refuses_embedded_token(self):
        os.environ["OFOX_API_KEY"] = self.clean
        os.environ["OFOX_CHAT_MODEL"] = self.clean
        self._accept(b'{"choices":[{"message":{"content":"OK"}}]}')
        code, out, err = self.run_main()
        if code != 1:
            raise AssertionError("refuse exit")
        if self.status_file.exists():
            raise AssertionError("refused write still created a file")
        if "REFUSING: status payload contained the API key." not in out:
            raise AssertionError("refuse message")
        self.assert_absent(out, self.clean)
        self.assert_absent(err, self.clean)

    def test_mask_failure_does_not_include_the_token_or_send(self):
        os.environ["OFOX_API_KEY"] = "\n" + self.clean
        os.environ["GITHUB_ACTIONS"] = "true"

        class _Boom(io.StringIO):
            def write(self, text):
                if text.startswith("::add-mask::"):
                    raise OSError("stdout failed")
                return super().write(text)

        stdout = _Boom()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = mod.main()
            except Exception as exc:
                raise AssertionError("main raised " + type(exc).__name__) from None
        if code != 2:
            raise AssertionError("mask failure exit")
        if self.urlopen_mock.called:
            raise AssertionError("mask failure called the network")
        out = stdout.getvalue()
        err = stderr.getvalue()
        if mod.REASON_MASK not in out:
            raise AssertionError("mask failure message")
        self.assert_absent(out, self.clean)
        self.assert_absent(err, self.clean)
        if self.status_file.exists():
            raise AssertionError("mask failure wrote status")

    def test_workflow_script_and_triggers_stay_narrow(self):
        workflow = (ROOT / ".github/workflows/ofox-smoke.yml").read_text(encoding="utf-8")
        if "python3 scripts/ofox-smoke.py" not in workflow:
            raise AssertionError("smoke entrypoint missing")
        if "tests/ofox_smoke.py" in workflow or "workflow_call" in workflow:
            raise AssertionError("workflow broadened")
        if "workflow_dispatch:" not in workflow:
            raise AssertionError("workflow_dispatch missing")
        if "schedule:" in workflow or "cron:" in workflow:
            raise AssertionError("scheduled smoke run was reintroduced")

    def test_three_protocol_calls_record_a_pass_without_the_key(self):
        os.environ["OFOX_API_KEY"] = self.clean
        self._accept(b'{"choices":[{"message":{"content":" OK "}}]}')
        code, out, err = self.run_main()
        if code != 0:
            raise AssertionError("protocol exit")
        urls = [item[0].full_url for item in self.requests]
        self.assert_same(
            urls,
            [mod.ENDPOINT, mod.RESPONSES_ENDPOINT, mod.ANTHROPIC_ENDPOINT],
            "call order",
        )
        chat, responses, messages = [item[0] for item in self.requests]
        if chat.headers.get("Authorization") != "Bearer " + self.clean:
            raise AssertionError("chat auth")
        if responses.headers.get("Authorization") != "Bearer " + self.clean:
            raise AssertionError("responses auth")
        if responses.headers.get("X-api-key") not in (None, ""):
            raise AssertionError("responses sent x-api-key")
        if messages.headers.get("X-api-key") != self.clean:
            raise AssertionError("messages key header")
        if messages.headers.get("Anthropic-version") != mod.ANTHROPIC_VERSION:
            raise AssertionError("anthropic version")
        if messages.headers.get("Authorization"):
            raise AssertionError("messages sent Authorization")
        for request, _timeout in self.requests:
            self.assert_absent(request.data or b"", self.clean)
            self.assert_absent(request.full_url, self.clean)
            if _timeout != 45:
                raise AssertionError("timeout")
        self.assert_same(json.loads(chat.data.decode())["model"], "openai/gpt-5.4", "chat model")
        self.assert_same(json.loads(chat.data.decode())["max_tokens"], 16, "chat tokens")
        responses_body = json.loads(responses.data.decode())
        self.assert_same(responses_body["model"], "qwen/qwen-flash", "responses model")
        self.assert_same(responses_body["max_output_tokens"], 16, "responses tokens")
        self.assert_same(responses_body["input"], "Reply with OK only.", "responses input")
        messages_body = json.loads(messages.data.decode())
        self.assert_same(messages_body["model"], "qwen/qwen-flash", "messages model")
        self.assert_same(messages_body["max_tokens"], 16, "messages tokens")
        text = self.status_file.read_text(encoding="utf-8")
        self.assert_absent(text, self.clean)
        self.assert_absent(out, self.clean)
        self.assert_absent(err, self.clean)
        if "balance" in text.lower() or "payment" in text.lower() or '"httpStatus": 402' in text:
            raise AssertionError("blocked label stored")
        status = json.loads(text)
        if status["overall"] != "passed" or status["status"] != "passed" or status["httpStatus"] != 200:
            raise AssertionError("top level chat record")
        expected = (
            ("chat_completions", "openai/gpt-5.4", "POST " + mod.ENDPOINT, "One Chat Completions call returned message content."),
            ("openai_responses", "qwen/qwen-flash", "POST " + mod.RESPONSES_ENDPOINT, "One Responses call returned output text."),
            ("anthropic_messages", "qwen/qwen-flash", "POST " + mod.ANTHROPIC_ENDPOINT, "One Messages call returned text."),
        )
        for name, model, endpoint, detail in expected:
            check = status["checks"][name]
            if check["status"] != "passed" or check["httpStatus"] != 200 or check["model"] != model:
                raise AssertionError(name)
            if check["endpoint"] != endpoint or check["detail"] != detail:
                raise AssertionError(name + " endpoint or detail")
            if not isinstance(check["latencyMs"], int) or check["passedAt"] != check["timestamp"]:
                raise AssertionError(name + " timing")
        if status["checks"]["codex_cli"]["status"] != "unverified" or status["checks"]["codex_cli"].get("passedAt") is not None:
            raise AssertionError("codex")
        if status["checks"]["claude_code"]["status"] != "unverified":
            raise AssertionError("claude code")
        if status["checks"]["cursor_direct"] != mod.CURSOR_CHECK:
            raise AssertionError("cursor")

    def test_one_failed_check_still_runs_the_others(self):
        os.environ["OFOX_API_KEY"] = self.clean
        self.status_file.write_text(json.dumps({
            "schema": 2,
            "catalogChecked": "2026-11-12",
            "checks": {
                "chat_completions": {"status": "passed", "passedAt": "2026-01-01T00:00:00+00:00"},
                "openai_responses": {"status": "passed", "passedAt": "2026-02-02T00:00:00+00:00"},
                "anthropic_messages": {"status": "passed", "passedAt": "2026-03-03T00:00:00+00:00"},
            },
        }), encoding="utf-8")

        def _urlopen(request, timeout=None):
            self.requests.append((request, timeout))
            url = request.full_url
            if url == mod.RESPONSES_ENDPOINT:
                return FakeResponse(200, b'{"output":[]}')
            if url == mod.ANTHROPIC_ENDPOINT:
                raise mod.urllib.error.HTTPError(
                    url,
                    500,
                    "Server Error",
                    None,
                    io.BytesIO(b"echo " + self.clean.encode("utf-8")),
                )
            return FakeResponse(200, b'{"choices":[{"message":{"content":"OK"}}]}')

        self.requests = []
        self.urlopen_mock.side_effect = _urlopen
        code, out, err = self.run_main()
        if code != 0:
            raise AssertionError("partial exit")
        urls = [item[0].full_url for item in self.requests]
        self.assert_same(
            urls,
            [mod.ENDPOINT, mod.RESPONSES_ENDPOINT, mod.ANTHROPIC_ENDPOINT],
            "partial order",
        )
        text = self.status_file.read_text(encoding="utf-8")
        self.assert_absent(text, self.clean)
        self.assert_absent(out, self.clean)
        self.assert_absent(err, self.clean)
        status = json.loads(text)
        if status["overall"] != "chat_completion_passed" or status["status"] != "passed":
            raise AssertionError("chat overall")
        if status.get("catalogChecked") != "2026-11-12":
            raise AssertionError("catalog note dropped")
        chat = status["checks"]["chat_completions"]
        responses = status["checks"]["openai_responses"]
        messages = status["checks"]["anthropic_messages"]
        if chat["status"] != "passed" or chat["passedAt"] == "2026-01-01T00:00:00+00:00":
            raise AssertionError("chat pass was not refreshed")
        if responses["status"] != "failed" or responses["passedAt"] != "2026-02-02T00:00:00+00:00":
            raise AssertionError("responses pass was not preserved")
        if responses["httpStatus"] != 200:
            raise AssertionError("empty responses http")
        if messages["status"] != "failed" or messages["passedAt"] != "2026-03-03T00:00:00+00:00":
            raise AssertionError("messages pass was not preserved")
        if messages["httpStatus"] != 500 or "HTTP 500" not in messages["detail"]:
            raise AssertionError("messages http detail")
        if status["checks"]["codex_cli"]["status"] == "passed":
            raise AssertionError("codex passed")

    def test_payment_failure_is_generic_and_does_not_stop_the_run(self):
        os.environ["OFOX_API_KEY"] = self.clean

        def _urlopen(request, timeout=None):
            self.requests.append((request, timeout))
            url = request.full_url
            if url == mod.ENDPOINT:
                raise mod.urllib.error.HTTPError(
                    url,
                    402,
                    "Payment Required",
                    None,
                    io.BytesIO(b"insufficient balance; payment required " + self.clean.encode("utf-8")),
                )
            if url == mod.ANTHROPIC_ENDPOINT:
                return FakeResponse(200, b'{"content":[{"type":"text","text":"OK"}]}')
            return FakeResponse(200, b'{"output":[{"content":[{"text":"OK"}]}]}')

        self.requests = []
        self.urlopen_mock.side_effect = _urlopen
        code, out, err = self.run_main()
        if code != 0:
            raise AssertionError("payment exit")
        urls = [item[0].full_url for item in self.requests]
        if mod.RESPONSES_ENDPOINT not in urls or mod.ANTHROPIC_ENDPOINT not in urls:
            raise AssertionError("later checks were skipped")
        text = self.status_file.read_text(encoding="utf-8")
        blob = "\n".join((text, out, err))
        self.assert_absent(blob, self.clean)
        if "balance" in blob.lower() or "payment" in blob.lower():
            raise AssertionError("payment detail leaked")
        if '"httpStatus": 402' in text or "HTTP 402" in blob or "http=402" in blob:
            raise AssertionError("payment status leaked")
        status = json.loads(text)
        chat = status["checks"]["chat_completions"]
        if chat["status"] != "failed" or chat["httpStatus"] is not None or chat["passedAt"] is not None:
            raise AssertionError("chat payment record")
        if chat["detail"] != "The call failed. Response body was not stored.":
            raise AssertionError("chat payment detail")
        if status["httpStatus"] is not None or status["overall"] != "failed":
            raise AssertionError("top level payment record")
        if status["checks"]["openai_responses"]["status"] != "passed":
            raise AssertionError("responses did not pass")
        if status["checks"]["anthropic_messages"]["status"] != "passed":
            raise AssertionError("messages did not pass")

    def test_chat_failure_clears_its_own_passed_at(self):
        os.environ["OFOX_API_KEY"] = self.clean
        self.status_file.write_text(json.dumps({
            "checks": {
                "chat_completions": {"status": "passed", "passedAt": "2026-01-01T00:00:00+00:00"},
                "openai_responses": {"status": "unverified", "passedAt": None},
            },
        }), encoding="utf-8")

        def _urlopen(request, timeout=None):
            if request.full_url == mod.ENDPOINT:
                return FakeResponse(200, b'{"choices":[]}')
            if request.full_url == mod.ANTHROPIC_ENDPOINT:
                return FakeResponse(200, b'{"content":[{"type":"text","text":"OK"}]}')
            return FakeResponse(200, b'{"output_text":"OK"}')

        self.urlopen_mock.side_effect = _urlopen
        code, _out, _err = self.run_main()
        if code != 0:
            raise AssertionError("clear exit")
        status = json.loads(self.status_file.read_text(encoding="utf-8"))
        if status["checks"]["chat_completions"]["passedAt"] is not None:
            raise AssertionError("chat passedAt kept after failure")
        if status["checks"]["chat_completions"]["status"] != "failed":
            raise AssertionError("chat status")
        if status["checks"]["openai_responses"]["status"] != "passed":
            raise AssertionError("responses output_text")
        if status["checks"]["anthropic_messages"]["passedAt"] is None:
            raise AssertionError("messages passedAt")


class SubprocessSmokeTests(unittest.TestCase):
    clean = "sk-test-fake-7f3a9c2e1b84d056"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        site = pathlib.Path(self.tmp.name) / "sitecustomize.py"
        site.write_text(
            "import socket\n"
            "def _blocked(*_args, **_kwargs):\n"
            "    raise OSError('network blocked by offline test')\n"
            "socket.create_connection = _blocked\n"
            "socket.socket.connect = lambda self, *_args, **_kwargs: _blocked()\n",
            encoding="utf-8",
        )
        self.site_dir = str(pathlib.Path(self.tmp.name))

    def run_script(self, raw, actions=False):
        status = pathlib.Path(self.tmp.name) / "status.json"
        env = {
            "PATH": os.environ.get("PATH", ""),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": self.site_dir,
            "HOME": self.tmp.name,
            "OFOX_SMOKE_STATUS_PATH": str(status),
            "OFOX_API_KEY": raw,
        }
        if actions:
            env["GITHUB_ACTIONS"] = "true"
        command = [sys.executable, str(SCRIPT)]
        if any(_contains_secret(part, raw) or _contains_secret(part, self.clean) for part in command):
            raise AssertionError("token placed on the command line")
        proc = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc, status

    def assert_absent(self, haystack, secret, label="secret material in subprocess output"):
        if _contains_secret(haystack, secret):
            raise AssertionError(label)

    def test_subprocess_empty_and_invalid_do_not_leak(self):
        proc, status = self.run_script("")
        if proc.returncode != 0:
            raise AssertionError("empty subprocess exit")
        if "BLOCKED_NO_OFOX_API_KEY" not in proc.stdout:
            raise AssertionError("empty subprocess message")
        if proc.stderr:
            raise AssertionError("empty subprocess stderr")
        if status.exists():
            raise AssertionError("empty subprocess wrote status")

        raw = "Bearer\u200b" + self.clean + "\n"
        proc, status = self.run_script(raw)
        if proc.returncode != 2:
            raise AssertionError("invalid subprocess exit")
        if "INVALID_SECRET_FORMAT" not in proc.stdout:
            raise AssertionError("invalid subprocess message")
        if "Traceback" in proc.stderr or "network blocked" in proc.stdout or "network blocked" in proc.stderr:
            raise AssertionError("invalid subprocess attempted a request or traceback")
        self.assert_absent(proc.stdout, self.clean)
        self.assert_absent(proc.stderr, self.clean)
        self.assert_absent(proc.stdout, raw)
        if status.exists():
            raise AssertionError("invalid subprocess wrote status")

    def test_subprocess_normalized_key_is_blocked_from_the_network(self):
        raw = "\ufeff" + self.clean[:9] + " \r\n" + self.clean[9:]
        proc, status = self.run_script(raw, actions=True)
        if proc.returncode != 0:
            raise AssertionError("normalized subprocess exit")
        if "Traceback" in proc.stderr:
            raise AssertionError("normalized subprocess traceback")
        if "network blocked" in proc.stdout or "network blocked" in proc.stderr:
            raise AssertionError("exception text was logged")
        text = status.read_text(encoding="utf-8")
        if "Details were not stored." not in text:
            raise AssertionError("network failure was not recorded safely")
        self.assert_absent(text, self.clean)
        self.assert_absent(text, raw)
        lines = proc.stdout.splitlines()
        masks = [line for line in lines if line.startswith("::add-mask::")]
        if len(masks) != 1:
            raise AssertionError("subprocess add-mask count")
        payload = _unescape_workflow_data(masks[0][len("::add-mask::"):])
        if payload != self.clean:
            raise AssertionError("subprocess add-mask payload mismatch")
        other = "\n".join(line for line in lines if not line.startswith("::add-mask::"))
        self.assert_absent(other, self.clean)
        self.assert_absent(other, raw)
        self.assert_absent(proc.stderr, self.clean)
        # The blocked socket must be the reason no HTTP status was stored.
        parsed = json.loads(text)
        if parsed.get("httpStatus") is not None:
            raise AssertionError("offline subprocess stored an HTTP status")


if __name__ == "__main__":
    unittest.main()
