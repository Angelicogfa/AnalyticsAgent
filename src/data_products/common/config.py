"""Configuração segura para produtos de dados multi-cloud (zero segredos hardcoded, zero bypass TLS).

SPEC-ID: SPEC-000
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuração de ambiente imutável carregada exclusivamente de variáveis de ambiente."""

    env: str
    aws_region: str
    fabric_workspace_id: str | None
    fabric_lakehouse_id: str | None
    ca_bundle_path: Path | None

    @classmethod
    def from_env(cls) -> RuntimeConfig:
        if os.environ.get("NODE_TLS_REJECT_UNAUTHORIZED") == "0":
            raise RuntimeError("Violação P0 (RULE-05): NODE_TLS_REJECT_UNAUTHORIZED=0 é proibido.")
        if os.environ.get("AZURE_CLI_DISABLE_CONNECTION_VERIFICATION"):
            raise RuntimeError("Violação P0 (RULE-05): AZURE_CLI_DISABLE_CONNECTION_VERIFICATION é proibido.")

        ca_raw = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or ""
        ca_path = Path(ca_raw) if ca_raw.strip() else None

        return cls(
            env=os.environ.get("DATA_PRODUCT_ENV", "dev").strip().lower(),
            aws_region=os.environ.get("AWS_REGION", "us-east-1").strip(),
            fabric_workspace_id=os.environ.get("FABRIC_WORKSPACE_ID") or None,
            fabric_lakehouse_id=os.environ.get("FABRIC_LAKEHOUSE_ID") or None,
            ca_bundle_path=ca_path,
        )

    def tls_verify_arg(self) -> str | bool:
        """Retorna caminho de bundle CA confiável ou True (jamais False)."""
        if self.ca_bundle_path is not None:
            return str(self.ca_bundle_path)
        return True
