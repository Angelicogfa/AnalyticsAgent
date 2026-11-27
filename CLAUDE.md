# AnalyticsAgent — Ponte para o Claude Code

Este arquivo apenas conecta o Claude Code à fonte única de verdade do harness (`AGENTS.md` + `.agents/`).
Não duplique regras aqui: edite `AGENTS.md` / `.agents/rules/` e rode `uv run scripts/warmup.py sync-claude`.

@AGENTS.md
@.agents/rules/00-governance-and-security.md
@.agents/rules/01-plan-review-critique-loop.md
@.agents/rules/02-finops-and-cost-tiering.md
@.agents/rules/03-statistical-and-data-rigor.md
@.agents/rules/04-skill-and-rule-evolution.md
@.agents/rules/05-mcp-auth-and-tls-runtime.md

## Tradução de Harness (Antigravity → Claude Code)

| Termo nas regras/agentes (Antigravity) | Equivalente no Claude Code |
| :--- | :--- |
| `run_workflow` + `.agents/workflows/data_task_orchestrator.py` | `python .claude/workflows/run_spec_cycle.py --spec <SPEC>` (executa o mesmo orquestrador) |
| Tier `flash_lite` / `flash` / `pro` | `haiku` / `sonnet` / `opus` (ver `.claude/model_map.json`) |
| Gemini 4 `Hydrogen` / `Neon` / `Carbon` | `haiku` / `sonnet` / `opus` |
| `invoke_subagent` / `/swarm` | Ferramenta `Agent` com os subagentes de `.claude/agents/` |
| `run_command` / `write_file` / `edit_file` / `call_mcp_tool` | `Bash` ou `PowerShell` / `Write` / `Edit` / `mcp__<servidor>__<ferramenta>` |
| `.agents/hooks.json` | `.claude/settings.json` (adaptadores em `.claude/hooks/` reutilizam `.agents/hooks/`) |
| `.agents/skills/` | `.claude/skills/` (gerado; scripts continuam em `.agents/skills/<skill>/scripts/`) |
| `.agents/plugins/multicloud-mcp-connectors/mcp_config.json` | `.mcp.json` (gerado) |

Arquivos em `.claude/skills/`, `.claude/agents/` e `.mcp.json` são **gerados** — não edite manualmente.
