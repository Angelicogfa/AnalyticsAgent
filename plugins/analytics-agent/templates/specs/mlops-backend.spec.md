---
spec_id: SPEC-NNN
title: "<slug-da-tarefa>"
domain: backend-mlops
status: DRAFT
clouds: "<aws | azure-fabric | multi-cloud>"
owner: backend-mlops-specialist
created_at: "<YYYY-MM-DD>"
hitl_required: true
---

# SPEC-NNN — <Título do Serviço Backend / Pipeline MLOps>

## 1. Contexto e Objetivo
- **Modelo / Serviço a Operacionalizar:** (referencie `SPEC` de Ciência de Dados/Engenharia de origem, se houver)
- **Padrão de Inferência & SLA:** `Batch` | `Serverless` | `Real-Time` — Latência alvo (p95), throughput (RPS) e disponibilidade.
- **Critérios de Aceite:**
  - [ ] Contrato OpenAPI / Pydantic validado com testes determinísticos em sandbox.
  - [ ] Artefato versionado no Model Registry (Fabric MLflow / AWS SageMaker) com linhagem completa.
  - [ ] Estratégia de rollout seguro (`Shadow`/`Canary`) e rollback para versão `Champion` documentados e testados.
  - [ ] Zero PII em logs de inferência, métricas e traces.

## 2. Escopo Multi-Cloud
- **Origem das Features / Artefatos:** (ex.: Fabric OneLake Gold / MLflow Registry ou AWS S3/ECR/SageMaker Registry)
- **Alvo de Deploy & Runtime:** (ex.: AWS SageMaker Serverless/ECS/Lambda ou Fabric Batch Scoring / Azure Container Apps)
- **Segurança & Autenticação:** (IAM Role least privilege, Entra ID / OAuth2, criptografia TLS/KMS, isolamento de rede)
- **Monitoramento (SLO & Drift):** Latência, taxa de erro, *data drift* (PSI/KS) e gatilho de retreinamento (CT).

## 3. Parecer de Literatura e Premissas
> *Preenchido pelo `literature-researcher` (`LITERATURE_CHECK`).*
- **Referências Técnicas (MLOps, Drift Detection, Serving Architecture):**
- **Premissas Operacionais (Tráfego, Sazonalidade, Janela de Retreinamento, Latência):**
- **Testes Diagnósticos / Carga Obrigatórios:**

## 4. Plano Técnico e FinOps
> *Preenchido pelo `planner-architect` (`PLANNED`).*
- **DAG de Execução (Empacotamento → API/Batch → Testes de Contrato → Observabilidade → Rollout):**
- **Estimativa FinOps (Batch vs Serverless vs Endpoint 24/7 + Egress + LLM Tiering):**
- **Plano de Rollback (Reversão para `Champion`):**

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
