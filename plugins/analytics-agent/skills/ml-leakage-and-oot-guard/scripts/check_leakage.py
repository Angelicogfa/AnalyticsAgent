#!/usr/bin/env python3
"""Auditor estático (AST + padrões) de data leakage, reprodutibilidade e conformidade TLS em src/data_products/science/."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import re
import sys
from pathlib import Path


def has_unverified_tls_call(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "verify" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                    return True
    return False


def inspect_python_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings: list[dict] = []
    rel = str(path)

    fit_match = re.search(r"\.fit_transform\s*\(", text)
    split_match = re.search(r"\btrain_test_split\s*\(", text)
    if fit_match and split_match and fit_match.start() < split_match.start():
        findings.append(
            {
                "severity": "BLOCKER",
                "ruleId": "ML-LEAK-FIT-BEFORE-SPLIT",
                "file": rel,
                "message": "Chamada `.fit_transform()` detectada antes de `train_test_split()`. Encapsule em sklearn.pipeline.Pipeline após o split.",
            }
        )

    if split_match and re.search(r"(?i)\b(dt_|date|timestamp|oot|temporal)\b", text):
        if not re.search(r"shuffle\s*=\s*False", text):
            findings.append(
                {
                    "severity": "MAJOR",
                    "ruleId": "ML-LEAK-SHUFFLE-SPLIT",
                    "file": rel,
                    "message": "Dataset com indício temporal usando `train_test_split` sem `shuffle=False`. Use split Out-of-Time (OOT) / TimeSeriesSplit.",
                }
            )

    if re.search(r"\b(RandomForest|XGB|LGBM|CatBoost|KFold|StratifiedKFold|train_test_split)\w*\s*\(", text):
        if "random_state" not in text and "seed" not in text:
            findings.append(
                {
                    "severity": "MAJOR",
                    "ruleId": "ML-REPRO-NO-SEED",
                    "file": rel,
                    "message": "Componente estocástico detectado sem `random_state` / `seed` fixo.",
                }
            )

    try:
        tree = ast.parse(text, filename=rel)
        if has_unverified_tls_call(tree):
            findings.append(
                {
                    "severity": "BLOCKER",
                    "ruleId": "ML-TLS-BYPASS",
                    "file": rel,
                    "message": "Chamada HTTP com desativação de verificação TLS bloqueada pela RULE-05.",
                }
            )
    except SyntaxError as exc:
        findings.append(
            {
                "severity": "BLOCKER",
                "ruleId": "ML-SYNTAX-ERROR",
                "file": rel,
                "message": f"Erro de sintaxe Python: {exc}",
            }
        )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Detector estático de data leakage e reprodutibilidade ML.")
    parser.add_argument("--path", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"Erro: diretório não encontrado: {target}", file=sys.stderr)
        return 1

    py_files = [p for p in target.rglob("*.py") if "__pycache__" not in p.parts]
    findings: list[dict] = []
    for pf in py_files:
        findings.extend(inspect_python_file(pf))

    blockers = sum(1 for f in findings if f["severity"] == "BLOCKER")
    majors = sum(1 for f in findings if f["severity"] == "MAJOR")
    report = {
        "generatedAtUtc": dt.datetime.now(dt.UTC).isoformat(),
        "scannedPath": str(target),
        "filesScanned": len(py_files),
        "passed": blockers == 0,
        "counts": {"BLOCKER": blockers, "MAJOR": majors},
        "findings": findings,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Auditoria ML leakage gravada em: {out} (passed={report['passed']}, blockers={blockers}, majors={majors})")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
