---
spec_id: SPEC-NNN
title: "<slug-da-integracao-runtime>"
domain: platform-runtime
status: DRAFT
clouds: "<aws | azure-fabric | multi-cloud>"
owner: data-engineer
created_at: "<YYYY-MM-DD>"
hitl_required: true
---

# SPEC-NNN — <Título da Integração MCP / Runtime / Conectividade>

## 1. Contexto e Objetivo
- **Serviços/MCPs Integrados:**
- **Escopo de Estação / Ambiente:** (Windows/Linux, proxy TLS corporativo, fora de escopo)
- **Critérios de Aceite (Somente Leitura):**
  - [ ] Autenticação via credencial local do usuário sem segredos em arquivo.
  - [ ] Verificação TLS intacta com CA corporativa confiável (zero bypass).
  - [ ] Probe de conectividade dos MCPs e runtimes validado e documentado.

## 2. Escopo Multi-Cloud
- **Arquitetura de Comunicação (Stdio / Streamable HTTP / REST / TDS):**
- **Requisitos de Runtime e Versões Verificadas:** (Node, uv/uvx, Python 3.11/3.12, CLIs, drivers)
- **Configuração MCP (sem segredos) e Escopo de Ferramentas (`read-only` vs `all`):**

## 3. Parecer de Literatura e Premissas
> *Preenchido pelo `literature-researcher` (`LITERATURE_CHECK`).*
- **Referências Oficiais (MCP / Cloud SDKs / TLS / X.509):**
- **Premissas Operacionais (Expiração de Token, Sincronização de Metadados, Proxy):**

## 4. Plano Técnico e FinOps
> *Preenchido pelo `planner-architect` (`PLANNED`).*
- **Problemas Conhecidos e Decisões de Mitigação:**
- **Checklist de Verificação Read-Only:**

## 5. Revisão e Crítica Adversarial
> *Preenchido pelo `plan-reviewer-critic` (`REVIEWED` → `CRITIQUED`).*
- **BLOCKERs (TLS bypass, segredos em config, duplicação de MCPs, escopo excessivo):**
- **MAJORs:**
- **MINORs:**

## 6. Auditoria de Governança
> *Preenchido pelo `governance-auditor` (`APPROVED` / `REJECTED`).*
- **Veredito:** `PENDING`
- **Regras Verificadas (`RULE-05` + `policy.json`):**
- **Aprovação Humana (HITL):** `[ ] Aprovado para Execução`
