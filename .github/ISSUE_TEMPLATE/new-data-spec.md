---
name: Nova SPEC de Produto de Dados
about: Abrir uma demanda governada (Engenharia, Ciência de Dados/Estatística, Analytics/PBIP, MLOps ou Runtime)
title: "[SPEC] <domínio>: <título curto>"
labels: ["spec", "triage"]
---

## Tipo de Produto de Dados
- [ ] Engenharia de Dados (`engineering`)
- [ ] Ciência de Dados & Estatística (`science`)
- [ ] Analytics & BI / PBIP (`analytics`)
- [ ] Backend & MLOps (`mlops`)
- [ ] Plataforma / MCP Runtime (`runtime`)

## Nuvem(ns) Envolvida(s)
- [ ] Azure / Microsoft Fabric
- [ ] AWS
- [ ] Multi-Cloud (AWS + Microsoft Fabric)

## Objetivo e Critérios de Aceite
Descreva o problema de negócio, fontes de dados esperadas, contrato ODCS alvo e critérios objetivos de sucesso.

## Próximo Passo no Harness
Criar a SPEC versionada em `specs/active/` via:
```bash
uv run .agents/skills/spec-lifecycle/scripts/spec_cli.py create --type <tipo> --slug <slug> --clouds <clouds>
```
