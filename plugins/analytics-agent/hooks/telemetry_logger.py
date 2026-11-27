#!/usr/bin/env python3
"""Antigravity PostToolUse hook (Modo Dual: grava em ops/telemetry do workspace ou PLUGIN_DATA)."""

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


def summarize_args(tool_name: str, args: dict) -> dict:
    if tool_name == "run_command":
        cmd = str(args.get("CommandLine", ""))
        first_token = cmd.strip().split()[0] if cmd.strip() else ""
        return {
            "binary": first_token,
            "cmdLength": len(cmd),
            "bypassSandbox": bool(args.get("BypassSandbox", False)),
        }
    if tool_name in {"read_file", "write_file", "edit_file"}:
        return {"path": str(args.get("Path", ""))[:180]}
    if tool_name in {"invoke_subagent", "run_workflow"}:
        return {
            "role": args.get("Role") or args.get("Description") or "",
            "model": args.get("Model") or "",
            "typeName": args.get("TypeName") or "",
        }
    return {"argKeys": sorted(list(args.keys()))[:10]}


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        sys.stdout.write("{}")
        return

    try:
        payload = json.loads(raw)
        workspace_root = resolve_workspace_root(payload)
        events_path = resolve_telemetry_path(workspace_root)
        events_path.parent.mkdir(parents=True, exist_ok=True)

        tool_call = payload.get("toolCall") or {}
        tool_name = str(tool_call.get("name", "unknown"))
        args = tool_call.get("args") or {}
        error = payload.get("error", "")

        record = {
            "timestampUtc": dt.datetime.now(dt.UTC).isoformat(),
            "eventType": "POST_TOOL_USE",
            "conversationId": payload.get("conversationId", ""),
            "stepIdx": payload.get("stepIdx"),
            "modelName": payload.get("modelName", ""),
            "toolId": tool_call.get("id", ""),
            "toolName": tool_name,
            "status": "ERROR" if error else "OK",
            "error": str(error)[:240] if error else "",
            "summary": summarize_args(tool_name, args),
        }

        with events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:  # telemetria nunca bloqueia a ferramenta
        sys.stderr.write(f"[telemetry_logger] falha ao registrar evento: {exc}\n")

    sys.stdout.write("{}")


if __name__ == "__main__":
    main()
