#!/usr/bin/env python3
"""CLI determinística para criar, validar, transicionar e arquivar SPECs de dados."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

STATES = [
    "DRAFT",
    "LITERATURE_CHECK",
    "PLANNED",
    "REVIEWED",
    "CRITIQUED",
    "APPROVED",
    "EXECUTING",
    "VERIFIED",
    "COMPLETED",
]

TEMPLATE_MAP = {
    "engineering": "data-engineering.spec.md",
    "science": "data-science-stats.spec.md",
    "analytics": "analytics-bi.spec.md",
    "mlops": "backend-mlops.spec.md",
    "runtime": "mcp-runtime-integration.spec.md",
}

REQUIRED_SECTIONS = [
    "## 1. Contexto e Objetivo",
    "## 2. Escopo Multi-Cloud",
    "## 3. Parecer de Literatura e Premissas",
    "## 4. Plano Técnico e FinOps",
    "## 5. Revisão e Crítica Adversarial",
    "## 6. Auditoria de Governança",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def next_spec_number(root: Path) -> int:
    max_num = 0
    for folder in (root / "specs" / "active", root / "specs" / "archive"):
        if not folder.exists():
            continue
        for f in folder.glob("SPEC-*.md"):
            m = re.match(r"SPEC-(\d+)-", f.name)
            if m:
                max_num = max(max_num, int(m.group(1)))
    return max_num + 1


def cmd_create(args: argparse.Namespace) -> int:
    root = repo_root()
    template_path = root / "specs" / "templates" / TEMPLATE_MAP[args.type]
    if not template_path.exists():
        print(f"Erro: template não encontrado em {template_path}", file=sys.stderr)
        return 1

    num = next_spec_number(root)
    spec_id = f"SPEC-{num:03d}"
    slug = re.sub(r"[^a-z0-9-]+", "-", args.slug.lower()).strip("-")
    dest = root / "specs" / "active" / f"{spec_id}-{slug}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)

    content = template_path.read_text(encoding="utf-8")
    today = dt.date.today().isoformat()
    content = (
        content.replace("SPEC-NNN", spec_id)
        .replace("<YYYY-MM-DD>", today)
        .replace("<slug-da-tarefa>", slug)
        .replace("<aws | azure-fabric | multi-cloud>", args.clouds)
    )
    dest.write_text(content, encoding="utf-8")
    print(json.dumps({"created": str(dest), "specId": spec_id, "status": "DRAFT"}, ensure_ascii=False))
    return 0


def parse_status(text: str) -> str:
    m = re.search(r"^status:\s*([A-Z_]+)", text, re.MULTILINE)
    return m.group(1) if m else "UNKNOWN"


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.spec)
    if not path.exists():
        print(f"Erro: SPEC não encontrada: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    status = parse_status(text)
    missing = [sec for sec in REQUIRED_SECTIONS if sec not in text]
    valid_status = status in STATES
    result = {
        "spec": str(path),
        "status": status,
        "validStatus": valid_status,
        "missingSections": missing,
        "valid": valid_status and not missing,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


def cmd_transition(args: argparse.Namespace) -> int:
    path = Path(args.spec)
    if not path.exists():
        print(f"Erro: SPEC não encontrada: {path}", file=sys.stderr)
        return 1
    target = args.to.upper()
    if target not in STATES:
        print(f"Erro: status inválido '{target}'. Válidos: {STATES}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    current = parse_status(text)
    if current not in STATES:
        print(f"Erro: status atual inválido '{current}'.", file=sys.stderr)
        return 1

    cur_idx = STATES.index(current)
    tgt_idx = STATES.index(target)

    # Permite avançar exatamente 1 passo ou retroceder para PLANNED em caso de rejeição
    allowed = (tgt_idx == cur_idx + 1) or (target == "PLANNED" and current in {"REVIEWED", "CRITIQUED"})
    if not allowed:
        print(
            f"Erro: transição bloqueada ({current} -> {target}). "
            f"Próximo passo válido: {STATES[cur_idx + 1] if cur_idx + 1 < len(STATES) else 'NONE'}",
            file=sys.stderr,
        )
        return 1

    updated = re.sub(r"^status:\s*[A-Z_]+", f"status: {target}", text, count=1, flags=re.MULTILINE)
    path.write_text(updated, encoding="utf-8")
    print(json.dumps({"spec": str(path), "from": current, "to": target}, ensure_ascii=False))
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    root = repo_root()
    path = Path(args.spec)
    if not path.exists():
        print(f"Erro: SPEC não encontrada: {path}", file=sys.stderr)
        return 1
    status = parse_status(path.read_text(encoding="utf-8"))
    if status != "COMPLETED":
        print(f"Erro: apenas SPECs com status COMPLETED podem ser arquivadas (atual: {status}).", file=sys.stderr)
        return 1
    archive_dir = root / "specs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / path.name
    shutil.move(str(path), str(dest))
    print(json.dumps({"archivedTo": str(dest)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Gerenciador de ciclo de vida de SPECs.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Criar SPEC a partir de template")
    p_create.add_argument("--type", choices=list(TEMPLATE_MAP.keys()), required=True)
    p_create.add_argument("--slug", required=True)
    p_create.add_argument("--clouds", default="multi-cloud")
    p_create.set_defaults(func=cmd_create)

    p_val = sub.add_parser("validate", help="Validar estrutura da SPEC")
    p_val.add_argument("--spec", required=True)
    p_val.set_defaults(func=cmd_validate)

    p_tr = sub.add_parser("transition", help="Avançar status da SPEC")
    p_tr.add_argument("--spec", required=True)
    p_tr.add_argument("--to", required=True)
    p_tr.set_defaults(func=cmd_transition)

    p_arc = sub.add_parser("archive", help="Arquivar SPEC concluída")
    p_arc.add_argument("--spec", required=True)
    p_arc.set_defaults(func=cmd_archive)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
