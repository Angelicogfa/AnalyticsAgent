---
name: powerbi-pbip-semantic-ops
description: >-
  Padroniza desenvolvimento, versionamento (.pbip + TMDL + PBIR), operação via MCP com Power BI Desktop
  (powerbi-modeling-mcp) e pré-checks obrigatórios de performance e boas práticas (análise estática TMDL/PBIR,
  Tabular Editor BPA, VertiPaq Analyzer, DAX Studio e guardrails Direct Lake).
  Use ao criar, alterar, revisar ou auditar modelos semânticos e relatórios Power BI / Microsoft Fabric.
---

# Skill: Power BI PBIP, TMDL/PBIR, Desktop MCP & Performance Pre-Check

## 1. Padrão Obrigatório de Versionamento (`.pbip` + TMDL + PBIR)
- **Proibido versionar `.pbix` binários** no Git. Todo ativo Power BI vive em `src/data_products/analytics/pbip/<dominio>/` no formato **Power BI Project (`.pbip`)**:
  - `<Projeto>.pbip` (manifesto do projeto)
  - `<Projeto>.SemanticModel/definition/` em **TMDL** (`database.tmdl`, `model.tmdl`, `relationships.tmdl`, `tables/*.tmdl`) — não usar `model.bim` monolítico legado.
  - `<Projeto>.Report/definition/` em **PBIR** (JSON estruturado por página/visual).
  - Ignorar caches locais no Git (`.pbi/cache.abf`, `.pbi/localSettings.json`, `*.pbix`).

## 2. Operação via MCP com Power BI Desktop (`powerbi-modeling-mcp`)
Configurado em `.agents/plugins/multicloud-mcp-connectors/mcp_config.json` (zero segredos):
- **Conexão com Power BI Desktop:** anexa à instância local do Analysis Services aberta pelo Power BI Desktop para inspecionar modelo, rodar consultas DAX de validação e testar medidas iterativamente.
- **Edição em escala de TMDL (`.pbip`):** permite refatorar medidas, descrições, *display folders*, relacionamentos e *calculation groups* diretamente nos arquivos `.tmdl` com diffs limpos no Git.
- **Governança de modo:** prefira descoberta/validação antes de mutações; alterações estruturais em `.tmdl` ou no modelo aberto exigem SPEC `APPROVED` e passam pelo gate `PreToolUse`. Caso precise bloquear escrita no servidor MCP, use a flag `--readonly`.

## 3. Pipeline Obrigatório de Pré-Check de Performance & Qualidade
Nenhum modelo semântico pode avançar para `VERIFIED` ou sincronizar com o Microsoft Fabric Git Integration sem executar os pré-checks abaixo (detalhes em [bpa-performance-checklist.md](./references/bpa-performance-checklist.md)):

1. **Pré-Check Determinístico Local (sempre obrigatório — CLI `scripts/pbip_precheck.py`):**
   ```powershell
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/powerbi-pbip-semantic-ops/scripts/pbip_precheck.py --path src/data_products/analytics/pbip --output ops/telemetry/pbip_precheck_report.json
   ```
   Valida: ausência de `.pbix` binários, formato TMDL (não `model.bim` legado), PBIR JSON válido, ausência de Auto Date/Time (`LocalDateTable_*`), relacionamentos bidirecionais não justificados, antipadrões DAX (`FILTER(ALL(...))` / iteradores sobre tabelas inteiras), medidas sem `description`/`formatString` e invoca automaticamente o **Tabular Editor BPA CLI** se disponível (`--bpa-rules <BPARules.json>`).
2. **Best Practice Analyzer (Tabular Editor CLI):**
   - Executa regras oficiais de modelagem/performance (Microsoft BPA Rules) sobre `<Projeto>.SemanticModel/definition`; falhas de severidade `Error` bloqueiam o merge.
3. **VertiPaq Analyzer & DAX Studio (Perfilamento de Memória e SE/FE):**
   - Medir tamanho de dicionários, cardinalidade de colunas, colunas calculadas vs medidas, e proporção *Storage Engine (SE)* vs *Formula Engine (FE)* nas medidas críticas (via DAX Studio / `powerbi-modeling-mcp` conectado ao Power BI Desktop ou XMLA/Semantic Link Labs).
4. **Guardrails Direct Lake (Microsoft Fabric):**
   - Confirmar V-Order nas tabelas Gold Delta, evitar colunas calculadas/relacionamentos que forcem *fallback* silencioso para DirectQuery e validar limites de linhas/memória do SKU da Fabric Capacity.
