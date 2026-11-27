#!/usr/bin/env python3
"""Antigravity Stop hook (Modo Dual: grava em ops/telemetry do workspace ou PLUGIN_DATA)."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path


def resolve_workspace_root(payload: dict) -> Path:
    workspace_paths = payload.get("workspacePaths") or []
    if workspace_paths:
        return Path(workspace_paths[0])
    return Path(__file__).resolve().parents[2]


def resolve_telemetry_path(workspace_root: Path) -> Path:
    ws_tel_dir = workspace_root / "ops" / "telemetry"
    if ws_tel_dir.exists():
        return ws_tel_dir / "events.jsonl"
    plugin_data = os.environ.get("PLUGIN_DATA", "").strip()
    if plugin_data:
        return Path(plugin_data) / "telemetry" / "events.jsonl"
    plugin_root = os.environ.get("PLUGIN_ROOT", "").strip()
    if plugin_root:
        return Path(plugin_root) / "ops" / "telemetry" / "events.jsonl"
    return ws_tel_dir / "events.jsonl"


def main() -> None:
    raw = sys.stdin.read().strip()
    if raw:
        try:
            payload = json.loads(raw)
            workspace_root = resolve_workspace_root(payload)
            events_path = resolve_telemetry_path(workspace_root)
            events_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "timestampUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "eventType": "TURN_STOP",
                "conversationId": payload.get("conversationId", ""),
                "modelName": payload.get("modelName", ""),
                "executionNum": payload.get("executionNum"),
                "terminationReason": payload.get("terminationReason", ""),
                "error": str(payload.get("error", ""))[:240],
            }
            with events_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    sys.stdout.write("{}")


if __name__ == "__main__":
    main()
