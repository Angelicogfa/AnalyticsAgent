---
name: odcs-contract-validator
description: >-
  Valida contratos de dados no padrão Open Data Contract Standard (ODCS v3.x) em contracts/*.odcs.yaml:
  campos obrigatórios, presença de chave de partição FinOps, regras de qualidade e ausência de colunas PII
  expostas sem classificação restrita. Otimizada para Gemini 4 Neon e Carbon.
---

# Skill: ODCS Data Contract Validator

## Execução Determinística (`scripts/validate_odcs.py`)
```powershell
uv run .agents/skills/odcs-contract-validator/scripts/validate_odcs.py `
  --contract contracts/templates/data-contract.odcs.yaml `
  --output ops/telemetry/odcs_validation.json
```

## O que é Validado
- Campos obrigatórios ODCS v3.x (`apiVersion`, `kind: DataContract`, `id`, `version`, `servers`, `schema`, `slaProperties`).
- Existência de chave de partição explícita (`partitioned: true`) para controle FinOps (Athena/Spark).
- Declaração de regras de qualidade (`quality:`).
- Alerta `BLOCKER` caso colunas com nomes típicos de PII (`cpf`, `email`, `telefone`, `ssn`, etc.) apareçam sem classificação restrita/mascaramento.
