#!/usr/bin/env python3
"""Claude Code SessionStart -> mesmo contexto injetado por `.agents/hooks/session_bootstrap.py`."""

from __future__ import annotations

import json
import os
import sys

from _bridge import load_hook_module, project_root, read_payload


def build_message(payload: dict) -> str:
    boot = load_hook_module("session_bootstrap")
    root = project_root(payload)
    plugin_mode = bool(os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip())
    specs = boot.list_active_specs(root)
    candidates = boot.count_skill_candidates(root)
    inbox_pdfs = boot.count_inbox_pdfs(root)

    mode = "Plugin Global" if plugin_mode else "Workspace"
    spec_line = ", ".join(specs) if specs else "nenhuma SPEC ativa em specs/active/"
    kb_note = f" PDFs novos em knowledge/inbox/: {inbox_pdfs}." if inbox_pdfs else ""
    warmup_hint = (
        " Workspace ainda sem estrutura de dados? Use a skill `project-warmup` (init-workspace)."
        if plugin_mode and not (root / "specs").exists()
        else ""
    )
    return (
        f"[AnalyticsAgent Harness Ativo — Modo {mode} — Claude Code] "
        f"SPECs ativas: {spec_line}. "
        f"Candidatos pendentes para extração de SKILL: {candidates}.{kb_note}{warmup_hint} "
        "Lembrete P0: toda demanda operacional segue o ciclo "
        "SPEC -> Literatura (knowledge/ + web) -> Plano -> Revisão -> Crítica -> "
        "Auditoria (governance-auditor) "
        "-> Execução. Guardrails determinísticos e telemetria estão ativos."
    )


def main() -> int:
    try:
        msg = build_message(read_payload())
    except Exception as exc:
        msg = f"[AnalyticsAgent] Bootstrap do harness falhou: {exc}"
    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
