#!/usr/bin/env python3
"""Estimador determinístico de FinOps Multi-Cloud (AWS + Microsoft Fabric) e tokens Gemini 4."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

# Referências públicas aproximadas em USD (usadas para ordem de grandeza e comparação entre opções)
ATHENA_USD_PER_TB = 5.00
AWS_INTERNET_EGRESS_USD_PER_GB = 0.09
FABRIC_CU_SECOND_USD = 0.18 / 3600.0  # ~US$ 0.18 por CU-hora pay-as-you-go (referência)

LLM_USD_PER_1M = {
    "carbon": (4.00, 20.00),
    "argon": (4.00, 20.00),
    "neon": (3.00, 15.00),
    "hydrogen": (1.50, 7.50),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_policy(root: Path) -> dict:
    p = root / "ops" / "governance" / "policy.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def parse_bool(val: str) -> bool:
    return val.strip().lower() in {"1", "true", "yes", "sim"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimador determinístico de FinOps Multi-Cloud e LLM.")
    parser.add_argument("--athena-scan-gb", type=float, default=0.0)
    parser.add_argument("--aws-egress-gb", type=float, default=0.0)
    parser.add_argument("--s3-shortcut-cache", type=parse_bool, default=True)
    parser.add_argument("--fabric-cu-seconds", type=float, default=0.0)
    parser.add_argument("--llm-model", choices=list(LLM_USD_PER_1M.keys()), default="neon")
    parser.add_argument("--llm-input-k", type=float, default=0.0, help="Milhares de tokens de entrada")
    parser.add_argument("--llm-output-k", type=float, default=0.0, help="Milhares de tokens de saída")
    parser.add_argument("--output", required=True, help="Arquivo JSON de saída")
    args = parser.parse_args()

    policy = load_policy(repo_root()).get("finops", {})
    max_athena_gb = float(policy.get("maxAthenaScanGbWithoutApproval", 50))
    max_fabric_cu_s = float(policy.get("maxFabricCuSecondsPerJob", 3600))

    athena_usd = (args.athena_scan_gb / 1024.0) * ATHENA_USD_PER_TB
    egress_raw_usd = args.aws_egress_gb * AWS_INTERNET_EGRESS_USD_PER_GB
    # Com S3 Shortcut Cache ativo em leituras repetidas, estima-se redução conservadora de 75% de egress
    egress_effective_usd = egress_raw_usd * (0.25 if args.s3_shortcut_cache else 1.0)
    fabric_usd = args.fabric_cu_seconds * FABRIC_CU_SECOND_USD

    in_rate, out_rate = LLM_USD_PER_1M[args.llm_model]
    llm_usd = (args.llm_input_k / 1000.0) * in_rate + (args.llm_output_k / 1000.0) * out_rate

    flags: list[str] = []
    if args.athena_scan_gb > max_athena_gb:
        flags.append(f"REQUIRES_APPROVAL: Athena scan ({args.athena_scan_gb} GB) excede limite ({max_athena_gb} GB).")
    if args.fabric_cu_seconds > max_fabric_cu_s:
        flags.append(
            f"REQUIRES_APPROVAL: Fabric CU-seconds ({args.fabric_cu_seconds}) excede limite ({max_fabric_cu_s})."
        )
    if args.aws_egress_gb > 0 and not args.s3_shortcut_cache:
        flags.append("FINOPS_WARNING: Egress AWS->Azure sem OneLake S3 Shortcut Cache habilitado.")

    total_usd = round(athena_usd + egress_effective_usd + fabric_usd + llm_usd, 4)
    report = {
        "generatedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {
            "athenaScanGb": args.athena_scan_gb,
            "awsEgressGb": args.aws_egress_gb,
            "s3ShortcutCache": args.s3_shortcut_cache,
            "fabricCuSeconds": args.fabric_cu_seconds,
            "llmModel": args.llm_model,
            "llmInputKTokens": args.llm_input_k,
            "llmOutputKTokens": args.llm_output_k,
        },
        "estimatedUsd": {
            "awsAthena": round(athena_usd, 4),
            "awsEgressEffective": round(egress_effective_usd, 4),
            "awsEgressWithoutCache": round(egress_raw_usd, 4),
            "azureFabricCu": round(fabric_usd, 4),
            "llmTokens": round(llm_usd, 4),
            "totalEstimatedUsd": total_usd,
        },
        "policyLimits": {
            "maxAthenaScanGbWithoutApproval": max_athena_gb,
            "maxFabricCuSecondsPerJob": max_fabric_cu_s,
        },
        "flags": flags,
        "withinAutoApprovalBudget": not any(f.startswith("REQUIRES_APPROVAL") for f in flags),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Estimativa FinOps gravada em: {out} "
        f"(total_usd=${total_usd:.4f}, within_budget={report['withinAutoApprovalBudget']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
