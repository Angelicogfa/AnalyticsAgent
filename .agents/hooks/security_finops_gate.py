#!/usr/bin/env python3
"""Antigravity PreToolUse hook (Modo Dual: workspace template ou Plugin Global via PLUGIN_ROOT).

Hardening P0:
  - Fail-closed (G1): política ausente/inválida ou erro de entrada/execução retorna `deny`.
  - Auto-proteção (G2): escrita em `.agents/**`, `.claude/**`, `.claude-plugin/**`,
    `plugins/analytics-agent/**` ou `ops/governance/**` exige `force_ask`, inclusive via shell.
  - MCP Allowlist & Fallback (G5): nega servidor fora de `allowedServers`; tool não classificada -> `force_ask`.
  - FinOps no MCP (I1): aplica `costWarningCommandPatterns` aos argumentos MCP.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

PROTECTED_PREFIXES = (
    ".agents/",
    ".claude/",
    ".claude-plugin/",
    "plugins/analytics-agent/",
    "ops/governance/",
)

SHELL_WRITE_RE = re.compile(
    r"(?i)(>>?|<<|\btee\b|\bsed\s+-i\b|\brm\b|\bdel\b|\bmv\b|\bcp\b|"
    r"\bmove-item\b|\bcopy-item\b|\bremove-item\b|\bset-content\b|\bout-file\b|\bunlink\b)"
)
PROTECTED_CMD_TARGET_RE = re.compile(
    r"(?i)(\.agents[/\\](hooks|rules|hooks\.json)|\.claude[/\\](hooks|settings\.json)|"
    r"\.claude-plugin[/\\]|plugins[/\\]analytics-agent[/\\]|ops[/\\]governance[/\\])"
)


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
    script_dir = Path(__file__).resolve().parent
    candidates.append(script_dir.parent / "ops" / "governance" / "policy.json")
    candidates.append(script_dir.parents[1] / "ops" / "governance" / "policy.json")

    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"policy.json inválido em {path}: {exc}") from exc
            required = {"security", "mcpGovernance", "finops"}
            if not isinstance(data, dict) or not required.issubset(data.keys()):
                raise RuntimeError(f"policy.json incompleto em {path}: requer {sorted(required)}.")
            return data

    raise RuntimeError("Nenhuma policy.json encontrada (fail-closed P0).")


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
        "timestampUtc": dt.datetime.now(dt.UTC).isoformat(),
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


def _is_protected_path(raw_path: str) -> bool:
    norm = raw_path.replace("\\", "/").lower()
    while norm.startswith("./"):
        norm = norm[2:]
    for prefix in PROTECTED_PREFIXES:
        if norm == prefix.rstrip("/") or norm.startswith(prefix) or f"/{prefix}" in f"/{norm}":
            return True
    return False


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

    if PROTECTED_CMD_TARGET_RE.search(cmd) and SHELL_WRITE_RE.search(cmd):
        return (
            "force_ask",
            "GOV-HARNESS-CMD-PROTECT",
            "Modificação via shell em regras, hooks ou política de governança exige aprovação humana.",
        )

    finops = policy.get("finops", {})
    for warn in finops.get("costWarningCommandPatterns", []):
        if re.search(warn["pattern"], cmd):
            return warn.get("decision", "force_ask"), warn["id"], warn["reason"]

    return "allow", "OK", "Comando aprovado pelo gate determinístico."


def evaluate_file_write(args: dict, policy: dict) -> tuple[str, str, str]:
    target_path = str(args.get("Path") or args.get("TargetFile") or args.get("file_path") or "")
    content = str(
        args.get("Content")
        or args.get("CodeContent")
        or args.get("content")
        or args.get("Replacement")
        or args.get("ReplacementContent")
        or args.get("new_string")
        or ""
    )

    if _is_protected_path(target_path):
        return (
            "force_ask",
            "GOV-HARNESS-PROTECT",
            f"Alteração em arquivo protegido do harness/governança ({target_path}) exige aprovação humana.",
        )

    security = policy.get("security", {})
    for secret in security.get("secretPatterns", []):
        if re.search(secret["pattern"], content):
            return (
                "deny",
                secret["id"],
                f"Escrita bloqueada: {secret['reason']} Use Azure Key Vault / AWS Secrets Manager ou sessão local.",
            )

    is_doc = target_path.replace("\\", "/").lower().endswith(".md")
    if not is_doc:
        for rule in security.get("blockedCodePatterns", []):
            if re.search(rule["pattern"], content):
                return "deny", rule["id"], rule["reason"]

    return "allow", "OK", "Escrita de arquivo aprovada pelo gate determinístico."


def _extract_mcp_server_and_tool(tool_name: str, args: dict) -> tuple[str, str]:
    server_name = str(args.get("ServerName") or args.get("server_name") or "").strip()
    effective_tool = str(args.get("ToolName") or args.get("tool_name") or tool_name).strip()
    if not server_name and tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) >= 2:
            server_name = parts[1]
        if len(parts) == 3 and not args.get("ToolName"):
            effective_tool = parts[2]
    return server_name, effective_tool


def evaluate_mcp_call(tool_name: str, args: dict, policy: dict) -> tuple[str, str, str]:
    mcp_gov = policy.get("mcpGovernance", {})
    server_name, effective_tool = _extract_mcp_server_and_tool(tool_name, args)
    serialized_args = json.dumps(args, ensure_ascii=False)

    allowed_servers = mcp_gov.get("allowedServers")
    if isinstance(allowed_servers, list) and server_name and server_name not in allowed_servers:
        return (
            "deny",
            "MCP-SERVER-NOT-ALLOWED",
            f"Servidor MCP '{server_name}' não está na lista permitida ({allowed_servers}).",
        )

    security = policy.get("security", {})
    for secret in security.get("secretPatterns", []):
        if re.search(secret["pattern"], serialized_args):
            return "deny", secret["id"], f"Chamada MCP bloqueada: {secret['reason']}"

    for rule in security.get("blockedCommandPatterns", []):
        if re.search(rule["pattern"], serialized_args):
            return rule.get("decision", "deny"), f"MCP-{rule['id']}", rule["reason"]

    finops = policy.get("finops", {})
    for warn in finops.get("costWarningCommandPatterns", []):
        if re.search(warn["pattern"], serialized_args):
            return warn.get("decision", "force_ask"), f"MCP-{warn['id']}", warn["reason"]

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
                f"Operação MCP mutável '{effective_tool}' ({server_name or 'mcp'}) exige confirmação humana.",
            )

    return (
        "force_ask",
        "MCP-UNCLASSIFIED-TOOL",
        f"Ferramenta MCP não classificada '{effective_tool}' ({server_name or 'mcp'}) exige confirmação.",
    )


def main() -> None:
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            raise RuntimeError("Entrada stdin vazia no hook PreToolUse (fail-closed P0).")

        payload = json.loads(raw)
        workspace_root = resolve_workspace_root(payload)
        policy = load_policy(workspace_root)

        tool_call = payload.get("toolCall") or {}
        tool_name = str(tool_call.get("name", ""))
        args = tool_call.get("args") or {}

        if tool_name == "run_command":
            cmd = str(args.get("CommandLine") or args.get("command") or "")
            decision, rule_id, reason = evaluate_command(cmd, policy)
        elif tool_name in {
            "write_file",
            "edit_file",
            "write_to_file",
            "replace_file_content",
            "multi_replace_file_content",
        }:
            decision, rule_id, reason = evaluate_file_write(args, policy)
        elif tool_name == "call_mcp_tool" or any(
            k in tool_name.lower() for k in ("fabric", "aws", "powerbi", "mcp")
        ):
            decision, rule_id, reason = evaluate_mcp_call(tool_name, args, policy)
        else:
            decision, rule_id, reason = "allow", "OK", "Ferramenta permitida."

        if decision != "allow":
            record_gate_event(workspace_root, payload, decision, rule_id, reason)

        output = {"decision": decision}
        if decision != "allow":
            output["reason"] = f"[{rule_id}] {reason}"
        sys.stdout.write(json.dumps(output, ensure_ascii=False))
    except Exception as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "decision": "deny",
                    "reason": f"[GATE-FAIL-CLOSED] Falha no gate de segurança; ação bloqueada: {exc}",
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
