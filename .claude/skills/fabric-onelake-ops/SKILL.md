---
name: fabric-onelake-ops
description: >-
  Padrões operacionais, integração MCP (fabric-mcp-server), acesso REST/SQL Endpoint (Python 3.12 + Entra ID)
  e FinOps para Azure / Microsoft Fabric (OneLake, Lakehouse, Spark/Delta V-Order, OneLake Shortcuts para AWS S3
  com cache, Direct Lake, Capacity Units e Microsoft Entra ID / Purview).
  Use ao planejar, revisar ou implementar cargas de trabalho ou análises de dados no Microsoft Fabric.
---

# Skill: Microsoft Fabric & OneLake Operations

## 1. Interface Primária via MCP (`fabric-mcp-server`)
- Utilize preferencialmente as ferramentas do servidor MCP `fabric-mcp-server` (configurado em `.agents/plugins/multicloud-mcp-connectors/mcp_config.json`) para descoberta de workspaces, lakehouses, tabelas OneLake e metadados (`core_list-workspaces`, `onelake_list-tables`, etc.).
- **Governança do `--mode all`:** Operações somente leitura são livres para descoberta; qualquer operação que crie/altere/apague itens, execute jobs ou modifique papéis exige **SPEC `APPROVED`** e confirmação explícita do gate `PreToolUse`.
- Em caso de falha de autenticação, valide a sessão local (`az login`) via skill `multicloud-mcp-runtime`.

## 2. Acesso Programático (API REST & SQL Endpoints)
Para análises e consultas diretas via scripts Python locais, siga integralmente o runbook detalhado em [fabric-rest-sql-runbook.md](./references/fabric-rest-sql-runbook.md):
- **Runtime obrigatório:** venv **Python 3.11 ou 3.12** (nunca Python 3.13+ atrás de proxy corporativo; não usar `az rest`).
- **Autenticação sem segredos:** `AzureCliCredential` (`azure-identity`) com escopos `https://api.fabric.microsoft.com/.default` (REST) e `https://database.windows.net/.default` (SQL Endpoint via `mssql-python` com atributo `SQL_COPT_SS_ACCESS_TOKEN = 1256`).
- **Obtenção de `connectionString`:** leia sempre de `GET /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}` → `properties.sqlEndpointProperties.connectionString` (não está presente em `GET /sqlEndpoints/{id}`).
- **SQL Endpoint sem tabelas visíveis (apenas `sys`/`queryinsights`):** dispare sincronização de metadados (somente metadados, não altera dados): `POST /v1/workspaces/{workspaceId}/sqlEndpoints/{sqlEndpointId}/refreshMetadata`. Se `INFORMATION_SCHEMA` retornar *deadlock* durante o refresh, aguarde alguns segundos e retente.

## 3. Arquitetura, FinOps & Governança
1. **Acesso a Dados na AWS via OneLake Shortcuts:**
   - Prefira **S3 Shortcuts** com **Shortcut Caching habilitado** no workspace Fabric para reduzir custos de *data egress* da AWS em leituras repetidas.
   - S3 Shortcuts são otimizados para leitura; execute transformações pesadas sobre dados da AWS na própria AWS (Glue/Spark) expondo Silver/Gold em Delta/Iceberg.
2. **Otimização Delta Lake & Direct Lake:**
   - Habilite **V-Order** nas tabelas Gold consumidas por modelos semânticos Direct Lake.
   - Execute `OPTIMIZE` e `VACUUM` com política de retenção definida para evitar *small files* e fallback para DirectQuery.
3. **Capacidade (CUs) e Segurança:**
   - Agende jobs pesados fora da janela de pico de consumo analítico e encerre sessões Spark ociosas.
   - Controle de acesso exclusivo via grupos **Entra ID**, ambientes isolados (`DEV`/`HOMOLOG`/`PROD`) e linhagem compatível com **Microsoft Purview**.
