#!/usr/bin/env python3
"""Claude Code PreToolUse -> `.agents/hooks/security_finops_gate.py` (mesmas regras, mesma política).

Traduz `tool_name`/`tool_input` do Claude Code para as funções `evaluate_*` do gate do Antigravity e devolve
`hookSpecificOutput.permissionDecision`. Qualquer falha interna bloqueia a ação (exit 2): fail-closed.
"""

from __future__ import annotations

import json
import sys

from _bridge import load_hook_module, project_root, read_payload, to_antigravity_payload

DECISION_MAP = {"allow": "allow", "deny": "deny", "force_ask": "ask"}


def translate(tool_name: str, tool_input: dict) -> tuple[str, dict]:
    """Retorna (nome da ferramenta no contrato Antigravity, args no contrato Antigravity)."""
    if tool_name in {"Bash", "PowerShell"}:
        return "run_command", {"CommandLine": str(tool_input.get("command", ""))}
    if tool_name == "Write":
        return "write_file", {
            "Path": tool_input.get("file_path", ""),
            "Content": tool_input.get("content", ""),
        }
    if tool_name == "Edit":
        return "edit_file", {
            "Path": tool_input.get("file_path", ""),
            "Replacement": tool_input.get("new_string", ""),
        }
    if tool_name == "NotebookEdit":
        # Campos de NotebookEdit não documentados: avalia o payload completo como conteúdo.
        path = tool_input.get("notebook_path") or tool_input.get("file_path") or ""
        return "edit_file", {"Path": path, "Replacement": json.dumps(tool_input, ensure_ascii=False)}
    if tool_name.startswith("mcp__"):
        _, server, tool = (tool_name.split("__", 2) + ["", ""])[:3]
        return "call_mcp_tool", {"ServerName": server, "ToolName": tool, **tool_input}
    return tool_name, tool_input


def decide(payload: dict) -> tuple[str, str, str, str, dict]:
    gate = load_hook_module("security_finops_gate")
    root = project_root(payload)
    policy = gate.load_policy(root)
    ag_tool, args = translate(str(payload.get("tool_name", "")), payload.get("tool_input") or {})

    if ag_tool == "run_command":
        decision, rule_id, reason = gate.evaluate_command(args["CommandLine"], policy)
    elif ag_tool in {"write_file", "edit_file"}:
        decision, rule_id, reason = gate.evaluate_file_write(args, policy)
    elif ag_tool == "call_mcp_tool":
        decision, rule_id, reason = gate.evaluate_mcp_call(ag_tool, args, policy)
    else:
        decision, rule_id, reason = "allow", "OK", "Ferramenta permitida."

    if decision != "allow":
        gate.record_gate_event(
            root, to_antigravity_payload(payload, ag_tool, args, root), decision, rule_id, reason
        )
    return decision, rule_id, reason, ag_tool, args


def main() -> int:
    try:
        payload = read_payload()
        decision, rule_id, reason, _, _ = decide(payload)
    except Exception as exc:  # fail-closed
        sys.stderr.write(f"[GATE-ERROR] Gate de segurança falhou; ação bloqueada: {exc}\n")
        return 2

    claude_decision = DECISION_MAP.get(decision, "deny")
    output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": claude_decision}}
    if claude_decision != "allow":
        output["hookSpecificOutput"]["permissionDecisionReason"] = f"[{rule_id}] {reason}"
    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
