---
spec_id: SPEC-000B
title: "pbip-powerbi-mcp-precheck"
domain: analytics-bi
status: APPROVED
clouds: "azure-fabric (power-bi-desktop + fabric-git)"
owner: analytics-bi-specialist
created_at: "2026-11-27"
hitl_required: false
---

# SPEC-000B (Interna) — Modelos Semânticos em `.pbip` (TMDL/PBIR), MCP Power BI Desktop e Pré-Checks de Performance

> **SPEC Operacional Base (Referência Interna):** Estabelece o padrão obrigatório de versionamento, operação agêntica via MCP com o **Power BI Desktop** e pré-checks automatizados de performance para todos os modelos semânticos e relatórios do repositório.
>
> As palavras **DEVE**, **NÃO DEVE** e **PODE** indicam, respectivamente, obrigatório, proibido e opcional.

## 1. Contexto e Objetivo
Padronizar o ciclo de vida de modelos semânticos Power BI / Microsoft Fabric para que os agentes (`analytics-bi-specialist`, `plan-reviewer-critic`, `governance-auditor`):
- Versionem modelos exclusivamente em texto estruturado (**`.pbip` + TMDL + PBIR**), habilitando code review em Git e integração nativa com **Microsoft Fabric Git Integration**;
- Operem localmente com o **Power BI Desktop** e arquivos TMDL via servidor MCP oficial (**`powerbi-modeling-mcp`**);
- Executem **pré-checks obrigatórios de performance e boas práticas** antes de qualquer promoção para workspaces de homologação/produção.

## 2. Escopo Multi-Cloud e Estrutura de Versionamento
### Layout Obrigatório no Repositório
```text
src/data_products/analytics/pbip/<dominio>/
├── <Projeto>.pbip
├── <Projeto>.SemanticModel/
│   ├── definition.pbism
│   └── definition/               # TMDL obrigatório (proibido model.bim legado)
│       ├── database.tmdl
│       ├── model.tmdl
│       ├── relationships.tmdl
│       └── tables/*.tmdl
└── <Projeto>.Report/
    ├── definition.pbir
    └── definition/               # PBIR JSON estruturado
```
- Arquivos binários **`*.pbix`** e caches locais (`.pbi/cache.abf`, `.pbi/localSettings.json`) **NÃO DEVEM** ser versionados no Git.

### Configuração MCP (Power BI Desktop + TMDL)
Declarada em `.agents/plugins/multicloud-mcp-connectors/mcp_config.json` (sem credenciais):
- `powerbi-modeling-mcp`: `npx -y @microsoft/powerbi-modeling-mcp@latest --start`
- Modos suportados:
  - Padrão (`--readwrite` com gate `PreToolUse` do Antigravity) para edição TMDL / testes no Desktop mediante SPEC `APPROVED`.
  - `--readonly` quando o objetivo for apenas inspeção/auditoria.
- Conexões suportadas pelo servidor:
  1. Pasta local `.pbip` / TMDL (edição em lote de medidas, descrições, relacionamentos e *calculation groups*).
  2. Instância ativa do **Power BI Desktop** (porta local do Analysis Services) para validação interativa e execução de consultas DAX de teste.

## 3. Parecer de Literatura e Premissas
- **Referências:** Documentação oficial Microsoft Power BI Projects (PBIP), Tabular Model Definition Language (TMDL), Power BI Enhanced Report Format (PBIR), Microsoft `powerbi-modeling-mcp`, SQLBI VertiPaq Analyzer / DAX Studio (`Server Timings`), Tabular Editor Best Practice Analyzer (BPA) e diretrizes Microsoft Fabric Direct Lake Guardrails.
- **Premissas Operacionais:**
  - Modelos semânticos são multiplicadores de custo de Capacity Units (CUs) no Fabric: um relacionamento bidirecional, Auto Date/Time ou medida DAX ineficiente degrada todos os consumidores simultaneamente.
  - Em Direct Lake, tabelas sem **V-Order** ou com excesso de *rowgroups/parquet files* podem causar *fallback* silencioso para DirectQuery.

## 4. Plano Técnico e FinOps (Pipeline de Pré-Check Obrigatório)
Antes de marcar qualquer SPEC de BI/Analytics como `VERIFIED`, o agente **DEVE** executar em ordem:
1. **Pré-Check Estático Determinístico (`pbip_precheck.py`):**
   - Verifica ausência de `.pbix`, uso de TMDL/PBIR, JSON válido, ausência de `LocalDateTable_*`, relacionamentos bidirecionais/M2M, antipadrões DAX (`FILTER` de tabela inteira, `IFERROR`) e cobertura de descrições/formatos em medidas.
2. **Best Practice Analyzer (Tabular Editor CLI):**
   - Executa regras oficiais `BPARules.json` sobre `.SemanticModel/definition`; qualquer violação `Error` bloqueia a promoção.
3. **Perfilamento de Memória & DAX (VertiPaq Analyzer + DAX Studio + `powerbi-modeling-mcp`):**
   - Validar cardinalidade de colunas, tamanho de dicionários, razão *Storage Engine (SE)* vs *Formula Engine (FE)* e ausência de *fallback* DirectQuery em Direct Lake.
4. **Performance Analyzer (Relatórios PBIR):**
   - Conferir quantidade de visuais por página e tempo de resposta dos visuais críticos no Power BI Desktop.

## 5. Revisão e Crítica Adversarial
- **BLOCKERs Automáticos:** commit de `.pbix`, `model.bim` legado, Auto Date/Time habilitado, JSON inválido em PBIR, violação BPA `Error` ou quebra de reconciliação Gold vs Silver.
- **Governança MCP:** mutações no modelo via `powerbi-modeling-mcp` exigem SPEC `APPROVED` e revisão do diff TMDL em Git antes da sincronização com o workspace Fabric.

## 6. Auditoria de Governança
- **Veredito:** `APPROVED` (Baseline Interna)
- **Critério de Aceite Read-Only:**
  1. `powerbi-modeling-mcp` listado e conectado no Antigravity.
  2. `uv run .agents/skills/powerbi-pbip-semantic-ops/scripts/pbip_precheck.py --path src/data_products/analytics/pbip --output ops/telemetry/pbip_precheck_report.json` retornando `passed: true` (`0` blockers).
