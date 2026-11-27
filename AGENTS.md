# AnalyticsAgent — Operador Agêntico Multi-Cloud de Dados (Regras Raiz P0)

Este repositório implementa um **Harness Agêntico de Dados** nativo para **Google Antigravity**, cobrindo Engenharia de Dados, Ciência de Dados, Estatística e Analytics em ambientes **Azure (Microsoft Fabric)** e **AWS**.

> **Princípio de Arquitetura:** Código, queries, notebooks e modelos são artefatos compilados a partir de **SPECs** aprovadas. Nenhuma execução relevante ocorre sem passar pelo ciclo governado.

---

## 1. Regras Invioláveis (P0 — Mandatory)

1. **Spec-First (Obrigatório):** Toda demanda operacional ou analítica nasce como uma SPEC em `specs/active/SPEC-NNN-<slug>.md` usando os templates de `specs/templates/`. Sem SPEC com status `APPROVED`, nenhuma escrita em produção ou nuvem é permitida.
2. **Ciclo Obrigatório de Planejamento e Crítica:** Toda SPEC deve seguir a máquina de estados:
   `DRAFT → LITERATURE_CHECK → PLANNED → REVIEWED → CRITIQUED → APPROVED → EXECUTING → VERIFIED → COMPLETED`
   - Nenhum agente executor pode escrever código produtivo antes de o plano ser **criado**, **revisado**, **criticado adversarialmente** e **aprovado pelo `governance-auditor`**.
3. **Poder de Veto de Governança e Segurança:** O agente `governance-auditor` e os hooks determinísticos em `.agents/hooks.json` possuem autoridade de **VETO** absoluto sobre qualquer ação que viole segurança, privacidade (LGPD/PII), orçamento FinOps ou regras P0. Nunca tente contornar um bloqueio de hook ou sandbox.
4. **Rigor Científico e Estatístico:** Toda modelagem, inferência, teste A/B, série temporal ou pipeline com regra de negócio sensível exige parecer prévio do `literature-researcher` validando premissas estatísticas, distribucionais e operacionais com referências verificáveis, seguido de **testes diagnósticos determinísticos** em código sobre os dados reais.
5. **Determinismo sobre Probabilidade:** Nunca faça cálculos estatísticos, agregações, validações de schema ou estimativas de volumetria "de cabeça" no LLM. Delegue sempre para scripts Python/SQL determinísticos executados em sandbox.
6. **Zero Credenciais e Zero PII em Texto Plano:** Jamais grave segredos, tokens, connection strings, SAS tokens, chaves AWS ou dados pessoais identificáveis (CPF, e-mail, telefone, nomes reais) no repositório, em logs ou em prompts.
7. **Otimização de Custos e Capacidade (LLM + Cloud FinOps):**
   - **LLM Tiering:** Use `flash_lite`/`flash` para descoberta, coleta, formatação e checagens mecânicas; reserve `pro` para arquitetura, crítica adversarial, auditoria e rigor estatístico.
   - **Cloud FinOps:** Respeite limites de scan (Athena/Spark), particionamento obrigatório, cache em OneLake Shortcuts S3 (evitar egress AWS→Azure) e agendamento fora de pico nas Fabric Capacities (CUs).
8. **Circuit Breaker (Anti-Loop):** Limite máximo de **3 iterações** de revisão/correção por fase ou erro de execução. Atingido o limite, interrompa e escale ao humano com diagnóstico estruturado.

---

## 2. Evolução Contínua do Conhecimento

- **Tarefa Repetitiva → `SKILL`:** Qualquer procedimento executado **2 ou mais vezes** (ou identificado como recorrente na telemetria em `ops/telemetry/events.jsonl`) deve ser registrado em `ops/patterns/repetitive_tasks_registry.json` e extraído pelo `skill-curator` via skill `skill-extractor` para `.agents/skills/<nome>/`.
- **Invariante / Lição Aprendida → `RULE`:** Apenas regras **fundamentais, obrigatórias ou originadas de falhas concretas ("Earned Rules")** devem ser promovidas para `.agents/rules/` ou `AGENTS.md` via skill `rule-promoter`. Pode regras obsoletas para manter o orçamento de contexto enxuto (`< 24 KB` por arquivo).

---

## 3. Mapa Rápido do Harness

| Camada | Caminho | Responsabilidade |
| :--- | :--- | :--- |
| **Regras P0/P1** | `.agents/rules/` + `AGENTS.md` locais | Restrições obrigatórias (carregamento hierárquico por contexto) |
| **Agentes (N)** | `.agents/agents/` | Papéis especializados cooperativos (topologia Hub-and-Spoke) |
| **Skills** | `.agents/skills/` | Procedimentos reutilizáveis com divulgação progressiva |
| **Workflows** | `.agents/workflows/` | Orquestração Python determinística via `run_workflow` |
| **Hooks** | `.agents/hooks.json` + `.agents/hooks/` | Guardrails determinísticos (`PreToolUse`) e telemetria (`PostToolUse`) |
| **SPECs** | `specs/` | Contratos de trabalho versionados (Engenharia, Ciência, Analytics) |
| **Multi-Cloud** | `clouds/azure-fabric/` e `clouds/aws/` | Regras e padrões específicos de Microsoft Fabric e AWS |
| **Operações** | `ops/` | Telemetria JSONL, políticas declarativas (`policy.json`) e registro de padrões |
| **Código** | `src/` | Artefatos implementados e validados a partir das SPECs |
