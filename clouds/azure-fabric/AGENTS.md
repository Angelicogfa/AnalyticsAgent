# Regras de Escopo — Azure / Microsoft Fabric (`clouds/azure-fabric/`)

Aplicadas automaticamente quando agentes operam em artefatos relacionados ao Microsoft Fabric.

## Padrões Obrigatórios Microsoft Fabric
1. **Arquitetura Medallion no OneLake:**
   - `Bronze` (dados brutos imutáveis, preferencialmente via **OneLake Shortcuts** para S3 quando origem for AWS).
   - `Silver` (dados limpos, deduplicados, tipados, PII mascarada, Delta Lake com V-Order).
   - `Gold` (tabelas dimensionais/fato e features prontas para **Direct Lake** e Ciência de Dados).
2. **Interoperabilidade AWS → Fabric (FinOps):**
   - Sempre que consumir dados residentes na AWS S3, avalie primeiro **OneLake S3 Shortcuts** com **Shortcut Caching habilitado** no workspace para reduzir custos de *egress* da AWS.
   - Evite duplicar camadas Bronze da AWS para dentro do OneLake sem justificativa explícita aprovada na SPEC.
3. **Gestão de Capacidade (Fabric CUs):**
   - Documente o SKU/Capacidade alvo e estime o consumo de CUs na SPEC.
   - Use notebooks Spark otimizados (`V-Order`, `OPTIMIZE`, broadcast joins quando aplicável) e desative sessões interativas ociosas.
   - Evite sobrecarga de Spark em horários de pico de relatórios Power BI / Direct Lake na mesma capacidade.
4. **Governança e Segurança:**
   - Permissões exclusivamente via grupos **Microsoft Entra ID** (nunca conceder acesso direto por usuário nominal em produção).
   - Registre linhagem e classificação de sensibilidade compatíveis com **Microsoft Purview**.
   - Separação estrita de workspaces: `DEV`, `HOMOLOG`, `PROD` usando Deployment Pipelines / Git Integration.
5. **MCP (`fabric-mcp-server`), REST & SQL Endpoints (`RULE-05` / `SPEC-000`):**
   - Prefira `fabric-mcp-server` para descoberta read-only; mutações (`--mode all`) exigem SPEC `APPROVED` e confirmação humana.
   - Scripts REST/SQL devem rodar em **Python 3.11/3.12** com `AzureCliCredential` e bundle CA confiável (nunca `verify=False`, nunca `az rest` em Python 3.13+).
   - Leia `connectionString` em `GET /v1/workspaces/{ws}/lakehouses/{id}` (não em `/sqlEndpoints/{id}`). Se o SQL Endpoint exibir apenas `sys`/`queryinsights`, sincronize com `POST .../sqlEndpoints/{id}/refreshMetadata` e aplique retry curto se `INFORMATION_SCHEMA` sofrer *deadlock*.
6. **Modelos Semânticos Power BI (`.pbip` / TMDL / PBIR + MCP + Pré-Check — `SPEC-000B`):**
   - Versionamento obrigatório em **`.pbip` + TMDL** (`.SemanticModel/definition/*.tmdl`) e **PBIR** (`.Report/definition/`) dentro de `src/data_products/analytics/pbip/`. Proibido versionar binários `.pbix` ou `model.bim` legado.
   - Operação local com **Power BI Desktop** e refatoração TMDL via MCP `powerbi-modeling-mcp` (mutações exigem SPEC `APPROVED`).
   - Pré-check obrigatório antes de `VERIFIED`/deploy: executar `pbip_precheck.py` (0 blockers), **Tabular Editor BPA** (`BPARules.json`), perfilamento **VertiPaq Analyzer / DAX Studio** (SE vs FE, cardinalidade, ausência de Auto Date/Time) e checagem de guardrails **Direct Lake**.
