#!/usr/bin/env python3
"""Gera o esqueleto padronizado de uma nova Antigravity SKILL e atualiza o registro de padrões."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def resolve_workspace(workspace_arg: str = "") -> Path:
    if workspace_arg:
        return Path(workspace_arg).expanduser().resolve()
    for env_key in ("ANALYTICS_AGENT_WORKSPACE", "CLAUDE_PROJECT_DIR"):
        raw = os.environ.get(env_key, "").strip()
        if raw:
            return Path(raw).expanduser().resolve()
    cwd = Path.cwd()
    if any((cwd / marker).exists() for marker in (".agents", "ops", "specs", ".git")):
        return cwd
    return Path(__file__).resolve().parents[4]


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold padronizado de nova Antigravity SKILL.")
    parser.add_argument("--name", required=True, help="Nome da skill em kebab-case (<=64 chars)")
    parser.add_argument("--description", required=True, help="Descrição em terceira pessoa de quando usar")
    parser.add_argument("--with-script", action="store_true", help="Inclui template de script CLI em scripts/")
    parser.add_argument("--pattern-id", default="", help="Opcional: ID do padrão em repetitive_tasks_registry.json")
    parser.add_argument("--workspace", default="", help="Raiz do workspace alvo")
    args = parser.parse_args()

    name = args.name.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", name):
        print("Erro: --name deve estar em kebab-case (a-z, 0-9, hífens, 2-63 chars).", file=sys.stderr)
        return 1

    root = resolve_workspace(args.workspace)
    skill_dir = root / ".agents" / "skills" / name
    if skill_dir.exists():
        print(f"Erro: skill '{name}' já existe em {skill_dir}", file=sys.stderr)
        return 1

    skill_dir.mkdir(parents=True)
    (skill_dir / "references").mkdir()

    script_section = ""
    if args.with_script:
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script_path = scripts_dir / f"{name.replace('-', '_')}.py"
        script_path.write_text(
            '#!/usr/bin/env python3\n'
            f'"""CLI determinística da skill {name}."""\n\n'
            'import argparse\n'
            'import json\n'
            'from pathlib import Path\n\n\n'
            'def main() -> int:\n'
            f'    parser = argparse.ArgumentParser(description="CLI da skill {name}")\n'
            '    parser.add_argument("--output", required=True, help="Arquivo JSON de saída")\n'
            '    args = parser.parse_args()\n'
            '    result = {"status": "ok", "skill": "' + name + '"}\n'
            '    out = Path(args.output)\n'
            '    out.parent.mkdir(parents=True, exist_ok=True)\n'
            '    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")\n'
            '    print(f"Sucesso! Resultado gravado em: {out}")\n'
            '    return 0\n\n\n'
            'if __name__ == "__main__":\n'
            '    raise SystemExit(main())\n',
            encoding="utf-8",
        )
        script_section = (
            "\n## Script Determinístico\n"
            f"Execute via `uv run .agents/skills/{name}/scripts/{script_path.name} "
            "--output <arquivo.json>`.\n"
        )

    skill_md = (
        "---\n"
        f"name: {name}\n"
        "description: >-\n"
        f"  {args.description}\n"
        "---\n\n"
        f"# Skill: {name}\n\n"
        "## Visão Geral\n"
        "Descreva o propósito e os pré-requisitos desta skill.\n\n"
        "## Etapas\n"
        "1. Validar entradas e contexto da SPEC.\n"
        "2. Executar a rotina padronizada.\n"
        "3. Verificar saídas de forma determinística.\n"
        f"{script_section}\n"
        "## Validação\n"
        "- Critério objetivo que confirma sucesso da execução.\n\n"
        "## Erros Comuns\n"
        "- Liste 2-3 armadilhas conhecidas a evitar.\n"
    )
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    updated_registry = False
    if args.pattern_id:
        reg_path = root / "ops" / "patterns" / "repetitive_tasks_registry.json"
        if reg_path.exists():
            data = json.loads(reg_path.read_text(encoding="utf-8"))
            for item in data.get("patterns", []):
                if item.get("id") == args.pattern_id:
                    item["extractedSkill"] = name
                    updated_registry = True
            if updated_registry:
                reg_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )

    print(
        json.dumps(
            {
                "createdSkillDir": str(skill_dir),
                "withScript": args.with_script,
                "registryUpdated": updated_registry,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
