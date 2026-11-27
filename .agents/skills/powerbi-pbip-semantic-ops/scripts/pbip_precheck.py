#!/usr/bin/env python3
"""Pré-check determinístico de projetos Power BI (.pbip / TMDL / PBIR) e integração opcional com Tabular Editor BPA.

Verifica estrutura PBIP, ausência de .pbix binários, uso de TMDL/PBIR, antipadrões de performance
(Auto Date/Time, relacionamentos bidirecionais, iteradores DAX pesados, falta de descrições/formatos)
e grava relatório estruturado JSON em arquivo.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def scan_tmdl_file(path: Path) -> list[dict]:
    findings: list[dict] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    rel = str(path)

    # 1. Auto Date/Time (LocalDateTable / DateTableTemplate) - grande vilão de memória VertiPaq
    if re.search(r"\b(LocalDateTable_|DateTableTemplate_)", text):
        findings.append(
            {
                "severity": "BLOCKER",
                "ruleId": "PBI-PERF-AUTO-DATETIME",
                "file": rel,
                "message": "Detectada tabela automática Auto Date/Time (LocalDateTable/DateTableTemplate). Desative Auto Date/Time e use DimCalendario compartilhada.",
            }
        )

    # 2. Relacionamento bidirecional (risco de ambiguidade e degradação severa de performance)
    if re.search(r"(?i)crossFilteringBehavior\s*:\s*bothDirections", text):
        findings.append(
            {
                "severity": "MAJOR",
                "ruleId": "PBI-PERF-BIDIR-REL",
                "file": rel,
                "message": "Relacionamento bidirecional (bothDirections) detectado. Substitua por filtro unidirecional ou CROSSFILTER pontual em DAX, salvo justificativa na SPEC.",
            }
        )

    # 3. Relacionamento many-to-many
    if re.search(r"(?i)fromCardinality\s*:\s*many", text) and re.search(r"(?i)toCardinality\s*:\s*many", text):
        findings.append(
            {
                "severity": "MAJOR",
                "ruleId": "PBI-PERF-M2M-REL",
                "file": rel,
                "message": "Relacionamento many-to-many detectado. Avalie tabela ponte (bridge table) ou ajuste de grão.",
            }
        )

    # 4. Antipadrão DAX: FILTER sobre tabela inteira ou ALL/ALLSELECTED/ALLEXCEPT(Tabela)
    if re.search(r"(?i)\bFILTER\s*\(\s*(ALL(SELECTED|EXCEPT)?\s*\(\s*)?'?[A-Za-z0-9_ ]+'?\s*\)?\s*,", text):
        findings.append(
            {
                "severity": "MAJOR",
                "ruleId": "PBI-DAX-FILTER-TABLE",
                "file": rel,
                "message": "Possível FILTER() iterando tabela inteira detectado. Prefira filtros diretos em colunas (KEEPFILTERS / predicado de coluna) para evitar sobrecarga no Formula Engine.",
            }
        )

    # 5. Uso de IFERROR (força avaliação lenta no Formula Engine)
    if re.search(r"(?i)\bIFERROR\s*\(", text):
        findings.append(
            {
                "severity": "MINOR",
                "ruleId": "PBI-DAX-IFERROR",
                "file": rel,
                "message": "Uso de IFERROR() detectado. Prefira DIVIDE() ou validações explícitas para evitar penalidade de performance.",
            }
        )

    # 6. Tipo float (double) em colunas numéricas onde decimal/currency seria preferível ou chaves
    if re.search(r"(?i)dataType\s*:\s*double", text):
        findings.append(
            {
                "severity": "MINOR",
                "ruleId": "PBI-VERTIPAQ-DOUBLE",
                "file": rel,
                "message": "Coluna com dataType: double detectada. Avalie decimal (fixed decimal) se precisão de 4 casas bastar para melhor compressão VertiPaq.",
            }
        )

    # 7. Checagem simples de medidas sem formatString ou sem documentação (/// description)
    measure_blocks = re.split(r"(?m)^(\s*measure\s+)", text)
    if len(measure_blocks) > 1:
        # Avalia cada bloco de medida após a declaração
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            if re.match(r"^\s*measure\s+", line):
                # Checa comentário TMDL /// imediatamente acima
                has_doc = idx > 0 and lines[idx - 1].lstrip().startswith("///")
                # Checa formatString nas próximas 25 linhas até próxima declaração
                block_slice = "\n".join(lines[idx + 1 : min(len(lines), idx + 26)])
                has_fmt = bool(re.search(r"(?i)\bformatString\s*:", block_slice))
                m_name = line.strip()[:80]
                if not has_doc:
                    findings.append(
                        {
                            "severity": "MINOR",
                            "ruleId": "PBI-DOC-MEASURE-DESC",
                            "file": rel,
                            "message": f"Medida sem descrição TMDL ('/// ...'): {m_name}",
                        }
                    )
                if not has_fmt:
                    findings.append(
                        {
                            "severity": "MINOR",
                            "ruleId": "PBI-FMT-MEASURE",
                            "file": rel,
                            "message": f"Medida sem formatString explícito: {m_name}",
                        }
                    )

    return findings


def maybe_run_tabular_editor_bpa(semantic_model_def: Path, bpa_rules: Path | None) -> dict:
    te_bin = shutil.which("TabularEditor") or shutil.which("TabularEditor.CLI") or shutil.which("te")
    if not te_bin:
        return {
            "executed": False,
            "reason": "Tabular Editor CLI não encontrado no PATH. Execute manualmente ou instale no runner CI.",
        }
    if not bpa_rules or not bpa_rules.exists():
        return {
            "executed": False,
            "reason": "Caminho --bpa-rules não informado ou inexistente; BPA externo pulado.",
        }
    try:
        proc = subprocess.run(
            [te_bin, str(semantic_model_def), "-A", str(bpa_rules), "-V"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return {
            "executed": True,
            "binary": te_bin,
            "returncode": proc.returncode,
            "stdoutSample": proc.stdout.strip()[:1000],
            "stderrSample": proc.stderr.strip()[:500],
        }
    except Exception as exc:
        return {"executed": False, "error": str(exc)[:300]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Pré-check determinístico de projetos Power BI (.pbip / TMDL / PBIR).")
    parser.add_argument("--path", required=True, help="Diretório raiz contendo projetos .pbip (ex.: src/analytics/pbip)")
    parser.add_argument("--output", required=True, help="Arquivo JSON de saída do relatório de pré-check")
    parser.add_argument("--bpa-rules", default="", help="Opcional: caminho para BPARules.json do Tabular Editor CLI")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"Erro: diretório não encontrado: {target}", file=sys.stderr)
        return 1

    findings: list[dict] = []

    # 1. Proibir arquivos binários .pbix
    for pbix in target.rglob("*.pbix"):
        findings.append(
            {
                "severity": "BLOCKER",
                "ruleId": "PBI-NO-BINARY-PBIX",
                "file": str(pbix),
                "message": "Arquivo binário .pbix detectado. Converta para formato .pbip (TMDL + PBIR) antes de versionar.",
            }
        )

    # 2. Detectar model.bim legado em vez de TMDL
    for legacy_bim in target.rglob("model.bim"):
        findings.append(
            {
                "severity": "BLOCKER",
                "ruleId": "PBI-REQUIRE-TMDL",
                "file": str(legacy_bim),
                "message": "Formato legado model.bim detectado. Habilite TMDL (.SemanticModel/definition/*.tmdl) no Power BI Desktop.",
            }
        )

    # 3. Validar JSON de arquivos .pbip, definition.pbism, definition.pbir e PBIR
    pbip_files = list(target.rglob("*.pbip"))
    json_checked = 0
    for jf in list(target.rglob("*.pbip")) + list(target.rglob("*.pbism")) + list(target.rglob("*.pbir")) + list(target.rglob("*.json")):
        try:
            json.loads(jf.read_text(encoding="utf-8-sig"))
            json_checked += 1
        except Exception as exc:
            findings.append(
                {
                    "severity": "BLOCKER",
                    "ruleId": "PBI-INVALID-JSON",
                    "file": str(jf),
                    "message": f"JSON inválido em artefato PBIP/PBIR: {exc}",
                }
            )

    # 4. Inspecionar arquivos TMDL
    tmdl_files = list(target.rglob("*.tmdl"))
    for tf in tmdl_files:
        findings.extend(scan_tmdl_file(tf))

    # 5. Checar se existe SemanticModel sem definição TMDL
    semantic_models = [p for p in target.rglob("*.SemanticModel") if p.is_dir()]
    bpa_results = []
    bpa_rules_path = Path(args.bpa_rules) if args.bpa_rules else None
    for sm in semantic_models:
        def_dir = sm / "definition"
        if not def_dir.exists() or not list(def_dir.rglob("*.tmdl")):
            findings.append(
                {
                    "severity": "BLOCKER",
                    "ruleId": "PBI-MISSING-TMDL-DEF",
                    "file": str(sm),
                    "message": "Pasta .SemanticModel não contém definição TMDL em definition/*.tmdl.",
                }
            )
        else:
            bpa_results.append(
                {"semanticModel": str(sm), "bpa": maybe_run_tabular_editor_bpa(def_dir, bpa_rules_path)}
            )

    counts = {
        "BLOCKER": sum(1 for f in findings if f["severity"] == "BLOCKER"),
        "MAJOR": sum(1 for f in findings if f["severity"] == "MAJOR"),
        "MINOR": sum(1 for f in findings if f["severity"] == "MINOR"),
    }
    passed = counts["BLOCKER"] == 0

    report = {
        "generatedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scannedPath": str(target),
        "summary": {
            "pbipProjectsFound": len(pbip_files),
            "semanticModelsFound": len(semantic_models),
            "tmdlFilesScanned": len(tmdl_files),
            "jsonArtifactsValidated": json_checked,
            "counts": counts,
            "passed": passed,
        },
        "externalBpaChecks": bpa_results,
        "findings": findings,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Pré-check PBIP gravado em: {out} "
        f"(passed={passed}, blockers={counts['BLOCKER']}, majors={counts['MAJOR']}, minors={counts['MINOR']})"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
