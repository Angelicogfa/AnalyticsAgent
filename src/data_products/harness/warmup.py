#!/usr/bin/env python3
"""CLI Dual-Mode do AnalyticsAgent: instala/atualiza o Plugin Global no Antigravity e faz warmup sem copiar o repo.

Uso em instância crua do Antigravity (1 comando):
  uvx --from git+https://github.com/<org>/AnalyticsAgent analytics-agent-warmup install --repo-url https://github.com/<org>/AnalyticsAgent.git

Uso local (dentro de um clone):
  uv run scripts/warmup.py install
  uv run scripts/warmup.py init-workspace --workspace /caminho/do/seu-projeto
  uv run scripts/warmup.py status
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_NAME = "analytics-agent"
PLUGIN_VERSION = "0.2.0"
MAX_RULE_FILE_BYTES = 24_000


def default_plugin_dir() -> Path:
    return Path.home() / ".gemini" / "config" / "plugins" / PLUGIN_NAME


def default_source_cache_dir() -> Path:
    return Path.home() / ".gemini" / "config" / "plugins" / ".sources" / PLUGIN_NAME


def detect_local_repo_root() -> Path | None:
    # Sobe a partir deste arquivo (src/data_products/harness/warmup.py -> repo root)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".agents" / "hooks.json").exists() and (parent / "AGENTS.md").exists():
            return parent
    cwd = Path.cwd()
    if (cwd / ".agents" / "hooks.json").exists() and (cwd / "AGENTS.md").exists():
        return cwd
    return None


def sync_git_repo(repo_url: str, cache_dir: Path, branch: str | None = None) -> Path:
    git_bin = shutil.which("git")
    if not git_bin:
        raise RuntimeError("Git não encontrado no PATH; necessário para pull via --repo-url.")
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    if (cache_dir / ".git").exists():
        subprocess.run([git_bin, "-C", str(cache_dir), "fetch", "--all", "--prune"], check=True)
        if branch:
            subprocess.run([git_bin, "-C", str(cache_dir), "checkout", branch], check=True)
        subprocess.run([git_bin, "-C", str(cache_dir), "pull", "--ff-only"], check=True)
    else:
        cmd = [git_bin, "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([repo_url, str(cache_dir)])
        subprocess.run(cmd, check=True)
    return cache_dir


def build_consolidated_rules(source_root: Path) -> str:
    parts: list[str] = []
    root_agents = source_root / "AGENTS.md"
    if root_agents.exists():
        parts.append(root_agents.read_text(encoding="utf-8").strip())

    rules_dir = source_root / ".agents" / "rules"
    if rules_dir.exists():
        for rf in sorted(rules_dir.glob("*.md")):
            parts.append(rf.read_text(encoding="utf-8").strip())

    combined = "\n\n---\n\n".join(parts) + "\n"
    size_bytes = len(combined.encode("utf-8"))
    if size_bytes >= MAX_RULE_FILE_BYTES:
        raise ValueError(
            f"rules/AGENTS.md consolidado excedeu o limite do Antigravity "
            f"({size_bytes} bytes >= {MAX_RULE_FILE_BYTES} bytes). Pode regras redundantes antes de empacotar."
        )
    return combined


def assemble_plugin(source_root: Path, target_dir: Path, include_mcp: bool = True) -> dict:
    """Monta o bundle nativo de Plugin do Antigravity a partir da fonte única (.agents/)."""
    agents_src = source_root / ".agents"
    if not agents_src.exists():
        raise FileNotFoundError(f"Diretório .agents não encontrado na origem: {source_root}")

    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Manifesto oficial plugin.json (apenas campos reconhecidos pelo loader do Antigravity)
    manifest = {
        "name": PLUGIN_NAME,
        "displayName": "AnalyticsAgent Multi-Cloud Data Operator",
        "description": (
            "Rede cooperativa de 22 agentes (4 Domain Managers + 12 sub-operadores leaf), 20 skills, "
            "regras P0/FinOps, hooks determinísticos e MCPs para Microsoft Fabric, AWS e Power BI PBIP."
        ),
        "version": PLUGIN_VERSION,
        "suggestedPrompts": [
            "Faça o warmup deste projeto com project-warmup e crie nossa primeira SPEC de dados",
            "Valide o ambiente MCP (Fabric, AWS, Power BI), Python 3.12 e TLS em modo read-only",
            "Audite meus arquivos .pbip/TMDL ou contratos ODCS v3 com os pré-checks determinísticos",
        ],
    }
    (target_dir / "plugin.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 2. Rules consolidadas (< 24 KB garantido)
    rules_dir = target_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    consolidated_rules = build_consolidated_rules(source_root)
    (rules_dir / "AGENTS.md").write_text(consolidated_rules, encoding="utf-8")

    # 3. Agents achatados em 1 nível (descoberta 100% nativa em plugins Antigravity)
    agents_dst = target_dir / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    agent_count = 0
    for agent_md in sorted((agents_src / "agents").rglob("*.md")):
        shutil.copy2(agent_md, agents_dst / agent_md.name)
        agent_count += 1

    # 4. Skills
    skills_dst = target_dir / "skills"
    shutil.copytree(agents_src / "skills", skills_dst)
    skill_count = sum(1 for p in skills_dst.iterdir() if p.is_dir())

    # 5. Hooks + política padrão empacotada (fallback para PLUGIN_ROOT)
    shutil.copy2(agents_src / "hooks.json", target_dir / "hooks.json")
    shutil.copytree(agents_src / "hooks", target_dir / "hooks")

    policy_src = source_root / "ops" / "governance" / "policy.json"
    if policy_src.exists():
        (target_dir / "ops" / "governance").mkdir(parents=True, exist_ok=True)
        shutil.copy2(policy_src, target_dir / "ops" / "governance" / "policy.json")

    # 6. Workflows + templates de referência (para init-workspace sem precisar do repo original)
    if (agents_src / "workflows").exists():
        shutil.copytree(agents_src / "workflows", target_dir / "workflows")
    for tpl_rel in ("specs/templates", "contracts/templates", "knowledge/templates"):
        src_tpl = source_root / tpl_rel
        if src_tpl.exists():
            shutil.copytree(src_tpl, target_dir / "templates" / tpl_rel.split("/")[0])

    # 7. MCP Config (Fabric + AWS + Power BI Desktop)
    mcp_servers: list[str] = []
    mcp_src = agents_src / "plugins" / "multicloud-mcp-connectors" / "mcp_config.json"
    if include_mcp and mcp_src.exists():
        shutil.copy2(mcp_src, target_dir / "mcp_config.json")
        mcp_data = json.loads(mcp_src.read_text(encoding="utf-8"))
        mcp_servers = sorted(mcp_data.get("mcpServers", {}).keys())

    return {
        "pluginDir": str(target_dir),
        "version": PLUGIN_VERSION,
        "agentsBundled": agent_count,
        "skillsBundled": skill_count,
        "rulesBytes": len(consolidated_rules.encode("utf-8")),
        "mcpServers": mcp_servers,
        "hooksEnabled": True,
    }


def run_warmup_checks(source_root: Path | None) -> dict:
    v = sys.version_info
    tls_ok = (
        os.environ.get("NODE_TLS_REJECT_UNAUTHORIZED") != "0"
        and not os.environ.get("AZURE_CLI_DISABLE_CONNECTION_VERIFICATION")
    )
    binaries = {name: bool(shutil.which(name)) for name in ("git", "node", "npx", "uv", "uvx", "az", "aws")}

    kb_indexed = False
    if source_root and (source_root / "knowledge").exists():
        kb_cli = source_root / ".agents" / "skills" / "internal-knowledge-base" / "scripts" / "knowledge_cli.py"
        if kb_cli.exists():
            tmp_out = source_root / "ops" / "telemetry" / "warmup_kb_index.json"
            proc = subprocess.run(
                [sys.executable, str(kb_cli), "index", "--output", str(tmp_out)],
                capture_output=True,
                text=True,
                check=False,
            )
            kb_indexed = proc.returncode == 0
            tmp_out.unlink(missing_ok=True)

    return {
        "pythonVersion": f"{v.major}.{v.minor}.{v.micro}",
        "pythonRule05Compatible": (v.major, v.minor) < (3, 13),
        "tlsCompliant": tls_ok,
        "binariesOnPath": binaries,
        "knowledgeIndexWarmed": kb_indexed,
    }


def cmd_install(args: argparse.Namespace) -> int:
    if args.repo_url:
        source_root = sync_git_repo(args.repo_url, Path(args.cache_dir), branch=args.branch or None)
    elif args.source_dir:
        source_root = Path(args.source_dir).resolve()
    else:
        detected = detect_local_repo_root()
        if not detected:
            print(
                "Erro: não estou dentro de um clone do AnalyticsAgent. Informe --repo-url <git-url> ou --source-dir <dir>.",
                file=sys.stderr,
            )
            return 1
        source_root = detected

    target_dir = Path(args.target_dir).expanduser().resolve()
    bundle_info = assemble_plugin(source_root, target_dir, include_mcp=not args.no_mcp)
    warmup_info = run_warmup_checks(source_root)

    report = {
        "generatedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "global-plugin",
        "sourceRoot": str(source_root),
        "bundle": bundle_info,
        "warmup": warmup_info,
    }

    out_path = Path(args.output) if args.output else (target_dir / "warmup_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"Plugin '{PLUGIN_NAME}' instalado/atualizado em: {target_dir}\n"
        f"  Agentes: {bundle_info['agentsBundled']} | Skills: {bundle_info['skillsBundled']} | "
        f"Rules: {bundle_info['rulesBytes']} bytes | MCPs: {', '.join(bundle_info['mcpServers']) or 'none'}\n"
        f"  Warmup: Python {warmup_info['pythonVersion']} (RULE-05 ok={warmup_info['pythonRule05Compatible']}), "
        f"TLS ok={warmup_info['tlsCompliant']}\n"
        f"  Relatório: {out_path}"
    )
    return 0


def cmd_init_workspace(args: argparse.Namespace) -> int:
    """Inicializa apenas as pastas de trabalho de Produtos de Dados num workspace externo (sem copiar .agents/)."""
    ws = Path(args.workspace).expanduser().resolve()
    ws.mkdir(parents=True, exist_ok=True)

    dirs = [
        "specs/active",
        "specs/archive",
        "contracts",
        "knowledge/inbox",
        "knowledge/data-science",
        "knowledge/statistics",
        "knowledge/data-engineering",
        "knowledge/analytics-bi",
        "knowledge/mlops-backend",
        "src/data_products/common",
        "src/data_products/engineering",
        "src/data_products/science",
        "src/data_products/analytics/pbip",
        "src/data_products/mlops",
        "tests",
    ]
    created_dirs: list[str] = []
    for d in dirs:
        p = ws / d
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created_dirs.append(d)

    # Cria __init__.py mínimos no src-layout caso ausentes
    for pkg in (
        "src/data_products",
        "src/data_products/common",
        "src/data_products/engineering",
        "src/data_products/science",
        "src/data_products/analytics",
        "src/data_products/mlops",
    ):
        init_file = ws / pkg / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Data products package."""\n', encoding="utf-8")

    # Copia templates (specs, contracts, knowledge) a partir do plugin instalado ou repo local, sem copiar .agents/
    template_sources = []
    plugin_dir = Path(args.plugin_dir).expanduser().resolve()
    if (plugin_dir / "templates").exists():
        template_sources = [
            (plugin_dir / "templates" / "specs", ws / "specs" / "templates"),
            (plugin_dir / "templates" / "contracts", ws / "contracts" / "templates"),
            (plugin_dir / "templates" / "knowledge", ws / "knowledge" / "templates"),
        ]
    else:
        local_root = detect_local_repo_root()
        if local_root:
            template_sources = [
                (local_root / "specs" / "templates", ws / "specs" / "templates"),
                (local_root / "contracts" / "templates", ws / "contracts" / "templates"),
                (local_root / "knowledge" / "templates", ws / "knowledge" / "templates"),
            ]

    copied_templates = 0
    for src_t, dst_t in template_sources:
        if src_t.exists() and not dst_t.exists():
            shutil.copytree(src_t, dst_t)
            copied_templates += 1

    result = {
        "workspace": str(ws),
        "createdDirectories": len(created_dirs),
        "templateGroupsCopied": copied_templates,
        "dotAgentsCopied": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    target_dir = Path(args.target_dir).expanduser().resolve()
    if not (target_dir / "plugin.json").exists():
        print(json.dumps({"installed": False, "pluginDir": str(target_dir)}, ensure_ascii=False))
        return 0

    manifest = json.loads((target_dir / "plugin.json").read_text(encoding="utf-8"))
    agents = list((target_dir / "agents").glob("*.md")) if (target_dir / "agents").exists() else []
    skills = [p.name for p in (target_dir / "skills").iterdir() if p.is_dir()] if (target_dir / "skills").exists() else []
    rules_file = target_dir / "rules" / "AGENTS.md"
    mcp_file = target_dir / "mcp_config.json"
    mcps = sorted(json.loads(mcp_file.read_text(encoding="utf-8")).get("mcpServers", {}).keys()) if mcp_file.exists() else []

    info = {
        "installed": True,
        "pluginDir": str(target_dir),
        "name": manifest.get("name"),
        "version": manifest.get("version"),
        "agentsCount": len(agents),
        "skillsCount": len(skills),
        "rulesBytes": rules_file.stat().st_size if rules_file.exists() else 0,
        "mcpServers": mcps,
        "hooksPresent": (target_dir / "hooks.json").exists(),
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="analytics-agent-warmup",
        description="Instalador/Atualizador do Plugin Global AnalyticsAgent e Warmup de Workspaces no Antigravity.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_inst = sub.add_parser("install", help="Faz pull/montagem do Plugin Global em ~/.gemini/config/plugins/analytics-agent")
    p_inst.add_argument("--repo-url", default="", help="URL Git do repositório AnalyticsAgent para pull automático")
    p_inst.add_argument("--branch", default="", help="Branch opcional para checkout/pull")
    p_inst.add_argument("--source-dir", default="", help="Diretório local de origem (padrão: detecta clone atual)")
    p_inst.add_argument("--cache-dir", default=str(default_source_cache_dir()), help="Cache local do clone Git")
    p_inst.add_argument("--target-dir", default=str(default_plugin_dir()), help="Diretório destino do plugin Antigravity")
    p_inst.add_argument("--no-mcp", action="store_true", help="Instala o plugin sem mcp_config.json")
    p_inst.add_argument("--output", default="", help="Caminho opcional do relatório JSON de warmup")
    p_inst.set_defaults(func=cmd_install)

    p_ws = sub.add_parser("init-workspace", help="Prepara pastas de trabalho num projeto externo sem copiar .agents/")
    p_ws.add_argument("--workspace", default=".", help="Diretório do workspace a preparar")
    p_ws.add_argument("--plugin-dir", default=str(default_plugin_dir()), help="Diretório do plugin instalado")
    p_ws.set_defaults(func=cmd_init_workspace)

    p_st = sub.add_parser("status", help="Exibe status da instalação do Plugin Global")
    p_st.add_argument("--target-dir", default=str(default_plugin_dir()), help="Diretório do plugin Antigravity")
    p_st.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
