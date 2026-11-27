---
spec_id: SPEC-000
title: "mcp-fabric-aws-runtime"
domain: platform-runtime
status: APPROVED
clouds: "multi-cloud (aws, azure-fabric)"
owner: governance-auditor
created_at: "2026-11-27"
hitl_required: false
---

# SPEC-000 (Interna) — MCPs (Microsoft Fabric e AWS), Autenticação, TLS e Runtimes

> **SPEC Operacional Base (Referência Interna):** Define o contrato operacional padrão para que os agentes no **Google Antigravity** e scripts Python locais se conectem ao **Microsoft Fabric** e à **AWS** com segurança, zero segredos em arquivo e compatibilidade com proxies corporativos de inspeção TLS.
>
> As palavras **DEVE**, **NÃO DEVE** e **PODE** indicam, respectivamente, obrigatório, proibido e opcional.

## 1. Contexto e Objetivo
Permitir que a rede agêntica no Antigravity se comunique com **Microsoft Fabric** e **AWS** via MCP e que scripts locais consultem a **API REST** e **SQL Analytics Endpoints** do Fabric:
- Exclusivamente com as credenciais locais do usuário (`az login` / `aws login`), sem segredos versionados;
- Sem nunca desativar a verificação TLS atrás de proxies corporativos (ex.: Zscaler / Corporate Root CA).

## 2. Escopo Multi-Cloud e Arquitetura
```text
Antigravity ──stdio──► fabric-mcp-server (Node, npx @microsoft/fabric-mcp) ──HTTPS──► api.fabric.microsoft.com / OneLake
            └─stdio──► aws-mcp (Python, uvx mcp-proxy-for-aws) ──HTTPS + SigV4──► aws-mcp.<region>.api.aws/mcp

Scripts Locais (Python 3.11 / 3.12) ──HTTPS──► api.fabric.microsoft.com
                                    └──TDS───► <sql-endpoint>.datawarehouse.fabric.microsoft.com
Credenciais: az login (Entra ID) | aws login (IAM Identity Center / SSO)
TLS: bundle de CAs do sistema + CA raiz corporativa (fora do Git)
```

### Requisitos de Runtime
| Componente | Requisito Operacional |
| :--- | :--- |
| **Node.js / npx** | **DEVE** existir no `PATH` para executar `fabric-mcp-server`. |
| **uv / uvx** | **DEVE** existir no `PATH` para executar `aws-mcp` (`mcp-proxy-for-aws`). |
| **Python para scripts Fabric (REST/SQL)** | **DEVE** ser **3.11 ou 3.12**. **NÃO DEVE** ser **3.13+** atrás de proxy com CA sem `basicConstraints` crítico. |
| **Python do `aws-mcp` (`uvx`)** | Preferencialmente **3.11 ou 3.12**; fixar via `uvx --python 3.12` caso `uvx` selecione 3.13+. |
| **Azure CLI (`az`)** | **DEVE** estar autenticado (`az login`) apenas para emissão de token (`AzureCliCredential`). Não usar `az rest` se o CLI embutir Python 3.13+. |
| **AWS CLI (`aws`)** | **DEVE** estar autenticado via `aws login` (SSO) com região padrão configurada em `~/.aws/config`. |
| **Driver SQL Fabric (opcional)** | `mssql-python` + `azure-identity` + `requests` em venv Python 3.12 (dispensa driver ODBC local). |

### Configuração Versionada dos MCPs
Declarada no plugin de workspace `.agents/plugins/multicloud-mcp-connectors/mcp_config.json` (sem segredos nem bloco `env` com credenciais):
- `fabric-mcp-server`: `npx -y @microsoft/fabric-mcp@latest server start --mode all`
- `aws-mcp`: `uvx mcp-proxy-for-aws@latest https://aws-mcp.us-east-1.api.aws/mcp --metadata INSTALL_SOURCE=aws-cli`

Regras operacionais:
- **Sem duplicação:** remover definições duplicadas com o mesmo nome no escopo global de usuário.
- **Governança de `--mode all`:** mutações via MCP exigem SPEC `APPROVED` e passam pelo gate `PreToolUse` (`.agents/hooks/security_finops_gate.py`).
- **Pinning:** caso `@latest` quebre compatibilidade, fixar versão exata no `mcp_config.json` e registrar aqui.

## 3. Parecer de Literatura e Premissas
- **Referências:** Especificação oficial Model Context Protocol (Streamable HTTP / Stdio), documentação oficial `@microsoft/fabric-mcp`, `mcp-proxy-for-aws`, Microsoft Fabric REST API (`lakehouses`, `sqlEndpoints/refreshMetadata`), `azure-identity` (`AzureCliCredential`), PEP / CPython 3.13 X.509 strict verification (`VERIFY_X509_STRICT`).
- **Premissas Operacionais:**
  - Tokens Entra ID e sessões AWS SSO expiram periodicamente e causam falha imediata na conexão MCP até renovação.
  - Metadados do SQL Analytics Endpoint podem ficar defasados em relação às tabelas Delta do Lakehouse, exigindo `refreshMetadata`.
  - Consultas concorrentes a `INFORMATION_SCHEMA` durante sincronização de metadados podem sofrer *deadlock* transitório.

## 4. Plano Técnico e FinOps
### Matriz de Problemas Conhecidos e Decisões Operacionais
| # | Sintoma | Causa Raiz | Decisão Padrão |
| :---: | :--- | :--- | :--- |
| 1 | `CERTIFICATE_VERIFY_FAILED: Basic Constraints of CA cert not marked critical` (ex.: `az rest`) | Python 3.13+ ativa checagem X.509 estrita incompatível com CA raiz corporativa sem flag crítica. | Executar clientes REST/SQL Fabric em **Python 3.11/3.12** com bundle CA confiável; nunca desligar TLS. |
| 2 | `aws-mcp` falha ao conectar (`failed` / `Invalid request parameters`) | Credencial expirada, instabilidade de rede ou `uvx` escolhendo Python 3.13+. | Renovar `aws login`, reconectar MCP, rodar `verify_mcp_env.py --probe-aws-mcp` e fixar `uvx --python 3.12` se necessário. |
| 3 | SQL Endpoint do Lakehouse mostra apenas `sys` e `queryinsights` | Metadados do SQL Endpoint dessincronizados com o OneLake. | Chamar `POST /v1/workspaces/{ws}/sqlEndpoints/{id}/refreshMetadata` (somente metadados, sem impacto nos dados). |
| 4 | `GET /sqlEndpoints/{id}` não retorna `connectionString` | Campo exposto no recurso Lakehouse. | Ler via `GET /v1/workspaces/{ws}/lakehouses/{id}` → `properties.sqlEndpointProperties.connectionString`. |
| 5 | Deadlock ao consultar `INFORMATION_SCHEMA` | Sincronização de metadados em execução concorrente. | Aplicar retry com espera curta (5–10s, máx. 3 tentativas). |
| 6 | Restrição de shell/HTTP em sandbox corporativo | Políticas de segurança/endpoint da estação. | Usar scripts Python determinísticos com `requests` + bundle CA; nunca tentar contornar bloqueios de sandbox ou proxy. |

## 5. Revisão e Crítica Adversarial
- **TLS:** Proibido `verify=False`, `NODE_TLS_REJECT_UNAUTHORIZED=0`, `AZURE_CLI_DISABLE_CONNECTION_VERIFICATION` ou `curl -k` (enforced via `RULE-05` e `security_finops_gate.py`).
- **Segredos:** Nenhum token/chave persistido em arquivos, prompts ou telemetria (`verify_mcp_env.py` mascara Account IDs e nunca imprime tokens).
- **MCP `--mode all`:** Operações destrutivas bloqueadas (`deny`) e mutáveis exigindo aprovação explícita (`force_ask`).

## 6. Auditoria de Governança
- **Veredito:** `APPROVED` (Baseline Interna)
- **Verificação de Aceite (Somente Leitura):**
  1. Executar `uv run .agents/skills/multicloud-mcp-runtime/scripts/verify_mcp_env.py --check-auth --probe-aws-mcp --output ops/telemetry/mcp_env_check.json`.
  2. Confirmar servidores `fabric-mcp-server` e `aws-mcp` conectados no Antigravity.
  3. Confirmar descoberta read-only no Fabric (`core_list-workspaces` / `onelake_list-tables`) e consulta `SELECT TOP (1)` via Python 3.12 + token `database.windows.net` (`SQL_COPT_SS_ACCESS_TOKEN = 1256`).
