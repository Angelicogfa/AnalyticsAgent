"""Orquestrador Multi-Agente Nativo para Google Antigravity (`run_workflow`).

Executa o ciclo governado com persistência de estado e validação determinística:
  SPEC -> Literature Check -> [Plan -> Review & Critique -> Governance Audit (VETO)] (max 3x)
       -> (opcional HITL gate) -> Execution (DAG depends_on + fail-fast)
       -> Deterministic Verification -> Skill/Rule Curation
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Parâmetros e resolução de caminhos (Workspace vs. Modo Plugin)
# ---------------------------------------------------------------------------
spec_rel = args["spec_path"]
should_execute = bool(args.get("execute", False))
max_cycles = min(int(args.get("max_plan_cycles", 3)), 3)

workspace_root = Path(WORKSPACES[0]) if WORKSPACES else Path.cwd()
spec_file = (workspace_root / spec_rel) if not Path(spec_rel).is_absolute() else Path(spec_rel)

if not spec_file.exists():
    raise FileNotFoundError(f"SPEC não encontrada: {spec_file}")

plugin_env = os.environ.get("PLUGIN_ROOT", "").strip() or os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
plugin_root = Path(plugin_env) if plugin_env else None
is_plugin_mode = plugin_root is not None and (plugin_root / "skills").exists()
harness_root = plugin_root if is_plugin_mode else (workspace_root / ".agents")

AGENT_DOMAINS = {
    "orchestrator": "core",
    "literature-researcher": "core",
    "planner-architect": "core",
    "plan-reviewer-critic": "core",
    "governance-auditor": "core",
    "skill-curator": "core",
    "data-engineer": "data-engineering",
    "data-scientist-statistician": "data-science",
    "analytics-bi-specialist": "analytics-bi",
    "backend-mlops-specialist": "backend-mlops",
}


def agent_role_path(role_name: str) -> str:
    if is_plugin_mode and harness_root:
        return str((harness_root / "agents" / f"{role_name}.md").as_posix())
    domain = AGENT_DOMAINS.get(role_name, "core")
    return f".agents/agents/{domain}/{role_name}.md"


def skill_path(skill_name: str) -> str:
    if is_plugin_mode and harness_root:
        return str((harness_root / "skills" / skill_name / "SKILL.md").as_posix())
    return f".agents/skills/{skill_name}/SKILL.md"


def resolve_spec_cli() -> Path:
    if is_plugin_mode and harness_root:
        cand = harness_root / "skills" / "spec-lifecycle" / "scripts" / "spec_cli.py"
        if cand.exists():
            return cand
    return workspace_root / ".agents" / "skills" / "spec-lifecycle" / "scripts" / "spec_cli.py"


def load_policy_text() -> str:
    for p in (
        workspace_root / "ops" / "governance" / "policy.json",
        (harness_root / "ops" / "governance" / "policy.json") if harness_root else None,
        workspace_root / ".agents" / "ops" / "governance" / "policy.json",
    ):
        if p and p.exists():
            return p.read_text(encoding="utf-8")
    return "{}"


def parse_spec_meta(text: str) -> tuple[str, str]:
    id_m = re.search(r"^spec_id:\s*([A-Za-z0-9_-]+)", text, re.MULTILINE)
    st_m = re.search(r"^status:\s*([A-Z_]+)", text, re.MULTILINE)
    spec_id = id_m.group(1) if id_m else spec_file.stem.split("-")[0]
    status = st_m.group(1) if st_m else "DRAFT"
    return spec_id, status


def plan_digest(plan_obj: dict) -> str:
    canonical = json.dumps(plan_obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_state(state_file: Path) -> dict:
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return {}


def save_state(state_file: Path, state: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_spec_section(path: Path, heading: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = rf"(?ms)(^{re.escape(heading)}\n)(.*?)(?=^##\s+\d+\.|\Z)"
    replacement = f"{heading}\n{body.strip()}\n\n"
    if re.search(pattern, text):
        updated = re.sub(pattern, lambda _m: replacement, text, count=1)
    else:
        updated = text.rstrip() + "\n\n" + replacement
    path.write_text(updated, encoding="utf-8")


def transition_spec(path: Path, target_status: str) -> str:
    cli = resolve_spec_cli()
    proc = subprocess.run(
        [
            sys.executable,
            str(cli),
            "transition",
            "--workspace",
            str(workspace_root),
            "--spec",
            str(path),
            "--to",
            target_status,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Falha ao transicionar SPEC para {target_status}: {proc.stderr.strip()}")
    return target_status


def topo_sort_tasks(tasks: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for t in tasks:
        tid = t["id"]
        if tid in by_id:
            raise ValueError(f"ID de tarefa duplicado no plano: {tid}")
        by_id[tid] = t

    visited: dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=done
    ordered: list[dict] = []

    def visit(tid: str) -> None:
        state = visited.get(tid, 0)
        if state == 1:
            raise ValueError(f"Ciclo detectado no DAG de tarefas envolvendo '{tid}'.")
        if state == 2:
            return
        visited[tid] = 1
        for dep in by_id[tid].get("depends_on") or []:
            if dep not in by_id:
                raise ValueError(f"Tarefa '{tid}' depende de '{dep}', que não existe no plano.")
            visit(dep)
        visited[tid] = 2
        ordered.append(by_id[tid])

    for tid in by_id:
        visit(tid)
    return ordered


spec_content = spec_file.read_text(encoding="utf-8")
spec_id, current_status = parse_spec_meta(spec_content)
state_file = spec_file.parent / ".state" / f"{spec_id}.plan.json"
state = load_state(state_file)
policy_text = load_policy_text()

phase("0. Bootstrap da SPEC")
log(f"SPEC={spec_id} ({spec_file.name}) | status={current_status} | execute={should_execute}")

# ---------------------------------------------------------------------------
# Schemas estruturados
# ---------------------------------------------------------------------------
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
                "required": [
                    "id",
                    "executor_role",
                    "model_tier",
                    "title",
                    "deliverables",
                    "acceptance_test",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "IDs de tarefas que precisam concluir antes desta.",
                    },
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
                        "description": "Sub-operadores leaf opcionais necessários sob demanda.",
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

# ---------------------------------------------------------------------------
# Modo Execução (execute=True): exige plano já aprovado e hash íntegro (G3)
# ---------------------------------------------------------------------------
if should_execute:
    saved_plan = state.get("approved_plan")
    saved_hash = state.get("plan_sha256", "")
    saved_audit = state.get("last_audit") or {}
    saved_lit = state.get("literature_brief") or {"mandatory_diagnostic_tests": []}

    valid_exec_status = current_status in {"APPROVED", "EXECUTING"}
    valid_hash = bool(saved_plan) and plan_digest(saved_plan) == saved_hash

    if not valid_exec_status or not valid_hash:
        reason = (
            f"Execução bloqueada: SPEC status='{current_status}' (esperado APPROVED/EXECUTING) "
            f"ou plano aprovado ausente/adulterado em {state_file.name}."
        )
        log(reason)
        print(
            json.dumps(
                {
                    "status": "BLOCKED_UNAPPROVED_PLAN",
                    "spec": str(spec_file),
                    "spec_status": current_status,
                    "reason": reason,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if current_status == "APPROVED":
            current_status = transition_spec(spec_file, "EXECUTING")
            state["status"] = current_status
            save_state(state_file, state)

        phase("3. Execução Controlada do Plano Aprovado")
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

        ordered_tasks = topo_sort_tasks(saved_plan["tasks"])
        execution_results = []
        failed_task = None

        for task in ordered_tasks:
            role_file = agent_role_path(task["executor_role"])
            subagents = task.get("subagents_to_invoke") or []
            sub_block = (
                f"\nSub-operadores folha autorizados sob demanda (máx. 2 níveis): {subagents}\n"
                if subagents
                else "\nAcione sub-operadores listados no seu frontmatter apenas sob demanda.\n"
            )
            res = await agent(
                prompt=(
                    f"Atue como Domain Manager conforme `{role_file}` e `AGENTS.md` / `src/AGENTS.md`.\n"
                    f"Execute exclusivamente a tarefa `{task['id']}` abaixo, respeitando a auditoria."
                    f"{sub_block}"
                    "Escreva testes determinísticos e execute-os em sandbox antes de finalizar.\n\n"
                    f"--- TAREFA ---\n{json.dumps(task, ensure_ascii=False, indent=2)}\n\n"
                    f"--- CONDIÇÕES ---\n{json.dumps(saved_audit.get('conditions', []), ensure_ascii=False)}\n\n"
                    f"--- TESTES DIAGNÓSTICOS ---\n"
                    f"{json.dumps(saved_lit.get('mandatory_diagnostic_tests', []), ensure_ascii=False)}"
                ),
                schema=exec_schema,
                role=f"{task['executor_role']}: {task['id']}",
                model=task["model_tier"],
            )
            execution_results.append(res)
            if res["status"] in ("FAILED", "BLOCKED"):
                failed_task = res
                log(f"FAIL-FAST: tarefa '{task['id']}' retornou {res['status']}. Interrompendo execução.")
                break

        if failed_task is not None:
            print(
                json.dumps(
                    {
                        "status": "EXECUTION_FAILED",
                        "spec": str(spec_file),
                        "spec_status": current_status,
                        "failed_task": failed_task,
                        "execution_results": execution_results,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
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
            tel_skill = skill_path("ops-telemetry-auditor")
            verification = await agent(
                prompt=(
                    f"Atue como `governance-auditor` (`{agent_role_path('governance-auditor')}`). "
                    "Verifique se todas as tarefas concluíram com testes determinísticos executados e sem "
                    f"violações de segurança/PII/FinOps. Use `{tel_skill}` se aplicável.\n\n"
                    f"--- RESULTADOS ---\n{json.dumps(execution_results, ensure_ascii=False, indent=2)}"
                ),
                schema=verification_schema,
                role="Governance Final Verification",
                model="pro",
            )
            log(f"Verificação: verified={verification['verified']} | compliance={verification['compliance_ok']}")

            if not (verification["verified"] and verification["compliance_ok"]):
                print(
                    json.dumps(
                        {
                            "status": "VERIFICATION_FAILED",
                            "spec": str(spec_file),
                            "spec_status": current_status,
                            "verification": verification,
                            "execution_results": execution_results,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                current_status = transition_spec(spec_file, "VERIFIED")
                state["status"] = current_status
                save_state(state_file, state)

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
                        f"Atue como `skill-curator` (`{agent_role_path('skill-curator')}`).\n"
                        "Analise a execução concluída e `ops/patterns/repetitive_tasks_registry.json`.\n"
                        "Identifique tarefas repetitivas candidatas a novas SKILLs (>=2 ocorrências) "
                        "e lições críticas candidatas a Earned RULES.\n\n"
                        f"--- PLANO ---\n{json.dumps(saved_plan['summary'], ensure_ascii=False)}\n"
                        f"--- RESULTADOS ---\n{json.dumps(execution_results, ensure_ascii=False, indent=2)}"
                    ),
                    schema=curation_schema,
                    role="Skill & Rule Curator",
                    model="flash",
                )
                log(f"Curadoria concluída: {curation['summary']}")

                current_status = transition_spec(spec_file, "COMPLETED")
                state["status"] = current_status
                save_state(state_file, state)

                print(
                    json.dumps(
                        {
                            "status": "COMPLETED",
                            "spec": str(spec_file),
                            "spec_status": current_status,
                            "plan_sha256": saved_hash,
                            "verification": verification,
                            "curation": curation,
                            "execution_results": execution_results,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )

# ---------------------------------------------------------------------------
# Modo Planejamento (execute=False): retoma do status atual e persiste plano
# ---------------------------------------------------------------------------
else:
    if current_status in {"APPROVED", "EXECUTING", "VERIFIED", "COMPLETED"} and state.get("approved_plan"):
        phase("1-2. SPEC já Aprovada")
        log(f"SPEC já está em '{current_status}' com plano persistido. Pronto para `--execute`.")
        print(
            json.dumps(
                {
                    "status": "READY_FOR_HUMAN_APPROVAL",
                    "spec": str(spec_file),
                    "spec_status": current_status,
                    "plan_sha256": state.get("plan_sha256"),
                    "plan_summary": state["approved_plan"]["summary"],
                    "audit_verdict": (state.get("last_audit") or {}).get("verdict", "APPROVED"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        # Fase 1: Literatura (se ainda em DRAFT ou sem parecer salvo)
        literature_brief = state.get("literature_brief")
        if current_status == "DRAFT" or not literature_brief:
            phase("1. Validação de Literatura e Premissas")
            kb_skill = skill_path("internal-knowledge-base")
            lit_skill = skill_path("literature-premise-validator")
            literature_brief = await agent(
                prompt=(
                    f"Atue conforme `{agent_role_path('literature-researcher')}` e as skills "
                    f"`{kb_skill}` e `{lit_skill}`.\n"
                    "PRIMEIRO consulte a base interna `knowledge/` (citando `KB-NNN`); "
                    "DEPOIS complemente na web/literatura.\n"
                    "Levante premissas estatísticas/operacionais, testes diagnósticos e Plano B.\n\n"
                    f"--- SPEC ({spec_file.name}) ---\n{spec_content}"
                ),
                schema=literature_schema,
                role="Literature Researcher",
                model="flash",
            )
            refs_md = "\n".join(
                f"- **{r['title']}** ({r['source']}): {r['relevance']}"
                for r in literature_brief["references"]
            )
            lit_md = (
                f"- **Domínio:** {literature_brief['domain']}\n"
                f"- **Referências:**\n{refs_md or '- Nenhuma'}\n"
                f"- **Premissas Estatísticas:** {'; '.join(literature_brief['statistical_premises'])}\n"
                f"- **Premissas Operacionais:** {'; '.join(literature_brief['operational_premises'])}\n"
                f"- **Testes Diagnósticos Obrigatórios:** "
                f"{'; '.join(literature_brief['mandatory_diagnostic_tests'])}\n"
                f"- **Plano B:** {'; '.join(literature_brief['fallback_methods'])}"
            )
            update_spec_section(spec_file, "## 3. Parecer de Literatura e Premissas", lit_md)
            state["literature_brief"] = literature_brief
            if current_status == "DRAFT":
                current_status = transition_spec(spec_file, "LITERATURE_CHECK")
            state["status"] = current_status
            save_state(state_file, state)
            spec_content = spec_file.read_text(encoding="utf-8")

        # Fase 2: Ciclo Planejar -> Revisar -> Criticar -> Auditar (retomável)
        phase("2. Planejamento, Revisão, Crítica Adversarial e Auditoria")
        feedback_history = state.get("feedback_history") or []
        current_plan = state.get("approved_plan")
        last_critique = state.get("last_critique")
        last_audit = None

        for cycle in range(1, max_cycles + 1):
            log(f"--- Ciclo de Planejamento {cycle}/{max_cycles} (status atual={current_status}) ---")

            # Se já existe plano gerado (ex.: SPEC retomada em REVIEWED/CRITIQUED), reaproveita no ciclo 1
            if cycle == 1 and current_status in {"REVIEWED", "CRITIQUED"} and current_plan:
                log("Retomando plano existente sem regenerar do zero.")
            else:
                feedback_block = (
                    f"\nFeedback acumulado (resolva TODOS os blockers/violações):\n"
                    f"{json.dumps(feedback_history, ensure_ascii=False, indent=2)}"
                    if feedback_history
                    else ""
                )
                current_plan = await agent(
                    prompt=(
                        f"Atue conforme `{agent_role_path('planner-architect')}` e as regras em `AGENTS.md`, "
                        "`.agents/rules/`, `clouds/azure-fabric/AGENTS.md` e `clouds/aws/AGENTS.md`.\n"
                        "Elabore um plano técnico em DAG (usando `depends_on` quando houver precedência) "
                        "otimizado em custos (FinOps + LLM Tiering) e com testes diagnósticos.\n\n"
                        f"--- SPEC ---\n{spec_content}\n\n"
                        f"--- PARECER DE LITERATURA ---\n"
                        f"{json.dumps(literature_brief, ensure_ascii=False, indent=2)}"
                        f"{feedback_block}"
                    ),
                    schema=plan_schema,
                    role=f"Planner Architect (Ciclo {cycle})",
                    model="pro",
                )
                # Valida DAG antes de avançar
                topo_sort_tasks(current_plan["tasks"])

                tasks_md = "\n".join(
                    f"- `{t['id']}` ({t['executor_role']}, {t['model_tier']}, "
                    f"deps={t.get('depends_on') or []}): {t['title']}"
                    for t in current_plan["tasks"]
                )
                plan_md = (
                    f"- **Resumo:** {current_plan['summary']}\n"
                    f"- **Nuvens:** {', '.join(current_plan['clouds_involved'])}\n"
                    f"- **DAG de Execução:**\n{tasks_md or '- Nenhuma tarefa'}\n"
                    f"- **Controles FinOps:** {'; '.join(current_plan['finops_estimate']['cloud_cost_controls'])}\n"
                    f"- **Rollback:** {current_plan['rollback_plan']}"
                )
                update_spec_section(spec_file, "## 4. Plano Técnico e FinOps", plan_md)
                state["approved_plan"] = current_plan
                if current_status == "LITERATURE_CHECK":
                    current_status = transition_spec(spec_file, "PLANNED")
                if current_status == "PLANNED":
                    current_status = transition_spec(spec_file, "REVIEWED")
                state["status"] = current_status
                save_state(state_file, state)

            if cycle == 1 and current_status == "CRITIQUED" and last_critique:
                log("Retomando crítica existente para auditoria final.")
            else:
                last_critique = await agent(
                    prompt=(
                        f"Atue conforme `{agent_role_path('plan-reviewer-critic')}` em modo Red Team.\n"
                        "Critique o plano buscando: falhas à SPEC, egress AWS->Fabric, falta de partições, "
                        "CUs Fabric, data leakage, premissas sem teste diagnóstico, idempotência ou PII.\n\n"
                        f"--- SPEC ---\n{spec_content}\n\n"
                        f"--- LITERATURA ---\n{json.dumps(literature_brief, ensure_ascii=False, indent=2)}\n\n"
                        f"--- PLANO ---\n{json.dumps(current_plan, ensure_ascii=False, indent=2)}"
                    ),
                    schema=critique_schema,
                    role=f"Plan Reviewer & Critic (Ciclo {cycle})",
                    model="pro",
                )
                crit_md = (
                    f"- **Resumo da Revisão:** {last_critique['review_summary']}\n"
                    f"- **BLOCKERs:** {last_critique['blockers']}\n"
                    f"- **MAJORs:** {last_critique['majors']}\n"
                    f"- **MINORs:** {last_critique['minors']}"
                )
                update_spec_section(spec_file, "## 5. Revisão e Crítica Adversarial", crit_md)
                state["last_critique"] = last_critique
                if current_status == "REVIEWED":
                    current_status = transition_spec(spec_file, "CRITIQUED")
                state["status"] = current_status
                save_state(state_file, state)

            last_audit = await agent(
                prompt=(
                    f"Atue conforme `{agent_role_path('governance-auditor')}` com poder de VETO.\n"
                    "Audite o plano e a crítica contra `.agents/rules/` e a política abaixo.\n"
                    "Emita `REJECTED` se houver BLOCKER aberto, violação P0 ou falta de diagnósticos.\n\n"
                    f"--- POLICY.JSON ---\n{policy_text}\n\n"
                    f"--- PLANO ---\n{json.dumps(current_plan, ensure_ascii=False, indent=2)}\n\n"
                    f"--- CRÍTICA ---\n{json.dumps(last_critique, ensure_ascii=False, indent=2)}"
                ),
                schema=audit_schema,
                role=f"Governance Auditor (Ciclo {cycle})",
                model="pro",
            )
            audit_md = (
                f"- **Veredito:** `{last_audit['verdict']}`\n"
                f"- **Regras Verificadas:** {', '.join(last_audit['rules_checked'])}\n"
                f"- **Violações:** {last_audit['violations']}\n"
                f"- **Condições:** {last_audit['conditions']}\n"
                f"- **Justificativa:** {last_audit['rationale']}"
            )
            update_spec_section(spec_file, "## 6. Auditoria de Governança", audit_md)
            state["last_audit"] = last_audit

            log(f"Ciclo {cycle}: veredito de governança = {last_audit['verdict']}")
            if last_audit["verdict"] in ("APPROVED", "APPROVED_WITH_CONDITIONS"):
                current_status = transition_spec(spec_file, "APPROVED")
                state["status"] = current_status
                state["plan_sha256"] = plan_digest(current_plan)
                save_state(state_file, state)
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
            state["feedback_history"] = feedback_history
            if current_status in {"REVIEWED", "CRITIQUED"}:
                current_status = transition_spec(spec_file, "PLANNED")
            state["status"] = current_status
            save_state(state_file, state)

        if not last_audit or last_audit["verdict"] == "REJECTED":
            log("CIRCUIT BREAKER ACIONADO: Plano não aprovado após limite de ciclos.")
            print(
                json.dumps(
                    {
                        "status": "ESCALATED_TO_HUMAN",
                        "spec": str(spec_file),
                        "spec_status": current_status,
                        "cycles_run": max_cycles,
                        "last_audit": last_audit,
                        "last_critique": last_critique,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            phase("3. Aguardando Aprovação Humana (HITL Gate)")
            print(
                json.dumps(
                    {
                        "status": "READY_FOR_HUMAN_APPROVAL",
                        "spec": str(spec_file),
                        "spec_status": current_status,
                        "plan_sha256": state["plan_sha256"],
                        "literature_refs": len(literature_brief["references"]),
                        "plan_summary": current_plan["summary"],
                        "audit_verdict": last_audit["verdict"],
                        "audit_conditions": last_audit["conditions"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
