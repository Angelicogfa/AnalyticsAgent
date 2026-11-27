"""Orquestrador Multi-Agente Nativo para Google Antigravity (`run_workflow`).

Executa o ciclo governado:
  SPEC -> Literature Check -> [Plan -> Review & Critique -> Governance Audit (VETO)] (max 3x)
       -> (opcional HITL gate) -> Execution -> Deterministic Verification -> Skill/Rule Curation

Uso via ferramenta `run_workflow`:
  run_workflow(
      ScriptPath="<workspace>/.agents/workflows/data_task_orchestrator.py",
      Args={"spec_path": "specs/active/SPEC-001-exemplo-cross-cloud-churn.md", "execute": False},
      Description="Executar ciclo governado da SPEC-001"
  )
"""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Parâmetros e leitura inicial da SPEC
# ---------------------------------------------------------------------------
spec_rel = args["spec_path"]
should_execute = bool(args.get("execute", False))
max_cycles = min(int(args.get("max_plan_cycles", 3)), 3)

workspace_root = Path(WORKSPACES[0]) if WORKSPACES else Path.cwd()
spec_file = (workspace_root / spec_rel) if not Path(spec_rel).is_absolute() else Path(spec_rel)

if not spec_file.exists():
    raise FileNotFoundError(f"SPEC não encontrada: {spec_file}")

spec_content = spec_file.read_text(encoding="utf-8")
policy_file = workspace_root / "ops" / "governance" / "policy.json"
policy_text = policy_file.read_text(encoding="utf-8") if policy_file.exists() else "{}"

AGENT_ROLE_PATHS = {
    "orchestrator": ".agents/agents/core/orchestrator.md",
    "literature-researcher": ".agents/agents/core/literature-researcher.md",
    "planner-architect": ".agents/agents/core/planner-architect.md",
    "plan-reviewer-critic": ".agents/agents/core/plan-reviewer-critic.md",
    "governance-auditor": ".agents/agents/core/governance-auditor.md",
    "skill-curator": ".agents/agents/core/skill-curator.md",
    "data-engineer": ".agents/agents/data-engineering/data-engineer.md",
    "data-scientist-statistician": ".agents/agents/data-science/data-scientist-statistician.md",
    "analytics-bi-specialist": ".agents/agents/analytics-bi/analytics-bi-specialist.md",
    "backend-mlops-specialist": ".agents/agents/backend-mlops/backend-mlops-specialist.md",
}

phase("0. Bootstrap da SPEC")
log(f"SPEC carregada: {spec_file.name} | execute={should_execute} | max_cycles={max_cycles}")

# ---------------------------------------------------------------------------
# Fase 1: Pesquisa de Literatura & Premissas Estatísticas/Operacionais (flash)
# ---------------------------------------------------------------------------
phase("1. Validação de Literatura e Premissas")

literature_schema = {
    "type": "object",
    "required": [
        "domain",
        "references",
        "statistical_premises",
        "operational_premises",
        "mandatory_diagnostic_tests",
        "fallback_methods",
    ],
    "properties": {
        "domain": {"type": "string"},
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "source", "relevance"],
                "properties": {
                    "title": {"type": "string"},
                    "source": {"type": "string"},
                    "url": {"type": "string"},
                    "relevance": {"type": "string"},
                },
            },
        },
        "statistical_premises": {"type": "array", "items": {"type": "string"}},
        "operational_premises": {"type": "array", "items": {"type": "string"}},
        "mandatory_diagnostic_tests": {"type": "array", "items": {"type": "string"}},
        "fallback_methods": {"type": "array", "items": {"type": "string"}},
    },
}

literature_brief = await agent(
    prompt=(
        f"Atue conforme `{AGENT_ROLE_PATHS['literature-researcher']}` e as skills "
        "`.agents/skills/internal-knowledge-base/SKILL.md` e "
        "`.agents/skills/literature-premise-validator/SKILL.md`.\n"
        "PRIMEIRO consulte a base interna `knowledge/` via `knowledge_cli.py search` (citando `KB-NNN`) "
        "para incorporar dinâmicas e processos dos PDFs da equipe; DEPOIS complemente na web/literatura.\n"
        "Levante premissas estatísticas, comportamentais, distribucionais e operacionais dos dados, "
        "os testes diagnósticos determinísticos obrigatórios e métodos alternativos caso alguma premissa falhe.\n\n"
        f"--- SPEC ({spec_file.name}) ---\n{spec_content}"
    ),
    schema=literature_schema,
    role="Literature Researcher",
    model="flash",
)
log(
    f"Literatura concluída: {len(literature_brief['references'])} referências, "
    f"{len(literature_brief['mandatory_diagnostic_tests'])} testes diagnósticos obrigatórios."
)

# ---------------------------------------------------------------------------
# Fase 2: Ciclo Planejar -> Revisar -> Criticar -> Auditar (Circuit Breaker <= 3)
# ---------------------------------------------------------------------------
phase("2. Planejamento, Revisão, Crítica Adversarial e Auditoria")

plan_schema = {
    "type": "object",
    "required": [
        "summary",
        "clouds_involved",
        "finops_estimate",
        "tasks",
        "verification_plan",
        "rollback_plan",
    ],
    "properties": {
        "summary": {"type": "string"},
        "clouds_involved": {"type": "array", "items": {"type": "string"}},
        "finops_estimate": {
            "type": "object",
            "required": ["cloud_cost_controls", "llm_model_tiering"],
            "properties": {
                "cloud_cost_controls": {"type": "array", "items": {"type": "string"}},
                "llm_model_tiering": {"type": "string"},
            },
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "executor_role", "model_tier", "title", "deliverables", "acceptance_test"],
                "properties": {
                    "id": {"type": "string"},
                    "executor_role": {
                        "type": "string",
                        "enum": [
                            "data-engineer",
                            "data-scientist-statistician",
                            "analytics-bi-specialist",
                            "backend-mlops-specialist",
                        ],
                    },
                    "model_tier": {"type": "string", "enum": ["flash_lite", "flash", "pro"]},
                    "subagents_to_invoke": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sub-operadores leaf opcionais (ds-*, de-*, bi-*, mlops-*) necessários sob demanda para esta tarefa.",
                    },
                    "title": {"type": "string"},
                    "deliverables": {"type": "array", "items": {"type": "string"}},
                    "acceptance_test": {"type": "string"},
                },
            },
        },
        "verification_plan": {"type": "array", "items": {"type": "string"}},
        "rollback_plan": {"type": "string"},
    },
}

critique_schema = {
    "type": "object",
    "required": ["review_summary", "blockers", "majors", "minors", "ready_for_governance"],
    "properties": {
        "review_summary": {"type": "string"},
        "blockers": {"type": "array", "items": {"type": "string"}},
        "majors": {"type": "array", "items": {"type": "string"}},
        "minors": {"type": "array", "items": {"type": "string"}},
        "ready_for_governance": {"type": "boolean"},
    },
}

audit_schema = {
    "type": "object",
    "required": ["verdict", "rules_checked", "violations", "conditions", "rationale"],
    "properties": {
        "verdict": {"type": "string", "enum": ["APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED"]},
        "rules_checked": {"type": "array", "items": {"type": "string"}},
        "violations": {"type": "array", "items": {"type": "string"}},
        "conditions": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
}

feedback_history = []
current_plan = None
last_critique = None
last_audit = None

for cycle in range(1, max_cycles + 1):
    log(f"--- Ciclo de Planejamento {cycle}/{max_cycles} ---")

    feedback_block = (
        f"\nFeedback acumulado dos ciclos anteriores (resolva TODOS os blockers/violações):\n"
        f"{json.dumps(feedback_history, ensure_ascii=False, indent=2)}"
        if feedback_history
        else ""
    )

    current_plan = await agent(
        prompt=(
            f"Atue conforme `{AGENT_ROLE_PATHS['planner-architect']}` e as regras em `AGENTS.md`, "
            "`.agents/rules/`, `clouds/azure-fabric/AGENTS.md` e `clouds/aws/AGENTS.md`.\n"
            "Elabore um plano técnico em DAG otimizado em custos (FinOps Cloud + LLM Tiering) "
            "incorporando os testes diagnósticos exigidos pela literatura.\n\n"
            f"--- SPEC ---\n{spec_content}\n\n"
            f"--- PARECER DE LITERATURA ---\n{json.dumps(literature_brief, ensure_ascii=False, indent=2)}"
            f"{feedback_block}"
        ),
        schema=plan_schema,
        role=f"Planner Architect (Ciclo {cycle})",
        model="pro",
    )

    last_critique = await agent(
        prompt=(
            f"Atue conforme `{AGENT_ROLE_PATHS['plan-reviewer-critic']}` em modo Revisão Técnica + Red Team.\n"
            "Critique impiedosamente o plano abaixo procurando: falhas de aderência à SPEC, "
            "armadilhas de egress AWS->Fabric, falta de filtros de partição, sobrecarga de CUs Fabric, "
            "data leakage, premissas estatísticas sem teste diagnóstico, falta de idempotência ou vazamento de PII.\n\n"
            f"--- SPEC ---\n{spec_content}\n\n"
            f"--- LITERATURA ---\n{json.dumps(literature_brief, ensure_ascii=False, indent=2)}\n\n"
            f"--- PLANO PROPOSTO ---\n{json.dumps(current_plan, ensure_ascii=False, indent=2)}"
        ),
        schema=critique_schema,
        role=f"Plan Reviewer & Critic (Ciclo {cycle})",
        model="pro",
    )

    last_audit = await agent(
        prompt=(
            f"Atue conforme `{AGENT_ROLE_PATHS['governance-auditor']}` com poder de VETO.\n"
            "Audite o plano e a crítica contra todas as RULES em `.agents/rules/` e a política abaixo.\n"
            "Emita `REJECTED` se houver qualquer BLOCKER em aberto, violação P0 de segurança/LGPD, "
            "falta de testes diagnósticos estatísticos ou descontrole de FinOps.\n\n"
            f"--- POLICY.JSON ---\n{policy_text}\n\n"
            f"--- PLANO ---\n{json.dumps(current_plan, ensure_ascii=False, indent=2)}\n\n"
            f"--- CRÍTICA ADVERSARIAL ---\n{json.dumps(last_critique, ensure_ascii=False, indent=2)}"
        ),
        schema=audit_schema,
        role=f"Governance Auditor (Ciclo {cycle})",
        model="pro",
    )

    log(f"Ciclo {cycle}: veredito de governança = {last_audit['verdict']}")
    if last_audit["verdict"] in ("APPROVED", "APPROVED_WITH_CONDITIONS"):
        break

    feedback_history.append(
        {
            "cycle": cycle,
            "critique_blockers": last_critique["blockers"],
            "critique_majors": last_critique["majors"],
            "audit_violations": last_audit["violations"],
            "audit_rationale": last_audit["rationale"],
        }
    )

if not last_audit or last_audit["verdict"] == "REJECTED":
    log("CIRCUIT BREAKER ACIONADO: Plano não aprovado após o limite de ciclos. Escalando para revisão humana.")
    print(
        json.dumps(
            {
                "status": "ESCALATED_TO_HUMAN",
                "spec": str(spec_file),
                "cycles_run": max_cycles,
                "last_audit": last_audit,
                "last_critique": last_critique,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
else:
    # -----------------------------------------------------------------------
    # Fase 3: Gate HITL ou Execução Controlada
    # -----------------------------------------------------------------------
    execution_results = []
    if not should_execute:
        phase("3. Aguardando Aprovação Humana (HITL Gate)")
        log("Plano aprovado pela governança. `execute=False`: encerrando antes da execução para revisão humana.")
    else:
        phase("3. Execução Controlada pelos Especialistas")

        exec_schema = {
            "type": "object",
            "required": ["task_id", "status", "files_modified", "tests_executed", "evidence_summary"],
            "properties": {
                "task_id": {"type": "string"},
                "status": {"type": "string", "enum": ["DONE", "BLOCKED", "FAILED"]},
                "files_modified": {"type": "array", "items": {"type": "string"}},
                "tests_executed": {"type": "array", "items": {"type": "string"}},
                "evidence_summary": {"type": "string"},
            },
        }

        tasks = current_plan["tasks"]

        async def run_executor(task):
            role_file = AGENT_ROLE_PATHS.get(task["executor_role"], f".agents/agents/{task['executor_role']}.md")
            subagents = task.get("subagents_to_invoke") or []
            sub_block = (
                f"\nSub-operadores folha autorizados sob demanda (máx. 2 níveis, sem peer-to-peer): {subagents}\n"
                if subagents
                else "\nDelegação sob demanda: acione sub-operadores listados no seu frontmatter apenas se a tarefa exigir especialização granular.\n"
            )
            return await agent(
                prompt=(
                    f"Atue como Domain Manager conforme `{role_file}` e as regras em `AGENTS.md` e `src/AGENTS.md`.\n"
                    f"Execute exclusivamente a tarefa `{task['id']}` abaixo, respeitando as condições da auditoria."
                    f"{sub_block}"
                    "Escreva testes determinísticos e execute-os em sandbox antes de finalizar.\n\n"
                    f"--- TAREFA ---\n{json.dumps(task, ensure_ascii=False, indent=2)}\n\n"
                    f"--- CONDIÇÕES DE GOVERNANÇA ---\n{json.dumps(last_audit['conditions'], ensure_ascii=False)}\n\n"
                    f"--- TESTES DIAGNÓSTICOS DA LITERATURA ---\n"
                    f"{json.dumps(literature_brief['mandatory_diagnostic_tests'], ensure_ascii=False)}"
                ),
                schema=exec_schema,
                role=f"{task['executor_role']}: {task['id']}",
                model=task["model_tier"],
            )

        execution_results = await pipeline(tasks, run_executor)

        # -------------------------------------------------------------------
        # Fase 4: Verificação Final e Metrificação (governance-auditor)
        # -------------------------------------------------------------------
        phase("4. Verificação Final e Metrificação Operacional")
        verification_schema = {
            "type": "object",
            "required": ["verified", "compliance_ok", "notes"],
            "properties": {
                "verified": {"type": "boolean"},
                "compliance_ok": {"type": "boolean"},
                "notes": {"type": "string"},
            },
        }
        verification = await agent(
            prompt=(
                "Atue como `governance-auditor`. Verifique se todas as tarefas abaixo concluíram com testes "
                "determinísticos executados, sem violações de segurança/PII/FinOps. "
                "Se aplicável, execute `.agents/skills/ops-telemetry-auditor/scripts/audit_metrics.py`.\n\n"
                f"--- RESULTADOS DE EXECUÇÃO ---\n{json.dumps(execution_results, ensure_ascii=False, indent=2)}"
            ),
            schema=verification_schema,
            role="Governance Final Verification",
            model="pro",
        )
        log(f"Verificação final: verified={verification['verified']} | compliance={verification['compliance_ok']}")

        # -------------------------------------------------------------------
        # Fase 5: Curadoria de SKILLs e RULES (skill-curator)
        # -------------------------------------------------------------------
        phase("5. Curadoria de SKILLs e RULES")
        curation_schema = {
            "type": "object",
            "required": ["skill_candidates", "earned_rule_candidates", "summary"],
            "properties": {
                "skill_candidates": {"type": "array", "items": {"type": "string"}},
                "earned_rule_candidates": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
            },
        }
        curation = await agent(
            prompt=(
                f"Atue como `skill-curator` (`{AGENT_ROLE_PATHS['skill-curator']}`).\n"
                "Analise a execução concluída e `ops/patterns/repetitive_tasks_registry.json`.\n"
                "Identifique tarefas repetitivas candidatas a novas SKILLs (>=2 ocorrências) "
                "e lições aprendidas críticas candidatas a Earned RULES.\n\n"
                f"--- PLANO EXECUTADO ---\n{json.dumps(current_plan['summary'], ensure_ascii=False)}\n"
                f"--- RESULTADOS ---\n{json.dumps(execution_results, ensure_ascii=False, indent=2)}"
            ),
            schema=curation_schema,
            role="Skill & Rule Curator",
            model="flash",
        )
        log(f"Curadoria concluída: {curation['summary']}")

    print(
        json.dumps(
            {
                "status": "COMPLETED" if should_execute else "READY_FOR_HUMAN_APPROVAL",
                "spec": str(spec_file),
                "literature_refs": len(literature_brief["references"]),
                "plan_summary": current_plan["summary"],
                "audit_verdict": last_audit["verdict"],
                "audit_conditions": last_audit["conditions"],
                "execution_results": execution_results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
