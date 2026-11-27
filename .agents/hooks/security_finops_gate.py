#!/usr/bin/env python3
"""Antigravity PreToolUse hook (Modo Dual: workspace template ou Plugin Global via PLUGIN_ROOT/PLUGIN_DATA).

Ordem de precedência da política:
  1. <workspace>/ops/governance/policy.json (override local do projeto)
  2. <PLUGIN_ROOT>/ops/governance/policy.json (fallback empacotado no plugin global)
  3. <script_root>/ops/governance/policy.json (fallback relativo)
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path


def resolve_workspace_root(payload: dict) -> Path:
    workspace_paths = payload.get("workspacePaths") or []
    if workspace_paths:
        return Path(workspace_paths[0])
    return Path(__file__).resolve().parents[2]


def resolve_plugin_root() -> Path | None:
    raw = os.environ.get("PLUGIN_ROOT", "").strip()
    return Path(raw) if raw else None


def resolve_telemetry_path(workspace_root: Path) -> Path:
    ws_tel_dir = workspace_root / "ops" / "telemetry"
    if ws_tel_dir.exists():
        return ws_tel_dir / "events.jsonl"
    plugin_data = os.environ.get("PLUGIN_DATA", "").strip()
    if plugin_data:
        return Path(plugin_data) / "telemetry" / "events.jsonl"
    plugin_root = resolve_plugin_root()
    if plugin_root:
        return plugin_root / "ops" / "telemetry" / "events.jsonl"
    return ws_tel_dir / "events.jsonl"


def load_policy(workspace_root: Path) -> dict:
    candidates = [workspace_root / "ops" / "governance" / "policy.json"]
    plugin_root = resolve_plugin_root()
    if plugin_root:
        candidates.append(plugin_root / "ops" / "governance" / "policy.json")
    # Fallback relativo ao próprio script (funciona tanto em .agents/hooks/ quanto em <plugin>/hooks/)
    script_dir = Path(__file__).resolve().parent
    candidates.append(script_dir.parent / "ops" / "governance" / "policy.json")
    candidates.append(script_dir.parents[1] / "ops" / "governance" / "policy.json")

    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


def record_gate_event(
    workspace_root: Path,
    payload: dict,
    decision: str,
    rule_id: str,
    reason: str,
) -> None:
    events_path = resolve_telemetry_path(workspace_root)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    tool_call = payload.get("toolCall") or {}
    event = {
        "timestampUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "eventType": "PRE_TOOL_GATE",
        "conversationId": payload.get("conversationId", ""),
        "stepIdx": payload.get("stepIdx"),
        "modelName": payload.get("modelName", ""),
        "toolName": tool_call.get("name", ""),
        "decision": decision,
        "ruleId": rule_id,
        "reason": reason,
    }
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def evaluate_command(cmd: str, policy: dict) -> tuple[str, str, str]:
    security = policy.get("security", {})
    for rule in security.get("blockedCommandPatterns", []):
        if re.search(rule["pattern"], cmd):
            return rule.get("decision", "deny"), rule["id"], rule["reason"]

    for secret in security.get("secretPatterns", []):
        if re.search(secret["pattern"], cmd):
            return (
                "deny",
                secret["id"],
                f"Bloqueado por vazamento potencial de segredo: {secret['reason']}",
            )

    finops = policy.get("finops", {})
    for warn in finops.get("costWarningCommandPatterns", []):
        if re.search(warn["pattern"], cmd):
            return warn.get("decision", "force_ask"), warn["id"], warn["reason"]

    return "allow", "OK", "Comando aprovado pelo gate determinístico."


def evaluate_file_write(args: dict, policy: dict) -> tuple[str, str, str]:
    target_path = str(args.get("Path", ""))
    content = str(args.get("Content", "") or args.get("Replacement", ""))

    normalized = target_path.replace("\\", "/").lower()
    if normalized.endswith("ops/governance/policy.json"):
        return (
            "force_ask",
            "GOV-POLICY-EDIT",
            "Alteração em ops/governance/policy.json exige aprovação humana explícita.",
        )

    security = policy.get("security", {})
    for secret in security.get("secretPatterns", []):
        if re.search(secret["pattern"], content):
            return (
                "deny",
                secret["id"],
                f"Escrita bloqueada: {secret['reason']} Use Azure Key Vault / AWS Secrets Manager ou sessão local (az/aws login).",
            )

    is_doc = normalized.endswith(".md")
    if not is_doc:
        for rule in security.get("blockedCodePatterns", []):
            if re.search(rule["pattern"], content):
                return "deny", rule["id"], rule["reason"]

    return "allow", "OK", "Escrita de arquivo aprovada pelo gate determinístico."


def evaluate_mcp_call(tool_name: str, args: dict, policy: dict) -> tuple[str, str, str]:
    mcp_gov = policy.get("mcpGovernance", {})
    effective_tool = str(args.get("ToolName", "") or tool_name)
    server_name = str(args.get("ServerName", ""))
    serialized_args = json.dumps(args, ensure_ascii=False)

    security = policy.get("security", {})
    for secret in security.get("secretPatterns", []):
        if re.search(secret["pattern"], serialized_args):
            return "deny", secret["id"], f"Chamada MCP bloqueada: {secret['reason']}"

    for rule in security.get("blockedCommandPatterns", []):
        if re.search(rule["pattern"], serialized_args):
            return rule.get("decision", "deny"), f"MCP-{rule['id']}", rule["reason"]

    for pat in mcp_gov.get("destructiveToolPatterns", []):
        if re.search(pat, effective_tool):
            return (
                "deny",
                "MCP-DESTRUCTIVE-BLOCKED",
                f"Operação MCP destrutiva '{effective_tool}' ({server_name or 'mcp'}) bloqueada pela política P0.",
            )

    for pat in mcp_gov.get("safeReadOnlyPatterns", []):
        if re.search(pat, effective_tool):
            return "allow", "MCP-READONLY-OK", "Operação MCP somente leitura/metadados permitida."

    for pat in mcp_gov.get("mutatingToolPatterns", []):
        if re.search(pat, effective_tool):
            return (
                "force_ask",
                "MCP-MUTATION-CONFIRM",
                f"Operação MCP mutável '{effective_tool}' ({server_name or 'mcp'}) exige SPEC APPROVED e confirmação humana explícita.",
            )

    return "allow", "OK", "Chamada MCP aprovada."


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        sys.stdout.write(json.dumps({"decision": "allow"}))
        return

    payload = json.loads(raw)
    workspace_root = resolve_workspace_root(payload)
    policy = load_policy(workspace_root)

    tool_call = payload.get("toolCall") or {}
    tool_name = str(tool_call.get("name", ""))
    args = tool_call.get("args") or {}

    if tool_name == "run_command":
        cmd = str(args.get("CommandLine", ""))
        decision, rule_id, reason = evaluate_command(cmd, policy)
    elif tool_name in {"write_file", "edit_file"}:
        decision, rule_id, reason = evaluate_file_write(args, policy)
    elif tool_name == "call_mcp_tool" or any(k in tool_name.lower() for k in ("fabric", "aws", "powerbi", "mcp")):
        decision, rule_id, reason = evaluate_mcp_call(tool_name, args, policy)
    else:
        decision, rule_id, reason = "allow", "OK", "Ferramenta permitida."

    if decision != "allow":
        record_gate_event(workspace_root, payload, decision, rule_id, reason)

    output = {"decision": decision}
    if decision != "allow":
        output["reason"] = f"[{rule_id}] {reason}"

    sys.stdout.write(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
