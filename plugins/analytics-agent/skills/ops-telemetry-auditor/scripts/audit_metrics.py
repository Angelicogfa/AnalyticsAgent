#!/usr/bin/env python3
"""Agrega métricas operacionais, segurança e candidatos a SKILL a partir da telemetria JSONL."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditor de telemetria operacional do AnalyticsAgent.")
    parser.add_argument(
        "--events",
        default="",
        help="Caminho opcional para events.jsonl (padrão: ops/telemetry/events.jsonl)",
    )
    parser.add_argument("--output", required=True, help="Caminho do relatório JSON de saída")
    args = parser.parse_args()

    root = repo_root()
    events_path = Path(args.events) if args.events else (root / "ops" / "telemetry" / "events.jsonl")
    registry_path = root / "ops" / "patterns" / "repetitive_tasks_registry.json"

    total_events = 0
    tool_counts: collections.Counter[str] = collections.Counter()
    tool_errors: collections.Counter[str] = collections.Counter()
    model_counts: collections.Counter[str] = collections.Counter()
    gate_decisions: collections.Counter[str] = collections.Counter()
    gate_rules: collections.Counter[str] = collections.Counter()
    turn_stops: collections.Counter[str] = collections.Counter()

    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            total_events += 1
            ev_type = ev.get("eventType")
            model = ev.get("modelName") or "unknown"
            model_counts[model] += 1

            if ev_type == "POST_TOOL_USE":
                tname = ev.get("toolName") or "unknown"
                tool_counts[tname] += 1
                if ev.get("status") == "ERROR":
                    tool_errors[tname] += 1
            elif ev_type == "PRE_TOOL_GATE":
                gate_decisions[ev.get("decision") or "unknown"] += 1
                gate_rules[ev.get("ruleId") or "unknown"] += 1
            elif ev_type == "TURN_STOP":
                turn_stops[ev.get("terminationReason") or "unknown"] += 1

    skill_candidates = []
    if registry_path.exists():
        reg = json.loads(registry_path.read_text(encoding="utf-8"))
        threshold = int(reg.get("extractionThresholdOccurrences", 2))
        for p in reg.get("patterns", []):
            if int(p.get("occurrences", 0)) >= threshold and not p.get("extractedSkill"):
                skill_candidates.append(
                    {"id": p.get("id"), "name": p.get("name"), "occurrences": p.get("occurrences")}
                )

    total_tool_calls = sum(tool_counts.values())
    total_tool_errors = sum(tool_errors.values())
    error_rate = round(total_tool_errors / total_tool_calls, 4) if total_tool_calls else 0.0

    report = {
        "generatedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "eventsFile": str(events_path),
        "totalEvents": total_events,
        "toolMetrics": {
            "totalCalls": total_tool_calls,
            "totalErrors": total_tool_errors,
            "errorRate": error_rate,
            "callsByTool": dict(tool_counts.most_common()),
            "errorsByTool": dict(tool_errors.most_common()),
        },
        "governanceGates": {
            "decisions": dict(gate_decisions),
            "triggeredRules": dict(gate_rules.most_common()),
        },
        "modelUsageDistribution": dict(model_counts.most_common()),
        "turnTerminationReasons": dict(turn_stops),
        "pendingSkillExtractionCandidates": skill_candidates,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Relatório operacional gravado em: {out_path} (eventos={total_events}, taxa_erro={error_rate})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
