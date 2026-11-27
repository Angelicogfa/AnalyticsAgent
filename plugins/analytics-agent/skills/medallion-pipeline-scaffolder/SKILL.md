---
name: medallion-pipeline-scaffolder
description: >-
  Gera esqueleto padronizado e idempotente de produto de dados em src/data_products/engineering/ (src-layout),
  acompanhado de contrato ODCS v3.x em contracts/ e teste unitário pytest em tests/.
  Otimizada para Gemini 4 Hydrogen (data-engineer) após aprovação da SPEC.
---

# Skill: Medallion Pipeline Scaffolder (Hydrogen)

## Execução Determinística (`scripts/scaffold_pipeline.py`)
```powershell
uv run .agents/skills/medallion-pipeline-scaffolder/scripts/scaffold_pipeline.py `
  --spec-id SPEC-001 `
  --domain commercial `
  --slug silver-product-usage `
  --layer silver `
  --partition-col dt_ref
```

## O que o Scaffolder Cria
1. `src/data_products/engineering/<slug>.py` — módulo Python com cabeçalho `SPEC-ID`, `RuntimeConfig.from_env()`, stub de transformação idempotente por partição (`dt_ref`) e gancho de mascaramento PII.
2. `contracts/<domain>-<slug>.odcs.yaml` — contrato ODCS v3.x pré-preenchido pronto para validação por `odcs-contract-validator`.
3. `tests/test_<slug>.py` — teste `pytest` validando idempotência, ausência de duplicatas na chave e conformidade do contrato ODCS.
