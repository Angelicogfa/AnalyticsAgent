---
name: adversarial-redteam-checklist
description: >-
  Protocolo estruturado de crítica adversarial (Red Team) otimizado para Gemini 4 Carbon
  (plan-reviewer-critic e governance-auditor). Audita planos técnicos quanto a blast radius multi-cloud,
  data leakage, armadilhas de FinOps (egress AWS->Fabric, CUs, Athena), violações estatísticas,
  contratos ODCS, PBIP/Direct Lake e segurança/PII antes da aprovação.
---

# Skill: Adversarial Red Team Checklist (Carbon)

## Quando Ativar
Na fase `REVIEWED -> CRITIQUED` (pelo `plan-reviewer-critic`) e na auditoria final pré-execução (`governance-auditor`) de toda SPEC.

## Matriz de Ataque Obrigatória (6 Vetores)
1. **Segurança, LGPD/PII e TLS (`RULE-00` / `RULE-05`):**
   - Algum passo expõe colunas PII sem mascaramento fora da Bronze ou imprime amostras sensíveis em logs?
   - Há risco de uso de `verify=False`, `az rest` em Python 3.13+, credenciais hardcoded ou mutação MCP sem aprovação?
2. **Armadilhas FinOps Multi-Cloud (`RULE-02`):**
   - O plano copia dados brutos da AWS para Azure em vez de usar **OneLake S3 Shortcut com Cache**?
   - Há queries sem filtro de partição (`dt_ref`) ou `SELECT *` sem limite? O relatório de `finops-cost-estimator` está dentro dos tetos de `ops/governance/policy.json`?
   - O roteamento de modelos respeita Carbon (gates), Neon (arquitetura/DS/MLOps) e Hydrogen (execução paralela)?
3. **Rigor Estatístico & Data Leakage (`RULE-03`):**
   - Existe risco de *target leakage*, *temporal leakage* (split aleatório em série temporal ou janela de performance invadindo observação) ou `.fit()` fora de pipeline?
   - Toda premissa apontada pelo `literature-researcher` (`knowledge/` + web) possui teste diagnóstico determinístico (`statistical-diagnostics-runner`) e Plano B?
4. **Resiliência & Contratos ODCS (`src/AGENTS.md`):**
   - O pipeline é 100% idempotente em reprocessamento (`MERGE` / overwrite de partição)?
   - Existe contrato `contracts/*.odcs.yaml` validado por `odcs-contract-validator`?
5. **Modelos Semânticos Power BI (`SPEC-000B`):**
   - Se envolve BI/Analytics: garante `.pbip` + TMDL + PBIR (zero `.pbix`), `pbip_precheck.py` (0 blockers), BPA/VertiPaq e prevenção de fallback DirectQuery em Direct Lake?
6. **MLOps & Rollback (`mlops-serving-ops`):**
   - Se envolve serving: justificou Batch/Serverless antes de endpoint 24/7, pinou versão no Registry e definiu rollback testável?

## Critério de Severidade
- **`BLOCKER`**: qualquer falha nos vetores 1, 3 (leakage/sem diagnóstico), 4 (não idempotente), 5 (`.pbix`/Auto DateTime) ou custo fora de teto sem aprovação humana. **Impede `APPROVED`.**
- **`MAJOR`**: risco moderado de performance, manutenção ou custo; exige mitigação ou justificativa formal na SPEC.
- **`MINOR`**: melhoria recomendada não-bloqueante.
