#!/usr/bin/env python3
"""Diagnóstico read-only da stack MCP (Fabric + AWS), runtimes, sessões CLI e TLS.

Nunca expõe tokens/segredos na saída e nunca desativa verificação TLS.
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


def run_readonly(cmd: list[str], timeout: int = 15) -> dict:
    binary = shutil.which(cmd[0])
    if not binary:
        return {"ok": False, "error": f"Binário não encontrado no PATH: {cmd[0]}"}
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip()[:400],
            "stderr": proc.stderr.strip()[:400],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


def check_python_version() -> dict:
    v = sys.version_info
    is_313_plus = (v.major, v.minor) >= (3, 13)
    return {
        "version": f"{v.major}.{v.minor}.{v.micro}",
        "compatibleWithStrictCorpProxy": not is_313_plus,
        "warning": (
            "Python 3.13+ ativa validação estrita X.509 (basicConstraints). "
            "Use Python 3.11 ou 3.12 para clientes REST/SQL Fabric e uvx --python 3.12."
            if is_313_plus
            else ""
        ),
    }


def check_tls_env() -> dict:
    forbidden_flags = []
    if os.environ.get("NODE_TLS_REJECT_UNAUTHORIZED") == "0":
        forbidden_flags.append("NODE_TLS_REJECT_UNAUTHORIZED=0")
    if os.environ.get("AZURE_CLI_DISABLE_CONNECTION_VERIFICATION"):
        forbidden_flags.append("AZURE_CLI_DISABLE_CONNECTION_VERIFICATION")
    return {
        "requestsCaBundleSet": bool(os.environ.get("REQUESTS_CA_BUNDLE")),
        "sslCertFileSet": bool(os.environ.get("SSL_CERT_FILE")),
        "nodeExtraCaCertsSet": bool(os.environ.get("NODE_EXTRA_CA_CERTS")),
        "forbiddenTlsBypassDetected": forbidden_flags,
        "compliant": len(forbidden_flags) == 0,
    }


def probe_aws_mcp_stdio(python_pin: str | None = None, timeout: int = 25) -> dict:
    uvx_bin = shutil.which("uvx")
    if not uvx_bin:
        return {"ok": False, "error": "uvx não encontrado no PATH."}

    cmd = [uvx_bin]
    if python_pin:
        cmd.extend(["--python", python_pin])
    cmd.extend(
        [
            "mcp-proxy-for-aws@latest",
            "https://aws-mcp.us-east-1.api.aws/mcp",
            "--metadata",
            "INSTALL_SOURCE=aws-cli",
        ]
    )

    init_req = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "analytics-agent-probe", "version": "1.0.0"},
            },
        }
    )
    list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    stdin_payload = f"{init_req}\n{list_req}\n"

    try:
        proc = subprocess.run(
            cmd,
            input=stdin_payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        responses = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    responses.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        server_name = ""
        tool_count = 0
        for r in responses:
            res = r.get("result") or {}
            if "serverInfo" in res:
                server_name = res["serverInfo"].get("name", "")
            if "tools" in res and isinstance(res["tools"], list):
                tool_count = len(res["tools"])
        return {
            "ok": bool(server_name) or tool_count > 0,
            "serverName": server_name,
            "toolCount": tool_count,
            "stderrSample": proc.stderr.strip()[:300],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificação read-only de ambiente MCP (Fabric + AWS).")
    parser.add_argument("--output", required=True, help="Arquivo JSON de saída do diagnóstico.")
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="Verifica também sessões ativas de az login (token Fabric) e aws sts get-caller-identity.",
    )
    parser.add_argument(
        "--probe-aws-mcp",
        action="store_true",
        help="Executa probe JSON-RPC (initialize + tools/list) via stdio contra aws-mcp.",
    )
    parser.add_argument(
        "--python-pin",
        default="",
        help="Opcional: fixa versão Python no probe uvx (ex.: 3.12).",
    )
    args = parser.parse_args()

    report: dict = {
        "generatedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pythonRuntime": check_python_version(),
        "tlsCompliance": check_tls_env(),
        "binaries": {
            "node": run_readonly(["node", "--version"]),
            "npx": run_readonly(["npx", "--version"]),
            "uv": run_readonly(["uv", "--version"]),
            "uvx": run_readonly(["uvx", "--version"]),
            "az": run_readonly(["az", "--version"]),
            "aws": run_readonly(["aws", "--version"]),
        },
    }

    if args.check_auth:
        # Apenas metadados de sessão (nunca imprime o accessToken em si!)
        az_account = run_readonly(
            ["az", "account", "show", "--query", "{userType:user.type, state:state}", "-o", "json"]
        )
        az_token_exp = run_readonly(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                "https://api.fabric.microsoft.com",
                "--query",
                "expiresOn",
                "-o",
                "tsv",
            ]
        )
        aws_sts = run_readonly(["aws", "sts", "get-caller-identity", "--query", "Arn", "--output", "text"])
        # Mascara ID de conta AWS caso retornado para evitar vazamento desnecessário em logs compartilhados
        if aws_sts.get("ok") and aws_sts.get("stdout"):
            parts = aws_sts["stdout"].split(":")
            if len(parts) >= 5 and parts[4].isdigit():
                parts[4] = "***REDACTED***"
                aws_sts["stdout"] = ":".join(parts)

        report["authSessions"] = {
            "azureAccount": az_account,
            "fabricTokenExpiresOn": az_token_exp,
            "awsStsIdentity": aws_sts,
        }

    if args.probe_aws_mcp:
        report["awsMcpProbe"] = probe_aws_mcp_stdio(python_pin=args.python_pin or None)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    tls_ok = report["tlsCompliance"]["compliant"]
    py_ok = report["pythonRuntime"]["compatibleWithStrictCorpProxy"]
    print(f"Diagnóstico MCP gravado em: {out_path} (tls_ok={tls_ok}, py_311_312={py_ok})")
    return 0 if tls_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
