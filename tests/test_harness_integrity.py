"""Testes determinísticos de integridade do harness agêntico, Gemini 4 routing e src/data_products."""

from __future__ import annotations

import ast
import importlib.util
import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path

from data_products.common.config import RuntimeConfig

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_all_json_files_are_valid() -> None:
    json_files = [
        p
        for p in REPO_ROOT.rglob("*.json")
        if ".venv" not in p.parts and "node_modules" not in p.parts
    ]
    assert len(json_files) >= 6
    for jf in json_files:
        json.loads(jf.read_text(encoding="utf-8"))


def test_all_python_scripts_compile() -> None:
    py_files = [
        p
        for p in REPO_ROOT.rglob("*.py")
        if ".venv" not in p.parts and "__pycache__" not in p.parts
    ]
    for pf in py_files:
        src = pf.read_text(encoding="utf-8")
        if pf.name == "data_task_orchestrator.py":
            compile(src, str(pf), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        else:
            py_compile.compile(str(pf), doraise=True)


def test_rule_files_respect_antigravity_context_budget() -> None:
    rule_files = list(REPO_ROOT.rglob("AGENTS.md")) + list((REPO_ROOT / ".agents" / "rules").glob("*.md"))
    assert len(rule_files) >= 10
    total_bytes = 0
    for rf in rule_files:
        size = rf.stat().st_size
        assert size < 24_000, f"Regra excede limite de 24 KB do Antigravity: {rf} ({size} bytes)"
        total_bytes += size
    assert total_bytes < 60_000


def test_agents_declare_gemini4_models_and_valid_skills() -> None:
    agents_root = REPO_ROOT / ".agents" / "agents"
    agent_files = sorted(agents_root.rglob("*.md"))
    assert len(agent_files) == 22  # 10 principais + 12 sub-operadores leaf
    existing_skills = {p.name for p in (REPO_ROOT / ".agents" / "skills").iterdir() if p.is_dir()}
    assert len(existing_skills) >= 19

    # Garante que todo subdiretório de agentes está registrado no manifesto .agents/agents.json
    manifest_path = REPO_ROOT / ".agents" / "agents.json"
    assert manifest_path.exists(), "Manifesto .agents/agents.json ausente para descoberta de subpastas."
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared_dirs = {entry["path"].replace("\\", "/").rstrip("/") for entry in manifest.get("entries", [])}
    actual_dirs = {
        str(af.parent.relative_to(REPO_ROOT)).replace("\\", "/")
        for af in agent_files
        if af.parent != agents_root
    }
    assert actual_dirs.issubset(declared_dirs), f"Subpastas fora de .agents/agents.json: {actual_dirs - declared_dirs}"

    for af in agent_files:
        text = af.read_text(encoding="utf-8")
        assert re.search(r"(?m)^gemini4_model:\s*Gemini 4 (Carbon|Neon|Hydrogen|Argon)", text), (
            f"Agente sem gemini4_model válido: {af.name}"
        )
        m = re.search(r"(?ms)^skills:\n((?:\s+-\s+[a-z0-9-]+\n)+)", text)
        assert m, f"Agente sem lista de skills no frontmatter: {af.name}"
        declared = re.findall(r"-\s+([a-z0-9-]+)", m.group(1))
        for sk in declared:
            assert sk in existing_skills, f"Agente {af.name} referencia skill inexistente: {sk}"


def test_two_level_manager_subagent_hierarchy() -> None:
    agents_dir = REPO_ROOT / ".agents" / "agents"
    all_agents = {p.stem: p.read_text(encoding="utf-8") for p in agents_dir.rglob("*.md")}

    managers = {k: v for k, v in all_agents.items() if re.search(r"(?m)^role_type:\s*domain-manager$", v)}
    subagents = {k: v for k, v in all_agents.items() if re.search(r"(?m)^role_type:\s*subagent$", v)}

    assert len(managers) == 4
    assert len(subagents) == 12

    referenced_subagents: set[str] = set()
    for mgr_name, mgr_text in managers.items():
        m = re.search(r"(?ms)^subagents:\n((?:\s+-\s+[a-z0-9-]+\n)+)", mgr_text)
        assert m, f"Domain Manager sem lista de subagents: {mgr_name}"
        subs = re.findall(r"-\s+([a-z0-9-]+)", m.group(1))
        assert subs
        for s in subs:
            assert s in subagents, f"Manager {mgr_name} referencia subagent inexistente: {s}"
            assert re.search(rf"(?m)^manager:\s*{re.escape(mgr_name)}$", subagents[s]), (
                f"Subagent {s} não aponta para o manager {mgr_name}"
            )
            referenced_subagents.add(s)

    assert referenced_subagents == set(subagents.keys())

    # Impõe profundidade máxima = 2 níveis (nenhum leaf pode spawnar sub-agentes)
    for sub_name, sub_text in subagents.items():
        assert re.search(r"(?m)^can_spawn_subagents:\s*false$", sub_text), (
            f"Subagent {sub_name} deve declarar can_spawn_subagents: false"
        )
        assert not re.search(r"(?m)^subagents:", sub_text), (
            f"Subagent leaf {sub_name} não pode declarar subagents (limite 2 níveis)"
        )


def test_runtime_config_blocks_tls_bypass(monkeypatch) -> None:
    env_key = "NODE_TLS_REJECT_UNAUTHORIZED"
    monkeypatch.delenv(env_key, raising=False)
    monkeypatch.delenv("AZURE_CLI_DISABLE_CONNECTION_VERIFICATION", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    cfg = RuntimeConfig.from_env()
    assert cfg.tls_verify_arg() is True

    monkeypatch.setenv(env_key, "0")
    try:
        RuntimeConfig.from_env()
        raise AssertionError("RuntimeConfig deveria rejeitar bypass TLS")
    except RuntimeError:
        pass


def test_security_finops_gate_enforces_p0_rules() -> None:
    gate_path = REPO_ROOT / ".agents" / "hooks" / "security_finops_gate.py"
    spec = importlib.util.spec_from_file_location("security_finops_gate", gate_path)
    assert spec and spec.loader
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)

    policy = json.loads((REPO_ROOT / "ops" / "governance" / "policy.json").read_text(encoding="utf-8"))

    assert gate.evaluate_command("pytest tests/", policy)[0] == "allow"
    assert gate.evaluate_command("aws s3 rm s3://bucket --recursive", policy)[0] == "deny"
    assert gate.evaluate_command('sqlcmd -Q "DROP TABLE gold.orders"', policy)[0] == "deny"
    assert gate.evaluate_command("curl -k https://api.fabric.microsoft.com", policy)[0] == "deny"
    bad_tls_snippet = "requests.get(url, " + "verify" + "=False)"
    assert gate.evaluate_file_write(
        {"Path": "src/data_products/x.py", "Content": bad_tls_snippet},
        policy,
    )[0] == "deny"
    assert gate.evaluate_mcp_call(
        "call_mcp_tool",
        {"ServerName": "fabric-mcp-server", "ToolName": "core_list-workspaces"},
        policy,
    )[0] == "allow"
    assert gate.evaluate_mcp_call(
        "call_mcp_tool",
        {"ServerName": "fabric-mcp-server", "ToolName": "delete_workspace"},
        policy,
    )[0] == "deny"


def test_internal_and_example_specs_are_valid() -> None:
    spec_cli = REPO_ROOT / ".agents" / "skills" / "spec-lifecycle" / "scripts" / "spec_cli.py"
    for spec in (
        REPO_ROOT / "specs" / "internal" / "SPEC-000-mcp-fabric-aws-runtime.md",
        REPO_ROOT / "specs" / "internal" / "SPEC-000B-pbip-powerbi-mcp-precheck.md",
        REPO_ROOT / "specs" / "active" / "SPEC-001-exemplo-cross-cloud-churn.md",
    ):
        proc = subprocess.run(
            [sys.executable, str(spec_cli), "validate", "--spec", str(spec)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert json.loads(proc.stdout)["valid"] is True


def test_pbip_precheck_passes_on_clean_repo_directory(tmp_path: Path) -> None:
    precheck = REPO_ROOT / ".agents" / "skills" / "powerbi-pbip-semantic-ops" / "scripts" / "pbip_precheck.py"
    out = tmp_path / "pbip_report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(precheck),
            "--path",
            str(REPO_ROOT / "src" / "data_products" / "analytics" / "pbip"),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.returncode == 0
    assert json.loads(out.read_text(encoding="utf-8"))["summary"]["passed"] is True


def test_new_model_optimized_skill_clis(tmp_path: Path) -> None:
    # 1. finops-cost-estimator (Carbon / Neon)
    finops_cli = REPO_ROOT / ".agents/skills/finops-cost-estimator/scripts/estimate_finops.py"
    fin_out = tmp_path / "finops.json"
    subprocess.run(
        [
            sys.executable,
            str(finops_cli),
            "--athena-scan-gb",
            "80",
            "--aws-egress-gb",
            "20",
            "--s3-shortcut-cache",
            "true",
            "--fabric-cu-seconds",
            "1200",
            "--llm-model",
            "neon",
            "--llm-input-k",
            "100",
            "--llm-output-k",
            "20",
            "--output",
            str(fin_out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    fin_rep = json.loads(fin_out.read_text(encoding="utf-8"))
    assert fin_rep["withinAutoApprovalBudget"] is False

    # 2. odcs-contract-validator (Neon / Carbon)
    odcs_cli = REPO_ROOT / ".agents/skills/odcs-contract-validator/scripts/validate_odcs.py"
    odcs_out = tmp_path / "odcs.json"
    subprocess.run(
        [
            sys.executable,
            str(odcs_cli),
            "--contract",
            str(REPO_ROOT / "contracts/templates/data-contract.odcs.yaml"),
            "--output",
            str(odcs_out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(odcs_out.read_text(encoding="utf-8"))["passed"] is True

    # 3. statistical-diagnostics-runner (Neon)
    diag_cli = REPO_ROOT / ".agents/skills/statistical-diagnostics-runner/scripts/run_diagnostics.py"
    train_csv = tmp_path / "train.csv"
    oot_csv = tmp_path / "oot.csv"
    rows_train = ["x1,x2,y,prob"] + [f"{i},{i * 2},{i % 2},{0.8 if i % 2 else 0.2}" for i in range(1, 31)]
    rows_oot = ["x1,x2,y,prob"] + [f"{i + 50},{i * 2 + 100},{i % 2},{0.8 if i % 2 else 0.2}" for i in range(1, 31)]
    train_csv.write_text("\n".join(rows_train), encoding="utf-8")
    oot_csv.write_text("\n".join(rows_oot), encoding="utf-8")
    diag_out = tmp_path / "diag.json"
    subprocess.run(
        [
            sys.executable,
            str(diag_cli),
            "--train-csv",
            str(train_csv),
            "--oot-csv",
            str(oot_csv),
            "--target-col",
            "y",
            "--prob-col",
            "prob",
            "--output",
            str(diag_out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    diag_rep = json.loads(diag_out.read_text(encoding="utf-8"))
    assert len(diag_rep["highCollinearityPairs"]) >= 1
    assert len(diag_rep["psiAlerts"]) >= 1
    assert diag_rep["targetSummary"]["brierScore"] == 0.04

    # 4. ml-leakage-and-oot-guard (Neon / Carbon)
    leak_cli = REPO_ROOT / ".agents/skills/ml-leakage-and-oot-guard/scripts/check_leakage.py"
    bad_ml = tmp_path / "bad_ml"
    bad_ml.mkdir()
    (bad_ml / "pipe.py").write_text(
        "X = scaler.fit_transform(df)\nX_tr, X_te = train_test_split(X, y)\n",
        encoding="utf-8",
    )
    leak_out = tmp_path / "leak.json"
    res_leak = subprocess.run(
        [sys.executable, str(leak_cli), "--path", str(bad_ml), "--output", str(leak_out)],
        capture_output=True,
        text=True,
    )
    assert res_leak.returncode == 1
    assert json.loads(leak_out.read_text(encoding="utf-8"))["passed"] is False

    # 5. medallion-pipeline-scaffolder --help (Hydrogen)
    scaf_cli = REPO_ROOT / ".agents/skills/medallion-pipeline-scaffolder/scripts/scaffold_pipeline.py"
    subprocess.run([sys.executable, str(scaf_cli), "--help"], check=True, capture_output=True, text=True)


def test_dual_mode_global_plugin_install_and_init_workspace(tmp_path: Path) -> None:
    warmup_script = REPO_ROOT / "scripts" / "warmup.py"
    plugin_dir = tmp_path / "global_plugins" / "analytics-agent"
    plugin_data = tmp_path / "plugin_data"
    external_ws = tmp_path / "external_data_project"
    external_ws.mkdir()

    # 1. Instalar/montar o Plugin Global a partir do repositório local
    subprocess.run(
        [
            sys.executable,
            str(warmup_script),
            "install",
            "--source-dir",
            str(REPO_ROOT),
            "--target-dir",
            str(plugin_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    # Verifica artefatos nativos de plugin Antigravity
    manifest = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "analytics-agent"
    assert manifest.get("logo") == "assets/logo.svg"
    assert (plugin_dir / "assets" / "logo.svg").exists()
    assert (plugin_dir / "mcp_config.json").exists()
    assert (plugin_dir / "hooks.json").exists()
    assert (plugin_dir / "ops" / "governance" / "policy.json").exists()

    rules_file = plugin_dir / "rules" / "AGENTS.md"
    assert rules_file.exists() and rules_file.stat().st_size < 24_000

    bundled_agents = list((plugin_dir / "agents").glob("*.md"))
    bundled_skills = [p for p in (plugin_dir / "skills").iterdir() if p.is_dir()]
    assert len(bundled_agents) == 22
    assert len(bundled_skills) >= 20

    # 2. Testar status CLI
    st_proc = subprocess.run(
        [sys.executable, str(warmup_script), "status", "--target-dir", str(plugin_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    st = json.loads(st_proc.stdout)
    assert st["installed"] is True and st["agentsCount"] == 22 and st["skillsCount"] >= 20

    # 3. Testar hook PreToolUse em Modo Plugin Global sobre workspace externo SEM policy.json
    import os

    env = os.environ.copy()
    env["PLUGIN_ROOT"] = str(plugin_dir)
    env["PLUGIN_DATA"] = str(plugin_data)
    hook_payload = {
        "conversationId": "dual-test",
        "workspacePaths": [str(external_ws)],
        "modelName": "pro",
        "stepIdx": 1,
        "toolCall": {
            "id": "t1",
            "name": "run_command",
            "args": {"CommandLine": "aws s3 rm s3://prod-bucket --recursive"},
        },
    }
    hook_proc = subprocess.run(
        [sys.executable, str(plugin_dir / "hooks" / "security_finops_gate.py")],
        input=json.dumps(hook_payload),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(hook_proc.stdout)["decision"] == "deny"
    # Telemetria foi para PLUGIN_DATA sem criar pasta ops/ indesejada no workspace externo
    assert (plugin_data / "telemetry" / "events.jsonl").exists()
    assert not (external_ws / "ops").exists()

    # 4. Testar init-workspace (cria estrutura de trabalho sem copiar .agents/)
    init_proc = subprocess.run(
        [
            sys.executable,
            str(warmup_script),
            "init-workspace",
            "--workspace",
            str(external_ws),
            "--plugin-dir",
            str(plugin_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    init_res = json.loads(init_proc.stdout)
    assert init_res["dotAgentsCopied"] is False
    assert (external_ws / "specs" / "templates").exists()
    assert (external_ws / "contracts" / "templates").exists()
    assert (external_ws / "src" / "data_products" / "analytics" / "pbip").exists()
    assert not (external_ws / ".agents").exists()
