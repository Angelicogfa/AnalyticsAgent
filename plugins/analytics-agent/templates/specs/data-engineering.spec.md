---
spec_id: SPEC-NNN
title: "<slug-da-tarefa>"
domain: data-engineering
status: DRAFT
clouds: "<aws | azure-fabric | multi-cloud>"
owner: data-engineer
created_at: "<YYYY-MM-DD>"
hitl_required: true
---

# SPEC-NNN — <Título do Pipeline / Engenharia de Dados>

## 1. Contexto e Objetivo
- **Problema de Negócio / Operacional:** Descreva o objetivo e o consumidor final.
- **Critérios de Aceite (Objetivos):**
  - [ ] Contrato de schema validado sem violações.
  - [ ] Pipeline 100% idempotente em reprocessamento.
  - [ ] PII mascarada/tokenizada na saída da camada Bronze.
  - [ ] Testes determinísticos passando em sandbox.

## 2. Escopo Multi-Cloud
- **Origem(ns):** (ex.: AWS S3 `s3://bucket/bronze/...`, Glue Catalog, API)
- **Destino(s):** (ex.: Microsoft Fabric OneLake Lakehouse Silver/Gold via S3 Shortcut ou Delta Table)
- **Estratégia Cross-Cloud & Egress:** (ex.: processar pesado na AWS e expor Silver/Gold via OneLake Shortcut com Cache ativo)
- **Contrato de Dados & SLA:**
  - Formato aberto: `Delta Lake` / `Apache Iceberg`
  - Chave primária / grão: `<colunas>`
  - Coluna de partição: `<ex: dt_ref>`
  - Tratamento de dados tardios (*late-arriving data*) e *schema drift*: `<estratégia>`
  - Colunas PII identificadas e mascaramento: `<nenhuma | lista + método>`

## 3. Parecer de Literatura e Premissas
> *Preenchido pelo `literature-researcher` (`LITERATURE_CHECK`).*
- **Referências Técnicas:**
- **Premissas Operacionais e Comportamentais dos Dados:**
- **Testes Diagnósticos Obrigatórios:**

## 4. Plano Técnico e FinOps
> *Preenchido pelo `planner-architect` (`PLANNED`).*
- **DAG de Execução (Tarefas, Agente Executor, Model Tier):**
- **Estimativa FinOps (AWS Athena/Glue/Egress + Fabric CUs + LLM Tiering):**
- **Plano de Testes em Sandbox e Rollback:**

## 5. Revisão e Crítica Adversarial
> *Preenchido pelo `plan-reviewer-critic` (`REVIEWED` → `CRITIQUED`).*
- **BLOCKERs:**
- **MAJORs:**
- **MINORs:**

## 6. Auditoria de Governança
> *Preenchido pelo `governance-auditor` (`APPROVED` / `REJECTED`).*
- **Veredito:** `PENDING`
- **Regras Verificadas (`RULES` + `policy.json`):**
- **Condições / Observações:**
- **Aprovação Humana (HITL):** `[ ] Aprovado para Execução`
