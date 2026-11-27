---
name: rule-promoter
description: >-
  Promove restrições fundamentais, obrigatórias ou lições aprendidas de falhas reais ("Earned Rules")
  para .agents/rules/ ou AGENTS.md de escopo, preservando o orçamento de 24 KB por arquivo e podando regras obsoletas.
  Use após incidentes de auditoria, vetos recorrentes ou revisão periódica de governança.
---

# Skill: Rule Promoter ("Earned Rules Only")

## Critério de Classificação
Antes de criar ou editar qualquer regra, classifique-a:
- **`P0 — MANDATORY`**: Segurança, LGPD/PII, controle de custos destrutivos, integridade de dados ou fluxo obrigatório de governança.
- **`P1 — IMPORTANT`**: Invariante operacional ou estatístico nascido de uma falha real (*post-mortem*).
- **NÃO é RULE**: Procedimento passo a passo reutilizável → use `skill-extractor` para criar uma `SKILL`.

## Procedimento
1. **Escolha o menor escopo possível (Carregamento Hierárquico):**
   - Regra global de governança → `.agents/rules/` ou `AGENTS.md` raiz.
   - Regra exclusiva de Fabric → `clouds/azure-fabric/AGENTS.md`.
   - Regra exclusiva de AWS → `clouds/aws/AGENTS.md`.
   - Regra exclusiva de código → `src/AGENTS.md`.
2. **Escreva de forma prescritiva e verificável:**
   - Inclua: **Regra**, **Motivo/Incidente de origem (SPEC-ID)** e **Como auditar** (hook determinístico em `policy.json` ou checklist do `governance-auditor`).
3. **Verifique o Orçamento de Contexto:**
   - Cada arquivo de regra DEVE ficar **abaixo de 24.000 bytes** (ideal `< 8 KB`).
   - Se uma nova regra tornar outra redundante, pode a antiga na mesma alteração.
4. **Endurecimento Determinístico:**
   - Se a regra puder ser checada mecanicamente (ex.: novo comando perigoso ou padrão de segredo), proponha também a inclusão do regex em `ops/governance/policy.json` (requer aprovação humana explícita).
