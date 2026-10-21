#!/usr/bin/env python3
"""Minimal authenticated API smoke tests. Never prints API credentials.
Run only with an explicit OFOX_API_KEY and expect billable requests."""
import json, os, sys, urllib.request, urllib.error
KEY=os.getenv("OFOX_API_KEY","")
if not KEY:
 print("BLOCKED_NO_OFOX_API_KEY: Set encrypted GitHub Actions secret OFOX_API_KEY.")
 sys.exit(2)
tests=[
 ("OpenAI Responses", "https://api.ofox.ai/v1/responses",
  {"model":os.getenv("OFOX_RESPONSES_MODEL","openai/gpt-5.6"),"input":"Reply with OK only.","max_output_tokens":32},
  {"Authorization":"Bearer "+KEY}),
 ("Anthropic Messages","https://api.ofox.ai/anthropic/v1/messages",
  {"model":os.getenv("OFOX_ANTHROPIC_MODEL","anthropic/claude-sonnet-4.6"),"messages":[{"role":"user","content":"Reply with OK only."}],"max_tokens":32},
  {"x-api-key":KEY,"anthropic-version":"2023-06-01"})
]
failure=False
for name,url,payload,headers in tests:
 try:
  request=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json",**headers},method="POST")
  with urllib.request.urlopen(request,timeout=20) as response:
   body=json.loads(response.read(32768))
   ok=response.status==200 and (bool(body.get("output")) if "Responses" in name else bool(body.get("content")))
   print(f"{name}: HTTP {response.status}; valid_response={ok}; model={payload['model']}")
   if not ok:failure=True
 except urllib.error.HTTPError as exc:
  data=exc.read(1024).decode("utf-8","replace")
  # Print only status, never echo server response which may contain sensitive metadata.
  print(f"{name}: HTTP {exc.code}; FAILED. Check model, account balance and protocol. Response omitted.")
  failure=True
 except Exception as exc:
  print(f"{name}: NETWORK_ERROR {type(exc).__name__}; FAILED (details omitted)")
  failure=True
print("Scope: API protocol smoke test only; not client-level Codex/Claude Code feature validation.")
sys.exit(1 if failure else 0)
