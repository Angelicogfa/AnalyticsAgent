# Política de Segurança (`SECURITY.md`)

## Princípios de Segurança do Harness
Este template implementa defesa em profundidade para operações agênticas de dados:
- **Zero Credenciais Versionadas:** Conexões com Microsoft Fabric, AWS e Power BI Desktop usam exclusivamente autenticação local do usuário (`az login`, `aws login`) e gerenciadores de segredos em nuvem (Azure Key Vault / AWS Secrets Manager).
- **Zero Bypass de TLS (`RULE-05`):** É estritamente proibido desabilitar validação TLS (`verify=False`, `NODE_TLS_REJECT_UNAUTHORIZED=0`, `AZURE_CLI_DISABLE_CONNECTION_VERIFICATION`, `curl -k`).
- **Guardrails Determinísticos:** O hook `PreToolUse` (`.agents/hooks/security_finops_gate.py`) bloqueia comandos destrutivos, vazamento de chaves/tokens, bypass de TLS e mutações MCP sem aprovação.
- **Proteção de PII (LGPD):** Datasets reais com dados pessoais nunca devem ser commitados no Git, gravados em `knowledge/` ou impressos em logs/prompts.

## Reportando Vulnerabilidades
Caso identifique uma falha de segurança, bypass de hook ou exposição acidental:
1. **Não** abra uma issue pública expondo detalhes exploráveis.
2. Reporte diretamente aos mantenedores do repositório (via GitHub Security Advisories ou canal privado definido na instância do template).
3. Após correção, promova a lição aprendida como uma *Earned Rule* e adicione um teste de regressão determinístico em `tests/test_harness_integrity.py`.
