"""Gerador da camada Claude Code a partir da fonte única de verdade do harness (`.agents/`).

Gera, sem alterar nada consumido pelo Antigravity:
  - `.claude/skills/<skill>/SKILL.md`   (cópia fiel dos SKILL.md de `.agents/skills/`)
  - `.claude/agents/<dominio>/<nome>.md` (frontmatter traduzido para campos do Claude Code)
  - `.mcp.json` (a partir de `.agents/plugins/multicloud-mcp-connectors/mcp_config.json`)

Uso:
  uv run scripts/warmup.py sync-claude            # regenera
  uv run scripts/warmup.py sync-claude --check    # falha (exit 1) se houver divergência (CI)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

GENERATED_MARKER = "<!-- GERADO por `warmup.py sync-claude` a partir de {source} — NÃO EDITE. -->"
MCP_SOURCE = Path(".agents/plugins/multicloud-mcp-connectors/mcp_config.json")
MODEL_MAP_PATH = Path(".claude/model_map.json")

DEFAULT_MODEL_MAP: dict[str, dict[str, str]] = {
    "gemini4": {"Carbon": "opus", "Neon": "sonnet", "Hydrogen": "haiku", "Argon": "sonnet"},
    "tier": {"pro": "opus", "flash": "sonnet", "flash_lite": "haiku"},
}

# Valores de `permissionMode` usados em `.agents/agents/` que também existem no Claude Code.
SUPPORTED_PERMISSION_MODES = {"default", "plan"}


@dataclass
class SyncResult:
    files: dict[Path, str] = field(default_factory=dict)  # caminho relativo -> conteúdo esperado

    def add(self, rel: Path, content: str) -> None:
        self.files[rel] = content


def load_model_map(root: Path) -> dict[str, dict[str, str]]:
    path = root / MODEL_MAP_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return DEFAULT_MODEL_MAP


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Parser mínimo (stdlib) para o frontmatter usado em `.agents/agents/`: escalares e listas `- item`."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict[str, object] = {}
    current_list: list[str] | None = None
    end = None
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = idx
            break
        stripped = line.strip()
        if stripped.startswith("- ") and current_list is not None:
            current_list.append(stripped[2:].strip())
            continue
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            value = value.strip()
            if value:
                meta[key.strip()] = value
                current_list = None
            else:
                current_list = []
                meta[key.strip()] = current_list
    if end is None:
        return {}, text
    body = "\n".join(lines[end + 1 :])
    return meta, body


def translate_model(meta: dict[str, object], model_map: dict[str, dict[str, str]]) -> str:
    gem = str(meta.get("gemini4_model", ""))
    for family, claude_model in model_map["gemini4"].items():
        if family in gem:
            return claude_model
    return model_map["tier"].get(str(meta.get("model", "")), "inherit")


def render_agent(
    meta: dict[str, object], body: str, source_rel: str, model_map: dict[str, dict[str, str]]
) -> str:
    out = ["---", f"name: {meta['name']}", f"description: {meta['description']}"]
    out.append(f"model: {translate_model(meta, model_map)}")

    is_leaf = meta.get("role_type") == "subagent"
    if meta.get("permissionMode") in SUPPORTED_PERMISSION_MODES:
        out.append(f"permissionMode: {meta['permissionMode']}")
    if is_leaf:
        # Profundidade máxima = 2 níveis (policy.json: maxAgentHierarchyDepth): folhas não podem spawnar.
        out.append("disallowedTools: Agent")

    skills = meta.get("skills")
    if isinstance(skills, list) and skills:
        out.append("skills:")
        out.extend(f"  - {s}" for s in skills)
    out.append("---")
    out.append(GENERATED_MARKER.format(source=source_rel))

    sub = meta.get("subagents")
    if isinstance(sub, list) and sub:
        out.append("")
        out.append(
            "> **Claude Code:** delegue aos sub-operadores folha pela ferramenta `Agent` "
            f"(`subagent_type`): {', '.join(sub)}. Somente eles; sem peer-to-peer."
        )
    return "\n".join(out) + "\n" + body.rstrip("\n") + "\n"


def build(root: Path) -> SyncResult:
    result = SyncResult()
    model_map = load_model_map(root)

    # Skills: cópia fiel
    for skill_md in sorted((root / ".agents" / "skills").glob("*/SKILL.md")):
        rel = Path(".claude/skills") / skill_md.parent.name / "SKILL.md"
        result.add(rel, skill_md.read_text(encoding="utf-8"))

    # Agentes: frontmatter traduzido
    agents_root = root / ".agents" / "agents"
    for agent_md in sorted(agents_root.rglob("*.md")):
        meta, body = parse_frontmatter(agent_md.read_text(encoding="utf-8"))
        if "name" not in meta or "description" not in meta:
            raise ValueError(f"Agente sem name/description: {agent_md}")
        source_rel = agent_md.relative_to(root).as_posix()
        rel = Path(".claude/agents") / agent_md.relative_to(agents_root)
        result.add(rel, render_agent(meta, body, source_rel, model_map))

    # MCP
    mcp_src = root / MCP_SOURCE
    if mcp_src.exists():
        data = json.loads(mcp_src.read_text(encoding="utf-8"))
        result.add(Path(".mcp.json"), json.dumps({"mcpServers": data.get("mcpServers", {})}, indent=2) + "\n")
    return result


def managed_dirs() -> list[Path]:
    return [Path(".claude/skills"), Path(".claude/agents")]


def find_drift(root: Path, result: SyncResult) -> list[str]:
    drift: list[str] = []
    for rel, content in result.files.items():
        path = root / rel
        if not path.exists():
            drift.append(f"ausente: {rel.as_posix()}")
        elif path.read_text(encoding="utf-8") != content:
            drift.append(f"divergente: {rel.as_posix()}")
    expected = {rel.as_posix() for rel in result.files}
    for d in managed_dirs():
        base = root / d
        if base.exists():
            for p in base.rglob("*.md"):
                rel = p.relative_to(root).as_posix()
                if rel not in expected:
                    drift.append(f"órfão: {rel}")
    return sorted(drift)


def write(root: Path, result: SyncResult) -> int:
    for orphan in find_drift(root, result):
        if orphan.startswith("órfão: "):
            (root / orphan.removeprefix("órfão: ")).unlink()
    for rel, content in result.files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
    return len(result.files)


def run(root: Path, check: bool) -> int:
    result = build(root)
    if check:
        drift = find_drift(root, result)
        print(json.dumps({"inSync": not drift, "drift": drift}, ensure_ascii=False, indent=2))
        return 1 if drift else 0
    count = write(root, result)
    print(json.dumps({"generatedFiles": count}, ensure_ascii=False))
    return 0
