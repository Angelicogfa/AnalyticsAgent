#!/usr/bin/env python3
"""Validador determinístico de contratos ODCS v3.x (funciona com stdlib puro sem exigir PyYAML)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

REQUIRED_TOP_KEYS = ["apiVersion:", "kind:", "id:", "version:", "servers:", "schema:", "slaProperties:"]
PII_NAMES = {"cpf", "cnpj", "rg", "ssn", "email", "telefone", "celular", "endereco", "data_nascimento", "nome_completo"}


def validate_contract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings: list[dict] = []

    for key in REQUIRED_TOP_KEYS:
        if not re.search(rf"(?m)^{re.escape(key)}", text):
            findings.append({"severity": "BLOCKER", "ruleId": "ODCS-MISSING-KEY", "message": f"Chave obrigatória ausente: {key}"})

    if not re.search(r"(?m)^apiVersion:\s*v?3\.", text):
        findings.append({"severity": "MAJOR", "ruleId": "ODCS-VERSION", "message": "apiVersion deveria seguir ODCS v3.x."})

    if not re.search(r"(?m)^kind:\s*DataContract\b", text):
        findings.append({"severity": "BLOCKER", "ruleId": "ODCS-KIND", "message": "kind deve ser DataContract."})

    if not re.search(r"(?m)^\s+partitioned:\s*true\b", text):
        findings.append(
            {
                "severity": "MAJOR",
                "ruleId": "ODCS-FINOPS-PARTITION",
                "message": "Nenhuma coluna marcada com `partitioned: true` (obrigatório para FinOps em Athena/Spark).",
            }
        )

    if not re.search(r"(?m)^\s+quality:", text):
        findings.append({"severity": "MAJOR", "ruleId": "ODCS-QUALITY", "message": "Bloco `quality:` ausente no schema."})

    # Detecta colunas PII declaradas com classificação public/internal
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        m = re.match(r"^\s*-\s*name:\s*([A-Za-z0-9_]+)\s*$", line)
        if m and m.group(1).lower() in PII_NAMES:
            block = "\n".join(lines[idx : min(len(lines), idx + 12)])
            if re.search(r"(?i)classification:\s*(public|internal)\b", block):
                findings.append(
                    {
                        "severity": "BLOCKER",
                        "ruleId": "ODCS-PII-EXPOSURE",
                        "message": f"Coluna PII '{m.group(1)}' declarada como public/internal. Mascare/remova ou classifique como restricted.",
                    }
                )

    blockers = sum(1 for f in findings if f["severity"] == "BLOCKER")
    majors = sum(1 for f in findings if f["severity"] == "MAJOR")
    return {
        "generatedAtUtc": dt.datetime.now(dt.UTC).isoformat(),
        "contract": str(path),
        "passed": blockers == 0,
        "counts": {"BLOCKER": blockers, "MAJOR": majors},
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validador determinístico de contratos ODCS v3.x.")
    parser.add_argument("--contract", required=True, help="Caminho para arquivo .odcs.yaml")
    parser.add_argument("--output", required=True, help="Arquivo JSON de saída")
    args = parser.parse_args()

    c_path = Path(args.contract)
    if not c_path.exists():
        print(f"Erro: contrato não encontrado: {c_path}", file=sys.stderr)
        return 1

    report = validate_contract(c_path)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validação ODCS gravada em: {out} (passed={report['passed']}, blockers={report['counts']['BLOCKER']})")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
