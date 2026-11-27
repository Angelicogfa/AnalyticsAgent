"""Ponte Claude Code -> hooks do Antigravity (`.agents/hooks/`).

Carrega os módulos originais via importlib para que a lógica de decisão, telemetria e bootstrap
continue em um único lugar. Nenhum arquivo de `.agents/` é modificado.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

HARNESS = "claude-code"


def project_root(payload: dict | None = None) -> Path:
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if env_dir:
        return Path(env_dir)
    if payload and payload.get("cwd"):
        return Path(str(payload["cwd"]))
    return Path(__file__).resolve().parents[2]


def bridge_plugin_env() -> None:
    """No modo plugin do Claude Code, expõe as variáveis no nome que os hooks originais já entendem."""
    claude_data = os.environ.get("CLAUDE_PLUGIN_DATA", "").strip()
    if claude_data and not os.environ.get("PLUGIN_DATA"):
        os.environ["PLUGIN_DATA"] = claude_data
    claude_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if claude_root and not os.environ.get("PLUGIN_ROOT"):
        os.environ["PLUGIN_ROOT"] = claude_root


def hooks_source_dir() -> Path:
    """Diretório com os hooks originais: `.agents/hooks` (modo projeto) ou `<plugin>/hooks` (modo plugin)."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parents[1] / ".agents" / "hooks",  # <repo>/.claude/hooks -> <repo>/.agents/hooks
        here.parent / "hooks",  # <plugin>/claude_hooks -> <plugin>/hooks
    ]
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if plugin_root:
        candidates.insert(0, Path(plugin_root) / "hooks")
    for c in candidates:
        if (c / "security_finops_gate.py").exists():
            return c
    raise FileNotFoundError("Hooks originais do harness (.agents/hooks) não encontrados.")


def load_hook_module(name: str) -> ModuleType:
    bridge_plugin_env()
    path = hooks_source_dir() / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"ag_{name}", path)
    if not spec or not spec.loader:
        raise ImportError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_payload() -> dict:
    raw = sys.stdin.read().strip()
    return json.loads(raw) if raw else {}


def to_antigravity_payload(payload: dict, tool_name: str, args: dict, root: Path) -> dict:
    """Converte o payload do Claude Code para o contrato esperado pelas funções do Antigravity."""
    return {
        "conversationId": payload.get("session_id", ""),
        "workspacePaths": [str(root)],
        "modelName": payload.get("model", ""),
        "stepIdx": None,
        "toolCall": {"id": payload.get("tool_use_id", ""), "name": tool_name, "args": args},
    }
