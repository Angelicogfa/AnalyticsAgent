"""Testes da camada Claude Code: paridade com o Antigravity, sem drift e sem regressão do modo original."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
AG_GATE = REPO_ROOT / ".agents" / "hooks" / "security_finops_gate.py"
CLAUDE_GATE = REPO_ROOT / ".claude" / "hooks" / "claude_gate.py"
WARMUP = REPO_ROOT / "scripts" / "warmup.py"
RUN_SPEC = REPO_ROOT / ".claude" / "workflows" / "run_spec_cycle.py"
SPEC_001 = "specs/active/SPEC-001-exemplo-cross-cloud-churn.md"

TLS_BYPASS = "requests.get(url, " + "verify" + "=False)"
FAKE_AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"

# (descrição, payload Antigravity toolCall, payload Claude tool_name/tool_input, decisão Antigravity esperada)
PARITY_CASES = [
    (
        "pytest",
        ("run_command", {"CommandLine": "pytest tests/"}),
        ("Bash", {"command": "pytest tests/"}),
        "allow",
    ),
    (
        "s3-rm-recursive",
        ("run_command", {"CommandLine": "aws s3 rm s3://b --recursive"}),
        ("Bash", {"command": "aws s3 rm s3://b --recursive"}),
        "deny",
    ),
    (
        "drop-table-powershell",
        ("run_command", {"CommandLine": 'sqlcmd -Q "DROP TABLE gold.orders"'}),
        ("PowerShell", {"command": 'sqlcmd -Q "DROP TABLE gold.orders"'}),
        "deny",
    ),
    (
        "curl-insecure",
        ("run_command", {"CommandLine": "curl -k https://api.fabric.microsoft.com"}),
        ("Bash", {"command": "curl -k https://api.fabric.microsoft.com"}),
        "deny",
    ),
    (
        "truncate",
        ("run_command", {"CommandLine": "TRUNCATE TABLE silver.x"}),
        ("Bash", {"command": "TRUNCATE TABLE silver.x"}),
        "force_ask",
    ),
    (
        "select-star",
        ("run_command", {"CommandLine": "SELECT * FROM big_table"}),
        ("Bash", {"command": "SELECT * FROM big_table"}),
        "force_ask",
    ),
    (
        "write-tls-bypass",
        ("write_file", {"Path": "src/data_products/x.py", "Content": TLS_BYPASS}),
        ("Write", {"file_path": "src/data_products/x.py", "content": TLS_BYPASS}),
        "deny",
    ),
    (
        "write-policy",
        ("write_file", {"Path": "ops/governance/policy.json", "Content": "{}"}),
        ("Write", {"file_path": "ops/governance/policy.json", "content": "{}"}),
        "force_ask",
    ),
    (
        "edit-secret",
        ("edit_file", {"Path": "src/a.py", "Replacement": f"KEY = '{FAKE_AWS_KEY}'"}),
        ("Edit", {"file_path": "src/a.py", "old_string": "x", "new_string": f"KEY = '{FAKE_AWS_KEY}'"}),
        "deny",
    ),
    (
        "mcp-list",
        ("call_mcp_tool", {"ServerName": "fabric-mcp-server", "ToolName": "core_list-workspaces"}),
        ("mcp__fabric-mcp-server__core_list-workspaces", {}),
        "allow",
    ),
    (
        "mcp-delete",
        ("call_mcp_tool", {"ServerName": "fabric-mcp-server", "ToolName": "delete_workspace"}),
        ("mcp__fabric-mcp-server__delete_workspace", {}),
        "deny",
    ),
    (
        "mcp-create",
        ("call_mcp_tool", {"ServerName": "aws-mcp", "ToolName": "create_bucket"}),
        ("mcp__aws-mcp__create_bucket", {}),
        "force_ask",
    ),
]

CLAUDE_EQUIV = {"allow": "allow", "deny": "deny", "force_ask": "ask"}


def _clean_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "CLAUDE_PROJECT_DIR",
            "CLAUDE_PLUGIN_ROOT",
            "CLAUDE_PLUGIN_DATA",
            "PLUGIN_ROOT",
            "PLUGIN_DATA",
        }
    }
    env["PLUGIN_DATA"] = str(tmp_path / "plugin_data")
    env.update(extra)
    return env


def _run_hook(script: Path, payload: dict | str, env: dict[str, str]) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(script)], input=data, env=env, capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    ("case", "ag_call", "claude_call", "expected"), PARITY_CASES, ids=[c[0] for c in PARITY_CASES]
)
def test_gate_decision_parity(tmp_path: Path, case: str, ag_call, claude_call, expected: str) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    env = _clean_env(tmp_path, CLAUDE_PROJECT_DIR=str(ws))

    ag_payload = {
        "conversationId": case,
        "workspacePaths": [str(ws)],
        "toolCall": {"name": ag_call[0], "args": ag_call[1]},
    }
    ag = _run_hook(AG_GATE, ag_payload, env)
    assert ag.returncode == 0, ag.stderr
    ag_decision = json.loads(ag.stdout)["decision"]
    assert ag_decision == expected

    cl_payload = {
        "session_id": case,
        "cwd": str(ws),
        "hook_event_name": "PreToolUse",
        "tool_name": claude_call[0],
        "tool_input": claude_call[1],
    }
    cl = _run_hook(CLAUDE_GATE, cl_payload, env)
    assert cl.returncode == 0, cl.stderr
    out = json.loads(cl.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert out["permissionDecision"] == CLAUDE_EQUIV[ag_decision]
    if ag_decision != "allow":
        assert out["permissionDecisionReason"]


def test_claude_gate_fails_closed_on_invalid_input(tmp_path: Path) -> None:
    proc = _run_hook(CLAUDE_GATE, "{isto nao e json", _clean_env(tmp_path))
    assert proc.returncode == 2
    assert "GATE-ERROR" in proc.stderr


def test_claude_telemetry_and_bootstrap_adapters(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    (ws / "ops" / "telemetry").mkdir(parents=True)
    (ws / "specs" / "active").mkdir(parents=True)
    (ws / "specs" / "active" / "SPEC-009-x.md").write_text("---\nstatus: DRAFT\n---\n", encoding="utf-8")
    env = _clean_env(tmp_path, CLAUDE_PROJECT_DIR=str(ws))

    tel = _run_hook(
        REPO_ROOT / ".claude" / "hooks" / "claude_telemetry.py",
        {
            "session_id": "s1",
            "tool_name": "Bash",
            "tool_input": {"command": "uv run pytest"},
            "tool_response": "ok",
        },
        env,
    )
    assert tel.returncode == 0, tel.stderr
    stop = _run_hook(REPO_ROOT / ".claude" / "hooks" / "claude_stop.py", {"session_id": "s1"}, env)
    assert stop.returncode == 0, stop.stderr
    events = [
        json.loads(line)
        for line in (ws / "ops" / "telemetry" / "events.jsonl").read_text("utf-8").splitlines()
    ]
    assert [e["eventType"] for e in events] == ["POST_TOOL_USE", "TURN_STOP"]
    assert events[0]["toolName"] == "run_command" and events[0]["summary"]["binary"] == "uv"
    assert all(e["harness"] == "claude-code" for e in events)

    boot = _run_hook(REPO_ROOT / ".claude" / "hooks" / "claude_bootstrap.py", {"cwd": str(ws)}, env)
    ctx = json.loads(boot.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "SPEC-009-x.md [status=DRAFT]" in ctx


def test_generated_claude_artifacts_are_in_sync() -> None:
    proc = subprocess.run(
        [sys.executable, str(WARMUP), "sync-claude", "--check", "--source-dir", str(REPO_ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["inSync"] is True


def test_generated_agents_enforce_two_level_hierarchy() -> None:
    agents = list((REPO_ROOT / ".claude" / "agents").rglob("*.md"))
    src_root = REPO_ROOT / ".agents" / "agents"
    src_agents = list(src_root.rglob("*.md"))
    assert len(agents) == len(src_agents) >= 10
    leaves = [
        p for p in src_agents if "\nrole_type: subagent\n" in p.read_text(encoding="utf-8")
    ]
    assert len(leaves) >= 1
    for src in leaves:
        generated = REPO_ROOT / ".claude" / "agents" / src.relative_to(src_root)
        assert "\ndisallowedTools: Agent\n" in generated.read_text(encoding="utf-8")
    managers = [p for p in agents if "disallowedTools" not in p.read_text(encoding="utf-8")]
    assert len(managers) == len(src_agents) - len(leaves)


STUB_CLAUDE = r"""
import json, os, sys
schema = json.loads(sys.argv[sys.argv.index("--json-schema") + 1])
sys.stdin.read()
req = set(schema.get("required", []))
verdict = os.environ.get("STUB_VERDICT", "APPROVED")
if "references" in req:
    out = {"domain": "ds", "references": [], "statistical_premises": [], "operational_premises": [],
           "mandatory_diagnostic_tests": ["psi"], "fallback_methods": []}
elif "tasks" in req:
    out = {"summary": "plano", "clouds_involved": ["aws"], "tasks": [], "verification_plan": [],
           "rollback_plan": "r",
           "finops_estimate": {"cloud_cost_controls": [], "llm_model_tiering": "pro"}}
elif "blockers" in req:
    out = {"review_summary": "ok", "blockers": [], "majors": [], "minors": [], "ready_for_governance": True}
elif "verdict" in req:
    out = {"verdict": verdict, "rules_checked": [], "violations": [], "conditions": [], "rationale": "r"}
else:
    out = {}
print(json.dumps({"result": "", "structured_output": out}))
"""


@pytest.mark.parametrize(
    ("verdict", "status"), [("APPROVED", "READY_FOR_HUMAN_APPROVAL"), ("REJECTED", "ESCALATED_TO_HUMAN")]
)
def test_run_spec_cycle_executes_original_orchestrator(tmp_path: Path, verdict: str, status: str) -> None:
    ws = tmp_path / "ws"
    (ws / "specs" / "active").mkdir(parents=True)
    spec_rel = "specs/active/SPEC-001-test.md"
    (ws / spec_rel).write_text((REPO_ROOT / SPEC_001).read_text("utf-8"), encoding="utf-8")
    stub = tmp_path / "stub_claude.py"
    stub.write_text(STUB_CLAUDE, encoding="utf-8")
    env = _clean_env(tmp_path, CLAUDE_BIN=str(stub), STUB_VERDICT=verdict)
    proc = subprocess.run(
        [sys.executable, str(RUN_SPEC), "--spec", spec_rel, "--workspace", str(ws), "--max-plan-cycles", "2"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["status"] == status


def test_install_claude_code_target_builds_plugin(tmp_path: Path) -> None:
    claude_dir = tmp_path / "claude_plugin"
    ag_dir = tmp_path / "ag_plugin"
    subprocess.run(
        [
            sys.executable,
            str(WARMUP),
            "install",
            "--source-dir",
            str(REPO_ROOT),
            "--target",
            "claude-code",
            "--claude-target-dir",
            str(claude_dir),
            "--target-dir",
            str(ag_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert not ag_dir.exists(), "--target claude-code não deve tocar o plugin Antigravity"
    assert (
        json.loads((claude_dir / ".claude-plugin" / "plugin.json").read_text("utf-8"))["name"]
        == "analytics-agent"
    )
    hooks = json.loads((claude_dir / "hooks" / "hooks.json").read_text("utf-8"))["hooks"]
    assert hooks["PreToolUse"][0]["hooks"][0]["onFailure"] == "block"
    expected_agents = len(list((REPO_ROOT / ".agents" / "agents").rglob("*.md")))
    assert len(list((claude_dir / "agents").glob("*.md"))) == expected_agents
    assert sum(1 for p in (claude_dir / "skills").iterdir() if p.is_dir()) >= 20
    assert (claude_dir / ".mcp.json").exists()
    assert (claude_dir / "workflows" / "run_spec_cycle.py").exists()
    assert (claude_dir / "workflows" / "data_task_orchestrator.py").exists()

    # Gate em modo plugin Claude sobre workspace externo sem policy.json local
    ext = tmp_path / "external"
    ext.mkdir()
    env = _clean_env(
        tmp_path,
        CLAUDE_PLUGIN_ROOT=str(claude_dir),
        CLAUDE_PLUGIN_DATA=str(tmp_path / "cdata"),
        CLAUDE_PROJECT_DIR=str(ext),
    )
    env.pop("PLUGIN_DATA")
    proc = _run_hook(
        claude_dir / "claude_hooks" / "claude_gate.py",
        {"tool_name": "Bash", "tool_input": {"command": "aws s3 rm s3://prod --recursive"}, "cwd": str(ext)},
        env,
    )
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert (tmp_path / "cdata" / "telemetry" / "events.jsonl").exists()
    assert not (ext / "ops").exists()


def test_install_claude_code_refuses_foreign_nonempty_dir(tmp_path: Path) -> None:
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("dados", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(WARMUP),
            "install",
            "--source-dir",
            str(REPO_ROOT),
            "--target",
            "claude-code",
            "--claude-target-dir",
            str(foreign),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert (foreign / "keep.txt").exists()


def test_marketplace_points_to_committed_plugin() -> None:
    marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text("utf-8"))
    assert marketplace["owner"]["name"]
    (entry,) = marketplace["plugins"]
    assert entry["source"].startswith("./")
    plugin_dir = REPO_ROOT / entry["source"]
    manifest = json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    assert manifest["name"] == entry["name"] == "analytics-agent"
    assert "version" not in manifest  # atualização pelo SHA do commit (marketplace git)
    assert (plugin_dir / "hooks" / "hooks.json").exists()
    expected_agents = len(list((REPO_ROOT / ".agents" / "agents").rglob("*.md")))
    assert len(list((plugin_dir / "agents").glob("*.md"))) == expected_agents


def test_generated_agent_descriptions_are_quoted_yaml() -> None:
    for agent in (REPO_ROOT / ".claude" / "agents").rglob("*.md"):
        line = next(ln for ln in agent.read_text("utf-8").splitlines() if ln.startswith("description: "))
        assert json.loads(line.removeprefix("description: ")), agent.name


@pytest.mark.skipif(shutil.which("claude") is None, reason="CLI `claude` indisponível")
@pytest.mark.parametrize("target", [".", "plugins/analytics-agent", ".claude"])
def test_claude_cli_validates_plugin_and_marketplace(target: str) -> None:
    proc = subprocess.run(
        [shutil.which("claude") or "claude", "plugin", "validate", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
