# RULE-04: Evolução de SKILLs e RULES ("Earned Rules Only") (P1 — Importante)

- **Classificação:** `P1 — IMPORTANT`
- **Responsável:** `skill-curator` (com auditoria de `governance-auditor`)

## 1. Quando Extrair uma Nova `SKILL`
Uma atividade deve ser extraída para `.agents/skills/<nome-kebab-case>/` quando atender a **qualquer** critério abaixo:
1. O mesmo fluxo multi-etapa foi executado **2 ou mais vezes** (verificado em `ops/patterns/repetitive_tasks_registry.json` ou `ops/telemetry/events.jsonl`).
2. Envolve integração recorrente com API/CLI da AWS ou Microsoft Fabric que requer tratamento padronizado de paginação, retentativa ou formato de saída.
3. Há alto risco de erro humano/agêntico se feito de forma ad-hoc (ex.: validação de contrato Delta/Iceberg, checagem de premissas de séries temporais, deploy de notebook Fabric).

### Padrão Obrigatório de Skill
- `SKILL.md` enxuto com frontmatter `name` e `description` claros em terceira pessoa (Progressive Disclosure).
- Se envolver manipulação de dados, I/O ou API: encapsular em `scripts/<cli>.py` executável com `uv run`, gravando saídas extensas em arquivo e retornando status curto no `stdout`.
- Documentação densa vai em `references/`, nunca inchando o `SKILL.md`.

## 2. Quando Promover uma Nova `RULE` ("Earned Rules")
Evite *rule bloat* (regras demais diluem a atenção do modelo e consomem o orçamento de 20.000 tokens de regras do Antigravity). Promova uma nova regra apenas se:
- É uma restrição legal, de segurança, privacidade (LGPD) ou FinOps inviolável (`P0`); **OU**
- Nasceu de uma falha real observada em execução/auditoria (*post-mortem*), impedindo reincidência ("Earned Rule").

## 3. Poda Periódica
A cada ciclo de auditoria, o `skill-curator` revisa `.agents/rules/` e `AGENTS.md` locais para:
- Garantir que nenhum arquivo de regra ultrapasse **24 KB** (limite do Antigravity).
- Mover instruções procedurais longas de `RULES` para `SKILLs`.
- Arquivar regras obsoletas que não agregam proteção real.
