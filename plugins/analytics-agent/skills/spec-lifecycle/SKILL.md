---
name: spec-lifecycle
description: >-
  Gerencia o ciclo de vida completo de SPECs de dados (Engenharia, Ciência de Dados/Estatística e Analytics).
  Use quando precisar criar uma nova demanda operacional como SPEC, validar conformidade estrutural,
  avançar transições de status governadas ou arquivar uma SPEC concluída.
---

# Skill: Spec Lifecycle (Spec-Driven Data Operations)

## Visão Geral
Garante que todo fluxo de trabalho operacional nasça padronizado em `specs/active/` a partir dos templates oficiais e respeite rigorosamente a máquina de estados:
`DRAFT -> LITERATURE_CHECK -> PLANNED -> REVIEWED -> CRITIQUED -> APPROVED -> EXECUTING -> VERIFIED -> COMPLETED`.

## CLI Determinística (`scripts/spec_cli.py`)
Sempre execute via `uv run` (ou `python`):

1. **Criar nova SPEC a partir de template:**
   ```powershell
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/spec-lifecycle/scripts/spec_cli.py create --type engineering --slug ingestao-pedidos-s3-fabric --clouds aws,azure-fabric
   ```
   Tipos suportados: `engineering`, `science`, `analytics`, `mlops`, `runtime`.

2. **Validar estrutura e pré-requisitos de uma SPEC:**
   ```powershell
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/spec-lifecycle/scripts/spec_cli.py validate --spec specs/active/SPEC-001-exemplo-cross-cloud-churn.md
   ```

3. **Avançar status respeitando a máquina de estados (proíbe pular fases):**
   ```powershell
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/spec-lifecycle/scripts/spec_cli.py transition --spec specs/active/SPEC-001-exemplo-cross-cloud-churn.md --to PLANNED
   ```

4. **Arquivar SPEC concluída (`COMPLETED`):**
   ```powershell
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/spec-lifecycle/scripts/spec_cli.py archive --spec specs/active/SPEC-001-exemplo-cross-cloud-churn.md
   ```
