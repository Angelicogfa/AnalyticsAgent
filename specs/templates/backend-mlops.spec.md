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
- **Serviço / Produto de Dados ou ML:** Descreva o modelo ou capability a ser produtizada.
- **Padrão de Inferência & SLA:** `Batch` | `Serverless` | `Real-Time` (especificar latência alvo p95/p99, throughput esperado e disponibilidade).
- **Contrato de API / Payload:** (schema de entrada/saída, versionamento de contrato, códigos de erro).
- **Critérios de Aceite:**
  - [ ] Modelo/artefato registrado com versão imutável e assinatura validada (MLflow / SageMaker Model Registry).
  - [ ] Testes automatizados de contrato, inferência e tratamento de erro passando em sandbox.
  - [ ] Autenticação configurada e zero PII em logs de aplicação/inferência.
  - [ ] Estratégia de rollout seguro (Shadow/Canary/Blue-Green) e rollback testada.

## 2. Escopo Multi-Cloud
- **Origem do Modelo & Features:** (ex.: Fabric OneLake Gold / MLflow Registry / AWS S3 Iceberg)
- **Infraestrutura de Serving & CI/CD:** (ex.: AWS SageMaker/ECS/Lambda/ECR ou Azure Container Apps/Fabric Batch)
- **Monitoramento & Gatilhos de Drift/CT:** (métricas de latência, erro 5xx, PSI/KS de features/predições e política de retreinamento).
- **Segurança & Rede:** (IAM Role / Entra ID, VPC/PrivateLink, gestão de segredos via Key Vault / Secrets Manager).

## 3. Parecer de Literatura e Premissas
> *Preenchido pelo `literature-researcher` (`LITERATURE_CHECK`).*
- **Referências Técnicas (MLOps, Drift Detection, Serving Architecture):**
- **Premissas Operacionais e de Comportamento em Produção:** (latência de features online vs offline — *training-serving skew*, sazonalidade de tráfego, degradação de calibração)
- **Testes Diagnósticos e Checks de Pré-Deploy Obrigatórios:**

## 4. Plano Técnico e FinOps
> *Preenchido pelo `planner-architect` (`PLANNED`).*
- **DAG de Execução (Empacotamento → API/Batch → Testes de Contrato/Carga → Observabilidade → Rollout):**
- **Estimativa FinOps (Compute/Endpoints/Auto-scaling + Egress + LLM Tiering):**
- **Plano de Rollout Progressivo e Rollback:**

## 5. Revisão e Crítica Adversarial
> *Preenchido pelo `plan-reviewer-critic` (`REVIEWED` → `CRITIQUED`).*
- **BLOCKERs (training-serving skew, auth, PII em logs, endpoint ocioso caro, ausência de rollback):**
- **MAJORs:**
- **MINORs:**

## 6. Auditoria de Governança
> *Preenchido pelo `governance-auditor` (`APPROVED` / `REJECTED`).*
- **Veredito:** `PENDING`
- **Regras Verificadas (`RULES` + `policy.json`):**
- **Condições / Observações:**
- **Aprovação Humana (HITL):** `[ ] Aprovado para Execução`
