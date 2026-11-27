---
name: skill-extractor
description: >-
  Extrai tarefas repetitivas executadas pelos agentes (>= 2 ocorrências) em novas SKILLs padronizadas
  em .agents/skills/<nome>/ com divulgação progressiva e scripts CLI opcionais.
  Use ao concluir uma SPEC recorrente ou quando o skill-curator/governance-auditor sinalizar um padrão repetitivo.
---

# Skill: Skill Extractor (Destilação de Tarefas Repetitivas)

## Quando Ativar
- Uma sequência operacional ocorreu **2 ou mais vezes** em SPECs distintas ou na telemetria (`ops/telemetry/events.jsonl`).
- O registro `ops/patterns/repetitive_tasks_registry.json` possui um item com `occurrences >= 2` e `extractedSkill: null`.

## Procedimento Padronizado
1. **Avaliar se exige código determinístico:**
   - Se a tarefa chama APIs (Fabric REST, AWS boto3/CLI), valida schemas, manipula dados ou processa arquivos → gere a skill com `--with-script` (padrão CLI com saída em arquivo).
   - Se é puramente protocolo de raciocínio/coordenação → gere sem script.
2. **Gerar o esqueleto validado da nova SKILL:**
   ```powershell
   uv run .agents/skills/skill-extractor/scripts/scaffold_skill.py --name <nome-kebab-case> --description "<Quando usar em terceira pessoa>" --with-script --pattern-id PAT-001
   ```
3. **Preencher instruções enxutas (`SKILL.md`):**
   - Mantenha `SKILL.md` conciso; coloque documentação longa em `references/`.
   - Documente critérios explícitos de validação (como provar que a skill teve sucesso) e 2–3 erros comuns.
4. **Registrar e Validar:**
   - Confirme que `ops/patterns/repetitive_tasks_registry.json` foi atualizado com `extractedSkill: "<nome>"`.
   - Teste o script CLI gerado com `--help` e um caso mínimo em sandbox.
