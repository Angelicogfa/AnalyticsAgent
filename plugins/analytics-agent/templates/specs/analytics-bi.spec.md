---
spec_id: SPEC-NNN
title: "<slug-da-tarefa>"
domain: analytics-bi
status: DRAFT
clouds: "<aws | azure-fabric | multi-cloud>"
owner: analytics-bi-specialist
created_at: "<YYYY-MM-DD>"
hitl_required: true
---

# SPEC-NNN — <Título da Camada Analítica / KPI / Modelo Semântico>

## 1. Contexto e Objetivo
- **Público-Alvo e Decisão Executiva:**
- **Definição Canônica dos KPIs:**
  | KPI | Fórmula Matemática | Grão | Filtros / Exceções | Fonte Oficial |
  | :--- | :--- | :--- | :--- | :--- |
- **Critérios de Aceite:**
  - [ ] Reconciliação numérica Gold vs Silver com divergência `0%` (ou tolerância documentada).
  - [ ] Modelo dimensional Star Schema otimizado para Direct Lake (V-Order, sem fallback para DirectQuery).
  - [ ] Versionado em **`.pbip` + TMDL + PBIR** em `src/data_products/analytics/pbip/` (zero `.pbix` binário / `model.bim` legado).
  - [ ] Pré-check de performance aprovado: `pbip_precheck.py` (`0` blockers), Tabular Editor BPA (`0` errors) e perfilamento VertiPaq / DAX Studio (SE vs FE) documentado.

## 2. Escopo Multi-Cloud
- **Origem dos Dados:** (ex.: AWS S3/Iceberg via OneLake Shortcut com Cache -> Fabric Gold Lakehouse)
- **Camada Semântica & Consumo:** (ex.: Microsoft Fabric Direct Lake + Power BI / Athena SQL)
- **Governança de Acesso (Entra ID / RLS / Purview):**

## 3. Parecer de Literatura e Premissas
> *Preenchido pelo `literature-researcher` (`LITERATURE_CHECK`).*
- **Referências (Modelagem Dimensional / Definição de Métricas / Comportamento de Dados):**
- **Armadilhas Estatísticas / Analíticas a Evitar:** (ex.: Paradoxo de Simpson, média de médias, efeitos de sazonalidade/calendário)
- **Testes Diagnósticos e Reconciliação Obrigatórios:**

## 4. Plano Técnico e FinOps
> *Preenchido pelo `planner-architect` (`PLANNED`).*
- **DAG de Execução:**
- **Estimativa FinOps (Fabric CUs / Direct Lake guardrails / Athena scan):**
- **Plano de Verificação e Rollback:**

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
