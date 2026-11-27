# Regras de Escopo — SPECs (`specs/`)

- Toda SPEC ativa deve residir em `specs/active/SPEC-NNN-<slug>.md` e seguir exatamente o frontmatter YAML dos templates em `specs/templates/`.
- Nenhuma SPEC pode mudar diretamente de `DRAFT` para `EXECUTING` ou `APPROVED` sem conter evidências registradas das seções:
  1. **Parecer de Literatura & Premissas** (`literature-researcher`)
  2. **Plano Técnico & Estimativa FinOps** (`planner-architect`)
  3. **Revisão & Crítica Adversarial** (`plan-reviewer-critic`)
  4. **Veredito de Governança** (`governance-auditor`)
- Após conclusão e validação determinística (`VERIFIED`), mova a SPEC para `specs/archive/` mantendo seu histórico intacto para extração de `SKILLs` e auditoria.
