# RULE-01: Ciclo Obrigatório Planejar → Revisar → Criticar → Auditar → Executar (P0 — Obrigatório)

- **Classificação:** `P0 — MANDATORY`
- **Responsável pela Orquestração:** `orchestrator` / `governance-auditor`

## 1. Fluxo Obrigatório (Proibido Pular Etapas)
Para qualquer tarefa não-trivial de dados (pipeline, modelo, análise estatística, dashboard/semântica):

1. **SPEC (`DRAFT`):** Estruturar objetivo, fontes, contrato de dados, nuvem-alvo (Fabric/AWS), critérios de aceite e orçamento FinOps.
2. **Validação de Literatura (`LITERATURE_CHECK`):** Acionar `literature-researcher` para levantar referências teóricas/técnicas, premissas estatísticas/operacionais e testes diagnósticos obrigatórios.
3. **Planejamento (`PLANNED`):** Acionar `planner-architect` para desenhar o plano técnico em DAG (etapas, dependências, estimativa de custo de nuvem e tokens, plano de rollback e testes).
4. **Revisão Técnica (`REVIEWED`):** Verificar completude, aderência à SPEC, coerência multi-cloud (evitar movimentação desnecessária de dados entre AWS e Azure) e clareza dos critérios de aceite.
5. **Crítica Adversarial (`CRITIQUED`):** Acionar `plan-reviewer-critic` em modo *Red Team* para atacar ativamente o plano: buscar vazamento de dados (data leakage), violações de premissas estatísticas, gargalos de egress/scan, edge cases (nulos, dados tardios, schema drift) e falhas de idempotência.
6. **Auditoria e Gate de Governança (`APPROVED`):** Acionar `governance-auditor` para emitir veredito estruturado (`APPROVED`, `APPROVED_WITH_CONDITIONS` ou `REJECTED`).
   - Se `REJECTED`, retorna ao `planner-architect` (máximo **3 ciclos**; após isso, escalar ao humano).
7. **Execução Controlada (`EXECUTING`):** Somente após `APPROVED`, delegar para o(s) agente(s) executor(es) (`data-engineer`, `data-scientist-statistician`, `analytics-bi-specialist`, `backend-mlops-specialist`).
8. **Verificação Determinística (`VERIFIED`):** Executar testes unitários, validações de contrato de dados, diagnósticos estatísticos e checagem de custos reais.
9. **Encerramento e Curadoria (`COMPLETED`):** `governance-auditor` consolida métricas da execução e `skill-curator` avalia se há tarefa repetitiva a extrair como `SKILL` ou lição aprendida a promover como `RULE`.

## 2. Exceção de Baixa Complexidade (Fast-Path)
Perguntas puramente conceituais ou consultas read-only de inspeção simples que não modificam código, dados ou infraestrutura não exigem ciclo completo, mas continuam sujeitas às regras P0 de segurança e privacidade.

## 3. Hierarquia Máxima de 2 Níveis (Manager → Sub-Operadores Leaf)
- Os 4 agentes principais de domínio (`data-scientist-statistician`, `data-engineer`, `analytics-bi-specialist`, `backend-mlops-specialist`) atuam como **Domain Managers** podendo delegar subtarefas granulares aos seus **sub-operadores folha** (`ds-*`, `de-*`, `bi-*`, `mlops-*`).
- **Profundidade máxima = 2 níveis** (`Orchestrator → Domain Manager → Sub-Operador Leaf`). Sub-operadores **nunca** podem instanciar novos sub-agentes (`can_spawn_subagents: false`) nem se comunicar peer-to-peer entre si.
- **Delegação Sob Demanda (*Lazy Delegation*):** Acione apenas os sub-operadores estritamente necessários para a SPEC aprovada, trocando artefatos estruturados (JSON/arquivos) em vez de transcrições extensas.
