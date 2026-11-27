---
name: ops-telemetry-auditor
description: >-
  Metrifica operações da rede agêntica a partir de ops/telemetry/events.jsonl e ops/patterns/repetitive_tasks_registry.json.
  Calcula taxa de erros, bloqueios de segurança/FinOps, distribuição de uso por ferramenta/modelo e identifica tarefas repetitivas candidatas a SKILLs.
  Use pelo governance-auditor ao auditar execuções ou gerar relatórios operacionais.
---

# Skill: Ops Telemetry Auditor

## Visão Geral
Converte os eventos gravados automaticamente pelos hooks (`security_finops_gate.py`, `telemetry_logger.py`, `stop_gate.py`) em um relatório objetivo de governança, segurança, custo relativo e maturidade de automação.

## Execução Determinística
```powershell
uv run ${CLAUDE_PLUGIN_ROOT}/skills/ops-telemetry-auditor/scripts/audit_metrics.py --output ops/telemetry/audit_report.json
```

## O que o Relatório Mede
- Total de chamadas de ferramentas, taxa de erro (`ERROR / total`) e ferramentas com mais falhas (sinal de loop ou fricção).
- Total de bloqueios e escalações do `PreToolUse` (`deny`, `force_ask`) agrupados por `ruleId`.
- Distribuição de chamadas por `modelName` (verificação de aderência ao *Model Tiering*).
- Padrões repetitivos em `ops/patterns/repetitive_tasks_registry.json` prontos para extração (`occurrences >= 2` e `extractedSkill == null`).
