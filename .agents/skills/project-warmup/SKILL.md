---
name: project-warmup
description: >-
  Inicializa e aquece qualquer workspace externo em uma instância do Antigravity com o Plugin Global
  AnalyticsAgent instalado (cria specs/, contracts/, knowledge/, src/data_products/ e tests/ sem copiar .agents/)
  e valida runtimes MCP/TLS/Python 3.12 em modo read-only. Use ao abrir um projeto novo ou existente sem o harness local.
---

# Skill: Project Warmup (Modo Plugin Global — Zero Cópia de `.agents/`)

## Quando Ativar
Quando o harness `analytics-agent` estiver instalado como **Plugin Global** (`~/.gemini/config/plugins/analytics-agent/`) e o usuário abrir um projeto/repositório externo que ainda não possui as pastas operacionais (`specs/`, `contracts/`, `knowledge/`, `src/data_products/`).

## Fluxo em 3 Passos
1. **Preparar a estrutura leve de trabalho (sem copiar `.agents/`):**
   ```powershell
   uvx --from git+https://github.com/<org>/AnalyticsAgent analytics-agent-warmup init-workspace --workspace .
   ```
   *(Ou, se executado localmente a partir do plugin/clone: `python scripts/warmup.py init-workspace --workspace .`)*
2. **Validar ambiente MCP, Python 3.11/3.12 e TLS (`RULE-05`):**
   - Execute `multicloud-mcp-runtime` (`verify_mcp_env.py --output ops/telemetry/mcp_env_check.json`).
3. **Abrir a primeira SPEC (`spec-lifecycle`):**
   - Crie a SPEC em `specs/active/SPEC-001-<slug>.md` a partir de `specs/templates/` e inicie o ciclo governado.

## Atualização Contínua do Plugin Global (Pull em 1 Comando)
Sempre que houver novas skills, regras ou agentes no repositório central `AnalyticsAgent`, atualize globalmente sem tocar nos seus projetos:
```powershell
uvx --from git+https://github.com/<org>/AnalyticsAgent analytics-agent-warmup install --repo-url https://github.com/<org>/AnalyticsAgent.git
```
