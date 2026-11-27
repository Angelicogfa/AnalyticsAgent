# RULE-05: MCPs Multi-Cloud, Autenticação, TLS Corporativo e Runtimes (P0 — Earned Rule)

- **Classificação:** `P0 — MANDATORY (Earned Rule)`
- **Origem:** Lições operacionais consolidadas de integração com `fabric-mcp-server`, `aws-mcp`, API REST / SQL Endpoints do Microsoft Fabric e proxies corporativos com inspeção TLS (ex.: Zscaler).
- **SPEC Interna de Referência:** `specs/internal/SPEC-000-mcp-fabric-aws-runtime.md`

## 1. Conectores MCP e Credenciais (Zero Segredos)
- Os servidores `fabric-mcp-server` e `aws-mcp` são declarados sem segredos em `.agents/plugins/multicloud-mcp-connectors/mcp_config.json`.
- **NÃO DEVE** existir token, chave, senha ou bloco `env` com credenciais no `mcp_config.json`, no código ou nos logs. Cada agente/usuário opera com a sessão autenticada localmente (`az login` para Entra ID e `aws login` para IAM Identity Center / SSO).
- Evite duplicação do mesmo servidor MCP em escopo global e de projeto; mantenha uma única fonte de verdade.
- **Governança de `--mode all` (Fabric):** Como `--mode all` expõe operações mutáveis (criar/apagar itens, executar jobs, alterar papéis), toda mutação via MCP exige **SPEC `APPROVED`** e confirmação explícita (enforced por hook `PreToolUse`). Operações de descoberta devem permanecer estritamente somente leitura.
- **Pinning de Versões:** Se `@latest` introduzir regressão, fixe explicitamente a versão funcional no `mcp_config.json` (ex.: `@microsoft/fabric-mcp@<versão>` ou `mcp-proxy-for-aws==<versão>`) e registre na SPEC operacional.

## 2. TLS Atrás de Proxy Corporativo (Proibição de Bypass)
- **PROIBIDO (VETO P0):** Jamais desative a verificação TLS em qualquer runtime ou script:
  - Proibido `verify=False` (Python `requests`/`httpx`/`urllib`).
  - Proibido `AZURE_CLI_DISABLE_CONNECTION_VERIFICATION`.
  - Proibido `NODE_TLS_REJECT_UNAUTHORIZED=0`.
  - Proibido `curl -k` / `--insecure`.
- **Padrão Obrigatório:** Injete a CA raiz corporativa em um bundle de CAs (CAs do sistema + CA corporativa, fora do Git) e passe-o **somente no processo** que precisa via `REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, `verify=<bundle>` ou `NODE_EXTRA_CA_CERTS`.

## 3. Restrições de Runtime (Python 3.11 / 3.12 vs. 3.13+)
- Clientes Python que acessam a **API REST e SQL Endpoints do Microsoft Fabric** (e o proxy `aws-mcp`, se necessário) **DEVEM** rodar em **Python 3.11 ou 3.12** — **NÃO DEVEM** usar **Python 3.13+**.
  - *Motivo (Earned Rule):* Python 3.13+ ativa validação estrita de X.509 (`basicConstraints` crítico), causando `CERTIFICATE_VERIFY_FAILED` em proxies corporativos cuja CA raiz não marca `basicConstraints` como crítica.
- Pelo mesmo motivo, **não utilize `az rest`** quando o Azure CLI embutir Python 3.13+: use `az` apenas para emissão de token (`AzureCliCredential`) e realize chamadas REST/SQL com Python 3.11/3.12 (`requests`, `azure-identity`, `mssql-python`).
- Se o `uvx` passar a escolher Python 3.13+ para `aws-mcp`, fixe o runtime com `uvx --python 3.12 ...`.
