---
spec_id: SPEC-NNN
title: "<slug-da-tarefa>"
domain: data-science-statistics
status: DRAFT
clouds: "<aws | azure-fabric | multi-cloud>"
owner: data-scientist-statistician
created_at: "<YYYY-MM-DD>"
hitl_required: true
---

# SPEC-NNN — <Título do Estudo Estatístico / Modelo de Ciência de Dados>

## 1. Contexto e Objetivo
- **Pergunta de Negócio / Hipótese Científica ($H_0$ vs $H_1$):**
- **Decisão que será tomada com o resultado:**
- **Métrica Primária de Sucesso & Baseline:** (ex.: PR-AUC, RMSE, Brier Score, Lift, Poder Estatístico >= 80%)
- **Critérios de Aceite:**
  - [ ] Premissas estatísticas e distribucionais verificadas empiricamente em código.
  - [ ] Zero *data leakage* comprovado (split temporal/agrupado + pipeline encapsulado).
  - [ ] Código reproduzível com seeds fixas em `src/science/` e testes passando.

## 2. Escopo Multi-Cloud
- **Fontes de Dados (AWS / Microsoft Fabric OneLake):**
- **Ambiente de Treino / Inferência:** (ex.: Fabric Spark / Notebook ou AWS SageMaker / Python local sandbox)
- **Janela de Observação vs Janela de Performance (Maturação):**
- **Colunas Sensíveis (PII / Fairness / Viés):**

## 3. Parecer de Literatura e Premissas
> *Preenchido pelo `literature-researcher` (`LITERATURE_CHECK`).*
- **Referências Científicas / Estatísticas (com citações e URLs):**
- **Premissas Estatísticas & Distribucionais:** (normalidade, estacionariedade, independência, homoscedasticidade, censura, desbalanceamento, causalidade vs correlação)
- **Premissas Operacionais dos Dados:** (atraso de registro, sobrevivência/viés de seleção, *drift*)
- **Testes Diagnósticos Obrigatórios e Plano B (se premissa falhar):**

## 4. Plano Técnico e FinOps
> *Preenchido pelo `planner-architect` (`PLANNED`).*
- **DAG de Execução (Diagnóstico → Feature Engineering → Baseline → Modelagem → Calibração → Validação OOT):**
- **Estimativa FinOps (Compute + Scan + LLM Tiering):**
- **Plano de Verificação e Rollback:**

## 5. Revisão e Crítica Adversarial
> *Preenchido pelo `plan-reviewer-critic` (`REVIEWED` → `CRITIQUED`).*
- **BLOCKERs (incluindo checagem de Data Leakage e Premissas):**
- **MAJORs:**
- **MINORs:**

## 6. Auditoria de Governança
> *Preenchido pelo `governance-auditor` (`APPROVED` / `REJECTED`).*
- **Veredito:** `PENDING`
- **Regras Verificadas (`RULES` + `policy.json`):**
- **Condições / Observações:**
- **Aprovação Humana (HITL):** `[ ] Aprovado para Execução`
