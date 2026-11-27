#!/usr/bin/env python3
"""Gera esqueleto padronizado de produto de dados (src/data_products/engineering + contracts ODCS + pytest)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffolder de produto de dados Medallion (src-layout + ODCS + pytest).")
    parser.add_argument("--spec-id", required=True, help="ID da SPEC aprovada (ex.: SPEC-002)")
    parser.add_argument("--domain", required=True, help="Domínio de negócio (ex.: commercial, finance)")
    parser.add_argument("--slug", required=True, help="Nome do pipeline em kebab-case")
    parser.add_argument("--layer", choices=["bronze", "silver", "gold"], default="silver")
    parser.add_argument("--partition-col", default="dt_ref")
    args = parser.parse_args()

    slug = re.sub(r"[^a-z0-9-]+", "-", args.slug.lower()).strip("-")
    mod_name = slug.replace("-", "_")
    domain = re.sub(r"[^a-z0-9-]+", "-", args.domain.lower()).strip("-")

    root = repo_root()
    py_path = root / "src" / "data_products" / "engineering" / f"{mod_name}.py"
    contract_path = root / "contracts" / f"{domain}-{slug}.odcs.yaml"
    test_path = root / "tests" / f"test_{mod_name}.py"

    for p in (py_path, contract_path, test_path):
        if p.exists():
            print(f"Erro: arquivo já existe: {p}", file=sys.stderr)
            return 1

    py_code = (
        f'"""Produto de dados ({args.layer}): {domain}/{slug}.\n\n'
        f'SPEC-ID: {args.spec_id}\n'
        '"""\n\n'
        'from __future__ import annotations\n\n'
        'from typing import Any\n\n'
        'from data_products.common.config import RuntimeConfig\n\n\n'
        'def transform_partition(records: list[dict[str, Any]], partition_value: str) -> list[dict[str, Any]]:\n'
        '    """Transformação idempotente por partição (deduplica por entity_id e remove campos PII)."""\n'
        '    _cfg = RuntimeConfig.from_env()\n'
        '    pii_blocked = {"cpf", "cnpj", "email", "telefone", "nome_completo"}\n'
        '    dedup: dict[str, dict[str, Any]] = {}\n'
        '    for row in records:\n'
        '        clean = {k: v for k, v in row.items() if k.lower() not in pii_blocked}\n'
        f'        clean["{args.partition_col}"] = partition_value\n'
        '        key = str(clean.get("entity_id", ""))\n'
        '        if key:\n'
        '            dedup[key] = clean\n'
        '    return list(dedup.values())\n'
    )
    py_path.write_text(py_code, encoding="utf-8")

    template_odcs = (root / "contracts" / "templates" / "data-contract.odcs.yaml").read_text(encoding="utf-8")
    odcs_filled = (
        template_odcs.replace("<domain>-<data-product-slug>", f"{domain}-{slug}")
        .replace("<Nome do Produto de Dados>", f"{domain.title()} {slug}")
        .replace("<ex: commercial | finance | operations>", domain)
        .replace("<slug-do-produto>", slug)
        .replace("SPEC-NNN", args.spec_id)
        .replace("layer:gold", f"layer:{args.layer}")
        .replace("dt_ref", args.partition_col)
    )
    contract_path.write_text(odcs_filled, encoding="utf-8")

    test_code = (
        f'"""Testes determinísticos do produto de dados {mod_name} ({args.spec_id})."""\n\n'
        f'from data_products.engineering.{mod_name} import transform_partition\n\n\n'
        'def test_transform_partition_is_idempotent_and_strips_pii() -> None:\n'
        '    sample = [\n'
        '        {"entity_id": "e1", "metric_value": 10.0, "cpf": "00000000000"},\n'
        '        {"entity_id": "e1", "metric_value": 12.5, "email": "a@example.com"},\n'
        '    ]\n'
        '    out = transform_partition(sample, "2026-11-27")\n'
        '    assert len(out) == 1\n'
        '    assert "cpf" not in out[0] and "email" not in out[0]\n'
        f'    assert out[0]["{args.partition_col}"] == "2026-11-27"\n'
    )
    test_path.write_text(test_code, encoding="utf-8")

    print(
        json.dumps(
            {
                "pipeline": str(py_path),
                "contract": str(contract_path),
                "test": str(test_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
