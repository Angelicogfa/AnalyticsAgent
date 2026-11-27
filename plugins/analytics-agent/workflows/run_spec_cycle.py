#!/usr/bin/env python3
"""Runtime Claude Code para o MESMO orquestrador do Antigravity.

Arquivo executado: `.agents/workflows/data_task_orchestrator.py` (ou `<plugin>/workflows/` em modo plugin).

Uso:
  python .claude/workflows/run_spec_cycle.py --spec specs/active/SPEC-001-exemplo-cross-cloud-churn.md
  python .claude/workflows/run_spec_cycle.py --spec <SPEC> --execute        # após aprovação humana
Variáveis:
  CLAUDE_BIN  caminho alternativo do executável `claude` (ex.: stub em testes)
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _resolve_asset(plugin_rel: str, repo_rel: str) -> Path:
    """Resolve arquivo tanto em modo plugin (`<plugin>/workflows/`) quanto no repositório."""
    in_plugin = HERE / plugin_rel
    if in_plugin.exists():
        return in_plugin
    repo_root = HERE.parents[1]
    return repo_root / repo_rel


ORCHESTRATOR = _resolve_asset("data_task_orchestrator.py", ".agents/workflows/data_task_orchestrator.py")
RUNTIME_CFG = _resolve_asset("claude_runtime.json", ".claude/workflows/claude_runtime.json")
MODEL_MAP = _resolve_asset("model_map.json", ".claude/model_map.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ClaudeRuntime:
    def __init__(self, workspace: Path, runtime_cfg: dict, model_map: dict) -> None:
        self.workspace = workspace
        self.cfg = runtime_cfg
        self.tier_map = model_map["tier"]
        bin_env = os.environ.get(runtime_cfg.get("claudeBinEnv", "CLAUDE_BIN"), "").strip()
        self.claude_cmd = self._resolve_cmd(bin_env)

    @staticmethod
    def _resolve_cmd(bin_env: str) -> list[str]:
        if bin_env:
            return [sys.executable, bin_env] if bin_env.endswith(".py") else [bin_env]
        found = shutil.which("claude")
        if not found:
            raise RuntimeError("Executável `claude` não encontrado no PATH (defina CLAUDE_BIN).")
        return [found]

    def _phase_cfg(self, role: str) -> dict:
        planning = self.cfg["phases"]["planning"]
        if any(role.startswith(r) for r in planning["roles"]):
            return planning
        return self.cfg["phases"]["execution"]

    def phase(self, name: str) -> None:
        print(f"\n=== {name} ===", file=sys.stderr, flush=True)

    def log(self, msg: str) -> None:
        print(f"[log] {msg}", file=sys.stderr, flush=True)

    async def agent(self, prompt: str, schema: dict, role: str = "", model: str = "flash") -> dict:
        phase_cfg = self._phase_cfg(role)
        cmd = [
            *self.claude_cmd,
            "-p",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(schema, ensure_ascii=False),
            "--model",
            self.tier_map.get(model, model),
            "--allowedTools",
            phase_cfg["allowedTools"],
            "--permission-mode",
            phase_cfg["permissionMode"],
            "--max-turns",
            str(self.cfg.get("maxTurns", 40)),
        ]
        self.log(f"agent role='{role}' model={model}->{self.tier_map.get(model, model)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.workspace),
        )
        out, err = await proc.communicate(prompt.encode("utf-8"))
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude -p falhou para '{role}' (exit {proc.returncode}): {err.decode()[:500]}"
            )
        data = json.loads(out.decode("utf-8"))
        structured = data.get("structured_output")
        if structured is None:
            raise RuntimeError(
                f"Sem structured_output válido para '{role}': {str(data.get('result', ''))[:500]}"
            )
        return structured

    async def pipeline(self, items: list, fn) -> list:
        return [await fn(item) for item in items]


async def run(spec: str, execute: bool, max_cycles: int, workspace: Path) -> None:
    runtime = ClaudeRuntime(workspace, load_json(RUNTIME_CFG), load_json(MODEL_MAP))
    namespace = {
        "__name__": "__orchestrator__",
        "args": {"spec_path": spec, "execute": execute, "max_plan_cycles": max_cycles},
        "WORKSPACES": [str(workspace)],
        "phase": runtime.phase,
        "log": runtime.log,
        "agent": runtime.agent,
        "pipeline": runtime.pipeline,
    }
    code = compile(
        ORCHESTRATOR.read_text(encoding="utf-8"),
        str(ORCHESTRATOR),
        "exec",
        flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
    )
    result = eval(code, namespace)  # noqa: S307 - executa o orquestrador versionado do próprio repositório
    if asyncio.iscoroutine(result):
        await result


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o ciclo governado da SPEC no Claude Code.")
    parser.add_argument("--spec", required=True, help="Caminho da SPEC (ex.: specs/active/SPEC-001-*.md)")
    parser.add_argument("--execute", action="store_true", help="Executa as tarefas após aprovação (HITL).")
    parser.add_argument("--max-plan-cycles", type=int, default=3, choices=[1, 2, 3])
    parser.add_argument("--workspace", default="", help="Raiz do workspace (padrão: diretório atual)")
    ns = parser.parse_args()
    ws = Path(ns.workspace).resolve() if ns.workspace else Path.cwd()
    asyncio.run(run(ns.spec, ns.execute, ns.max_plan_cycles, ws))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
