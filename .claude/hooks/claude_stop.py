#!/usr/bin/env python3
"""Claude Code Stop -> evento TURN_STOP de `.agents/hooks/stop_gate.py` (+ campo `harness`)."""

from __future__ import annotations

import datetime as dt
import json
import sys

from _bridge import HARNESS, load_hook_module, project_root, read_payload


def main() -> int:
    try:
        payload = read_payload()
        stop_gate = load_hook_module("stop_gate")
        root = project_root(payload)
        events_path = stop_gate.resolve_telemetry_path(root)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestampUtc": dt.datetime.now(dt.UTC).isoformat(),
            "eventType": "TURN_STOP",
            "conversationId": payload.get("session_id", ""),
            "modelName": payload.get("model", ""),
            "executionNum": None,
            "terminationReason": "stop_hook_active" if payload.get("stop_hook_active") else "end_turn",
            "error": "",
            "harness": HARNESS,
        }
        with events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        sys.stderr.write(f"[TELEMETRY-WARN] {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
