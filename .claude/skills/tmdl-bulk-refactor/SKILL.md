---
name: tmdl-bulk-refactor
description: >-
  Protocolo de padronização e refatoração em lote de arquivos TMDL (.SemanticModel/definition/*.tmdl)
  otimizado para Gemini 4 Hydrogen (analytics-bi-specialist) via powerbi-modeling-mcp e edição estruturada,
  seguido obrigatoriamente de pbip_precheck.py.
---

# Skill: TMDL Bulk Refactor (Hydrogen)

## Quando Ativar
Ao padronizar múltiplas tabelas, medidas ou relacionamentos em projetos `.pbip` dentro de `src/data_products/analytics/pbip/`.

## Etapas Padronizadas
1. **Inventário Inicial:** Rode primeiro o pré-check para listar todas as pendências em arquivo:
   ```powershell
   uv run .agents/skills/powerbi-pbip-semantic-ops/scripts/pbip_precheck.py `
     --path src/data_products/analytics/pbip `
     --output ops/telemetry/pbip_before.json
   ```
2. **Refatoração Disciplinada em Lote (via `powerbi-modeling-mcp` ou edição TMDL):**
   - Adicionar descrições `///` canônicas alinhadas à SPEC em todas as medidas públicas.
   - Definir `formatString` explícito (`#,0.00`, `0.0%`, `#,0`) e `displayFolder` por domínio de KPI.
   - Ocultar chaves estrangeiras (`isHidden`) em tabelas fato para evitar agregação acidental por usuários finais.
   - Substituir `IFERROR()` por `DIVIDE()` e reescrever `FILTER(ALL(Tabela), ...)` usando filtros diretos de coluna / `KEEPFILTERS`.
   - Remover tabelas automáticas `LocalDateTable_*` (desativando Auto Date/Time).
3. **Validação Pós-Refatoração (Obrigatória):**
   - Reexecutar `pbip_precheck.py` confirmando `passed: true` (`0` blockers e redução de majors/minors).
   - Validar via `powerbi-modeling-mcp` no Power BI Desktop que as consultas `EVALUATE` das medidas reconciliam com a camada Gold.
