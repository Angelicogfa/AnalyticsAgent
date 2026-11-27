---
name: finops-cost-estimator
description: >-
  Calculadora determinística pré-execução de FinOps Multi-Cloud (AWS Athena scan, egress AWS->Azure com/sem
  OneLake S3 Shortcut Cache, Microsoft Fabric Capacity Units) e custo estimado de tokens Gemini 4 (Carbon/Neon/Hydrogen).
  Use na fase PLANNED (planner-architect) e na auditoria (plan-reviewer-critic / governance-auditor).
---

# Skill: Multi-Cloud & Gemini 4 FinOps Cost Estimator

## Execução Determinística (`scripts/estimate_finops.py`)
Nunca estime custos de nuvem ou LLM "de cabeça". Execute:

```powershell
uv run .agents/skills/finops-cost-estimator/scripts/estimate_finops.py `
  --athena-scan-gb 25 `
  --aws-egress-gb 10 `
  --s3-shortcut-cache true `
  --fabric-cu-seconds 900 `
  --llm-model neon `
  --llm-input-k 80 `
  --llm-output-k 15 `
  --output ops/telemetry/finops_estimate.json
```

## Guardrails Validados Automaticamente
Compara automaticamente os parâmetros informados contra `ops/governance/policy.json`:
- Sinaliza `REQUIRES_APPROVAL` se `--athena-scan-gb` ultrapassar `maxAthenaScanGbWithoutApproval`.
- Sinaliza `REQUIRES_APPROVAL` se `--fabric-cu-seconds` ultrapassar `maxFabricCuSecondsPerJob`.
- Sinaliza `FINOPS_WARNING` se houver egress AWS→Azure sem `--s3-shortcut-cache true`.
- Calcula economia estimada ao ativar o OneLake S3 Shortcut Cache (redução típica de ~70–85% em leituras repetidas).
