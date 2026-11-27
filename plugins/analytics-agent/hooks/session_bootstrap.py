#!/usr/bin/env python3
"""Antigravity SessionStart hook (Modo Dual: workspace template ou Plugin Global via PLUGIN_ROOT)."""

from __future__ import annotations

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


def list_active_specs(workspace_root: Path) -> list[str]:
    active_dir = workspace_root / "specs" / "active"
    if not active_dir.exists():
        return []
    summaries: list[str] = []
    for path in sorted(active_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        status_match = re.search(r"^status:\s*([A-Z_]+)", text, re.MULTILINE)
        status = status_match.group(1) if status_match else "UNKNOWN"
        summaries.append(f"{path.name} [status={status}]")
    return summaries


def count_skill_candidates(workspace_root: Path) -> int:
    reg_path = workspace_root / "ops" / "patterns" / "repetitive_tasks_registry.json"
    if not reg_path.exists():
        return 0
    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        return sum(
            1
            for item in data.get("patterns", [])
            if item.get("occurrences", 0) >= 2 and not item.get("extractedSkill")
        )
    except Exception:
        return 0


def count_inbox_pdfs(workspace_root: Path) -> int:
    inbox_dir = workspace_root / "knowledge" / "inbox"
    if not inbox_dir.exists():
        return 0
    return len(list(inbox_dir.glob("*.pdf")))


def main() -> None:
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    workspace_root = resolve_workspace_root(payload)
    plugin_root = resolve_plugin_root()

    mode = "Plugin Global" if plugin_root else "Workspace"
    specs = list_active_specs(workspace_root)
    candidates = count_skill_candidates(workspace_root)
    inbox_pdfs = count_inbox_pdfs(workspace_root)

    spec_line = ", ".join(specs) if specs else "nenhuma SPEC ativa em specs/active/"
    kb_note = f" PDFs novos em knowledge/inbox/: {inbox_pdfs}." if inbox_pdfs else ""
    warmup_hint = (
        " Workspace ainda sem estrutura de dados? Use a skill `project-warmup` (init-workspace)."
        if plugin_root and not (workspace_root / "specs").exists()
        else ""
    )
    msg = (
        f"[AnalyticsAgent Harness Ativo — Modo {mode}] "
        f"SPECs ativas: {spec_line}. "
        f"Candidatos pendentes para extração de SKILL: {candidates}.{kb_note}{warmup_hint} "
        "Lembrete P0: toda demanda operacional segue o ciclo "
        "SPEC -> Literatura (knowledge/ + web) -> Plano -> Revisão -> Crítica -> Auditoria (governance-auditor) -> Execução. "
        "Guardrails determinísticos e telemetria estão ativos."
    )

    output = {
        "injectSteps": [
            {
                "systemMessage": {
                    "systemMessage": msg,
                }
            }
        ]
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
