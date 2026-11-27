---
name: mlops-serving-ops
description: >-
  Padrões operacionais, segurança e FinOps para Backend de Dados/IA e MLOps Multi-Cloud
  (Microsoft Fabric MLflow / Azure Container Apps e AWS SageMaker / ECS / Lambda / Model Registry).
  Use ao planejar, revisar ou implementar APIs de inferência, empacotamento de modelos, CI/CD/CT,
  monitoramento de drift e estratégias de rollout/rollback.
---

# Skill: Backend & MLOps Serving Operations

## Checklist Arquitetural e FinOps
1. **Escolha do Padrão de Inferência (FinOps First):**
   - **Batch Scoring** (padrão preferencial quando SLA >= horas): Fabric Spark ou AWS Glue/SageMaker Batch Transform gravando na camada Gold (custo muito menor que endpoint 24/7).
   - **Serverless Inference:** AWS Lambda / SageMaker Serverless / Azure Container Apps (scale-to-zero) para tráfego intermitente ou baixo volume.
   - **Real-Time Dedicado:** Apenas quando há requisito comprovado de baixa latência contínua (p95/p99 documentado na SPEC), sempre com auto-scaling e política de *scale-down* fora de pico.
2. **Reprodutibilidade e Model Registry:**
   - Todo modelo promovido precisa de: `SPEC_ID`, versão pinada no **MLflow (Fabric)** ou **SageMaker Model Registry**, assinatura de entrada/saída (`input_example` / Pydantic schema) e lockfile determinístico de dependências.
3. **Deploy Seguro & Rollback:**
   - Adote rollout progressivo (**Shadow** → **Canary 5–10%** → **100%**) com alarmes automáticos de latência, erro 5xx e anomalia de distribuição das predições.
   - Mantenha a versão `N-1` pronta para rollback imediato.
4. **Segurança de APIs & Zero PII em Logs:**
   - Autenticação obrigatória (Microsoft Entra ID / AWS IAM / Cognito / JWT) — proibido endpoint público sem autenticação.
   - Logs estruturados de inferência devem registrar `request_id`, `model_version`, `latency_ms`, `status_code` e estatísticas agregadas — **nunca** PII em texto plano.
5. **Observabilidade de Drift & Retreinamento (CT):**
   - Monitore *feature drift* (PSI / KS) e *prediction drift* comparando produção contra a janela de referência do treino.
   - Gatilhos de retreinamento devem gerar nova execução auditada (com testes diagnósticos e validação OOT) — nunca sobrescrever produção sem gate de qualidade.
