---
spec_id: SPEC-001
title: "exemplo-cross-cloud-churn"
domain: data-science-statistics
status: DRAFT
clouds: "multi-cloud (aws, azure-fabric)"
owner: data-scientist-statistician
created_at: "2026-11-27"
hitl_required: true
---

# SPEC-001 — Predição de Churn B2B com Feature Store Cross-Cloud (AWS S3/Iceberg → Microsoft Fabric)

> **Exemplo de Referência:** Esta SPEC demonstra como uma demanda multi-cloud real (combinando Engenharia de Dados na AWS/Fabric, Ciência de Dados/Estatística e Analytics Direct Lake) nasce padronizada pronta para o orquestrador `.agents/workflows/data_task_orchestrator.py`.

## 1. Contexto e Objetivo
- **Problema de Negócio:** Estimar a probabilidade de churn em 60 dias para clientes B2B ativos, integrando eventos de uso (AWS S3/Iceberg) com faturamento/contratos (Microsoft Fabric Lakehouse), disponibilizando escores calibrados na camada Gold para o time de CS via Power BI Direct Lake.
- **Métrica Primária:** PR-AUC e Brier Score (calibração de probabilidades) em validação estritamente *Out-of-Time* (OOT), com baseline logístico regularizado.
- **Critérios de Aceite:**
  - [ ] Consumo de eventos da AWS via **OneLake S3 Shortcut com Cache ativo** (zero cópia bruta AWS→Azure).
  - [ ] Diagnóstico estatístico executado (desbalanceamento, censura à direita, drift temporal PSI, correlação/VIF).
  - [ ] Zero *data leakage* (features calculadas estritamente até `dt_corte`, sem dados da janela de performance).
  - [ ] PII (`cnpj`, `email_contato`) removida/hash antes da camada Silver/Feature Table.

## 2. Escopo Multi-Cloud
- **AWS (Origem de Eventos):** `s3://corp-data-lake/silver/product_usage_iceberg/` (catalogado no AWS Glue, particionado por `dt_evento`). Agregação pesada mensal executada na AWS (Glue/Athena) expondo apenas a tabela agregada `silver_usage_monthly`.
- **Azure / Microsoft Fabric (Destino & Modelagem):**
  - OneLake Shortcut apontando para `silver_usage_monthly` (Shortcut Caching habilitado).
  - Join com `lakehouse_finance.silver_contracts` (Delta Lake) para gerar `gold_churn_features` e `gold_churn_scores` (V-Order habilitado para Direct Lake).
- **Janela de Observação vs Performance:** 90 dias de histórico de uso (`[t-90, t]`) para prever cancelamento confirmado em `(t, t+60]`.

## 3. Parecer de Literatura e Premissas
> *A ser preenchido pelo `literature-researcher` na execução do orquestrador (`LITERATURE_CHECK`).*
- Referências esperadas: análise de sobrevivência vs classificação binária com censura à direita, calibração de probabilidades sob desbalanceamento (Platt/Isotonic), validação temporal *rolling origin*, detecção de *covariate shift* (PSI/KS).

## 4. Plano Técnico e FinOps
> *A ser preenchido pelo `planner-architect` (`PLANNED`).*

## 5. Revisão e Crítica Adversarial
> *A ser preenchido pelo `plan-reviewer-critic` (`REVIEWED` → `CRITIQUED`).*

## 6. Auditoria de Governança
> *A ser preenchido pelo `governance-auditor` (`APPROVED` / `REJECTED`).*
- **Veredito:** `PENDING`
- **Aprovação Humana (HITL):** `[ ] Aprovado para Execução`
