---
name: literature-premise-validator
description: >-
  Protocolo estruturado de busca na web e literatura científica/técnica para fundamentar métodos estatísticos,
  modelos de ciência de dados, arquiteturas de dados e premissas de comportamento/distribuição dos dados.
  Use na fase LITERATURE_CHECK de qualquer SPEC antes de fechar o plano técnico.
---

# Skill: Literature & Statistical Premise Validator

## Objetivo
Assegurar que toda decisão analítica, estatística ou de engenharia de dados no repositório seja respaldada por referências confiáveis e acompanhada de testes diagnósticos determinísticos sobre os dados reais.

## Protocolo em 5 Passos
1. **Enquadramento do Problema e Natureza dos Dados:**
   - Identifique o tipo de processo gerador de dados: transversal (*cross-sectional*), painel/longitudinal, série temporal, sobrevivência/censurado, contagem/zero-inflated, classificação desbalanceada, experimento A/B ou pipeline transacional/CDC.
2. **Consulta Prioritária à Base Interna (`knowledge/`):**
   - Execute `uv run ${CLAUDE_PLUGIN_ROOT}/skills/internal-knowledge-base/scripts/knowledge_cli.py search --query "<termos>" --limit 5 --output ops/telemetry/kb_search.json` para incorporar dinâmicas, processos e premissas dos PDFs curados pela equipe (`KB-NNN`).
3. **Busca Complementar de Referências (Web / Literatura):**
   - Pesquise fontes primárias via `search_web` (e, quando aplicável, arXiv, EuropePMC, documentação oficial Microsoft Fabric / AWS / scikit-learn / statsmodels).
   - Registre no mínimo **2–3 referências verificáveis** (título, autor/instituição, ano, URL ou `KB-NNN` e implicação prática para a SPEC).
4. **Matriz Obrigatória de Premissas e Diagnósticos:**
   Preencha para cada premissa crítica:
   | Premissa | Tipo (Estatística / Distribuição / Operacional) | Teste Diagnóstico Determinístico | Critério de Reprovação | Plano B (Literatura) |
   | :--- | :--- | :--- | :--- | :--- |
5. **Entrega na SPEC:**
   - Insira o resumo diretamente na seção `## 3. Parecer de Literatura e Premissas` da SPEC ativa e sinalize explicitamente o que o `planner-architect` **deve** incluir como etapa obrigatória antes da modelagem/transformação final.
