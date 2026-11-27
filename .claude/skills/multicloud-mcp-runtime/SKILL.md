---
name: multicloud-mcp-runtime
description: >-
  Diagnostica, valida e soluciona problemas operacionais dos servidores MCP (fabric-mcp-server e aws-mcp),
  autenticação local (az login / aws login), TLS atrás de proxy corporativo com CA customizada e
  compatibilidade de runtimes Python 3.11/3.12 vs 3.13+. Use antes de iniciar tarefas multi-cloud ou
  quando houver falha de conexão MCP, erro CERTIFICATE_VERIFY_FAILED ou token expirado.
---

# Skill: Multi-Cloud MCP, Auth & TLS Runtime Ops

## Visão Geral
Garante que o ambiente local esteja pronto para operar **Microsoft Fabric** (`fabric-mcp-server` via `npx`) e **AWS** (`aws-mcp` via `uvx mcp-proxy-for-aws`) usando exclusivamente credenciais do usuário (`az login` / `aws login`), sem segredos em arquivo e **sem nunca desativar verificação TLS** (`RULE-05`).

## Verificação Read-Only Determinística (`scripts/verify_mcp_env.py`)
Execute o diagnóstico completo (100% somente leitura, saída estruturada em arquivo):

```powershell
uv run .agents/skills/multicloud-mcp-runtime/scripts/verify_mcp_env.py --output ops/telemetry/mcp_env_check.json
```

Para incluir o *probe* JSON-RPC (`initialize` + `tools/list` via stdio) contra o `aws-mcp`:
```powershell
uv run .agents/skills/multicloud-mcp-runtime/scripts/verify_mcp_env.py --probe-aws-mcp --output ops/telemetry/mcp_env_check.json
```

## Checklist Operacional Rápido
1. **Runtimes obrigatórios no `PATH`:** `node`/`npx` (para `fabric-mcp-server`), `uv`/`uvx` (para `aws-mcp`), `az` (apenas emissão de token), `aws` (SSO `aws login` com região configurada).
2. **Restrição Python 3.11 / 3.12 (Proibido 3.13+ em clientes TLS corporativos):**
   - Scripts REST/SQL do Fabric **DEVEM** usar venv **Python 3.11 ou 3.12**.
   - Se o `uvx` selecionar Python 3.13+ e falhar com `Basic Constraints of CA cert not marked critical`, fixe o runtime com `uvx --python 3.12 mcp-proxy-for-aws@latest ...`.
   - Não use `az rest` quando o Azure CLI embutir Python 3.13+; use `AzureCliCredential` em Python 3.12.
3. **TLS atrás de Proxy Corporativo:**
   - Monte um bundle combinando CAs do sistema + CA raiz corporativa (fora do Git) e passe-o **somente no processo** via `REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE` ou `verify=<bundle>`.
   - Para Node (`fabric-mcp-server`), se houver erro de certificado, use `NODE_EXTRA_CA_CERTS=<caminho-ca.crt>`.
   - **Nunca** use `verify=False`, `NODE_TLS_REJECT_UNAUTHORIZED=0` ou `AZURE_CLI_DISABLE_CONNECTION_VERIFICATION`.
4. **Configuração MCP sem duplicação:**
   - Fonte única de verdade no repositório: `.agents/plugins/multicloud-mcp-connectors/mcp_config.json`.
   - Se `aws-mcp` ou `fabric-mcp-server` também existir em configuração global de usuário, remova a duplicata para evitar colisão.
   - Se `@latest` quebrar, fixe a versão exata no `mcp_config.json` e documente em `specs/internal/SPEC-000-mcp-fabric-aws-runtime.md`.

## Troubleshooting de Problemas Conhecidos
Consulte a tabela completa de diagnóstico e mitigação em `specs/internal/SPEC-000-mcp-fabric-aws-runtime.md`.
