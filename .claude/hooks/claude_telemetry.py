#!/usr/bin/env python3
"""Claude Code PostToolUse -> evento de `.agents/hooks/telemetry_logger.py` (+ campo `harness`)."""

from __future__ import annotations

import datetime as dt
import json
import sys

from _bridge import HARNESS, load_hook_module, project_root, read_payload
from claude_gate import translate


def main() -> int:
    try:
        payload = read_payload()
        logger = load_hook_module("telemetry_logger")
        root = project_root(payload)
        events_path = logger.resolve_telemetry_path(root)
        events_path.parent.mkdir(parents=True, exist_ok=True)

        ag_tool, args = translate(str(payload.get("tool_name", "")), payload.get("tool_input") or {})
        response = payload.get("tool_response")
        error = response if isinstance(response, str) and response.lower().startswith("error") else ""
        record = {
            "timestampUtc": dt.datetime.now(dt.UTC).isoformat(),
            "eventType": "POST_TOOL_USE",
            "conversationId": payload.get("session_id", ""),
            "stepIdx": None,
            "modelName": payload.get("model", ""),
            "toolId": payload.get("tool_use_id", ""),
            "toolName": ag_tool,
            "status": "ERROR" if error else "OK",
            "error": str(error)[:240] if error else "",
            "summary": logger.summarize_args(ag_tool, args),
            "harness": HARNESS,
            "claudeToolName": payload.get("tool_name", ""),
        }
        with events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:  # telemetria nunca bloqueia (mesmo comportamento do Antigravity)
        sys.stderr.write(f"[TELEMETRY-WARN] {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
