---
kb_id: KB-001
title: "Exemplo de Nota — Dinâmica de Validação e Premissas em Ciência de Dados"
domain: data-science
source_type: example-note
source_ref: "Exemplo inicial do harness (substitua ou complemente com seus PDFs)"
authors: "AnalyticsAgent Baseline (2026)"
tags: ["validacao", "data-leakage", "premissas", "out-of-time", "dinamica-ds"]
status: ACTIVE
candidate_for_skill: false
candidate_for_rule: false
distilled_at: "2026-11-27"
---

# KB-001 — Exemplo de Nota: Dinâmica de Validação e Premissas em Ciência de Dados

> **Nota de Exemplo:** Este arquivo ilustra o formato ideal de fichamento para que o índice SQLite FTS5 (`knowledge_cli.py`) retorne seções precisas com baixo custo de tokens. Você pode mantê-lo ou substituí-lo pelas notas destiladas dos seus próprios PDFs.

## 1. Resumo Executivo (Quando os Agentes Devem Consultar)
Aplicável a qualquer SPEC de modelagem preditiva, classificação, regressão ou scoring de clientes antes da definição do plano experimental e feature engineering.

## 2. Dinâmicas e Processos Chave
1. **Separação Estrita de Janelas (Observação vs. Performance):** Toda feature deve ser calculada exclusivamente com informações disponíveis até o instante de corte `t0`, enquanto o alvo é observado apenas em `(t0, t0 + H]`.
2. **Baseline Simples Antes de Modelos Complexos:** Sempre treinar e registrar um baseline interpretável (ex.: regressão logística/linear regularizada ou média móvel sazonal) antes de testar GBDTs ou modelos complexos, comprovando ganho real em validação *Out-of-Time* (OOT).
3. **Encapsulamento de Pré-Processamento:** Imputação, padronização, codificação de categorias e seleção de variáveis devem rodar exclusivamente dentro de pipelines ajustados no conjunto de treino de cada fold.

## 3. Premissas Estatísticas, Comportamentais e Operacionais
| Premissa / Restrição | Contexto de Aplicação | Teste / Verificação Recomendada | Ação se Violada | Referência |
| :--- | :--- | :--- | :--- | :--- |
| Estabilidade temporal das features | Dados longitudinais / scoring recorrente | PSI (Population Stability Index) e KS entre treino e OOT | Remover/transformar features instáveis ou recalibrar janela | Exemplo §3 |
| Calibração de probabilidades | Decisões baseadas em escore/limiar de risco | Brier Score e curva de calibração (ECE) | Aplicar Platt Scaling ou Isotonic Regression em conjunto de calibração separado | Exemplo §3 |

## 4. Antipadrões e Armadilhas a Evitar
- **Random Split em Dados Temporais:** Gera estimativas artificialmente otimistas por vazamento de futuro para passado.
- **Avaliação Única por ROC-AUC em Classes Muito Desbalanceadas:** Sempre reportar PR-AUC, Lift nos decis superiores e calibração.
