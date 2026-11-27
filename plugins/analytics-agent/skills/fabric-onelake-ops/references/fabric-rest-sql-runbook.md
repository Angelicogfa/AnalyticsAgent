# Runbook Operacional — API REST e SQL Endpoints do Microsoft Fabric

> **Pré-requisito P0 (`RULE-05`):** Execute sempre em **Python 3.11 ou 3.12** (nunca 3.13+ atrás de proxy corporativo), usando credencial local (`az login`) e bundle CA confiável (`REQUESTS_CA_BUNDLE` / `verify=<bundle>`). Jamais desative TLS (`verify=False`).

---

## 1. Emissão de Tokens com `AzureCliCredential` (Zero Segredos)

Dependências recomendadas em venv Python 3.12 (sem necessidade de driver ODBC):
- `azure-identity`
- `requests`
- `mssql-python`

Escopos Entra ID oficiais:
- **Fabric REST API:** `https://api.fabric.microsoft.com/.default`
- **Fabric SQL Analytics Endpoint (TDS):** `https://database.windows.net/.default`

```python
import os
import struct
import requests
from azure.identity import AzureCliCredential

FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
SQL_SCOPE = "https://database.windows.net/.default"
SQL_COPT_SS_ACCESS_TOKEN = 1256

cred = AzureCliCredential()
ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE", True)  # nunca False!

def get_fabric_headers() -> dict[str, str]:
    token = cred.get_token(FABRIC_SCOPE).token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
```

---

## 2. Descobrir `connectionString` do SQL Endpoint

> **Armadilha conhecida:** `GET /v1/workspaces/{workspaceId}/sqlEndpoints/{sqlEndpointId}` **não** retorna `connectionString`.

Leia sempre pelo recurso **Lakehouse**:

```python
def get_lakehouse_sql_endpoint(workspace_id: str, lakehouse_id: str) -> tuple[str, str]:
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses/{lakehouse_id}"
    resp = requests.get(url, headers=get_fabric_headers(), verify=ca_bundle, timeout=30)
    resp.raise_for_status()
    sql_props = resp.json()["properties"]["sqlEndpointProperties"]
    return sql_props["id"], sql_props["connectionString"]
```

---

## 3. Sincronização de Metadados do SQL Endpoint (`refreshMetadata`)

> **Sintoma conhecido:** O SQL endpoint conecta, mas não exibe nenhuma tabela do Lakehouse — apenas os schemas `sys` e `queryinsights`.
> **Causa:** Metadados do SQL Analytics Endpoint dessincronizados em relação às tabelas Delta do OneLake.

Ação segura (altera **somente metadados**, não modifica dados):

```python
def refresh_sql_endpoint_metadata(workspace_id: str, sql_endpoint_id: str) -> dict:
    url = (
        f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"
        f"/sqlEndpoints/{sql_endpoint_id}/refreshMetadata"
    )
    resp = requests.post(url, headers=get_fabric_headers(), json={}, verify=ca_bundle, timeout=60)
    resp.raise_for_status()
    return resp.json() if resp.text else {"status": resp.status_code}
```

> **Deadlock em `INFORMATION_SCHEMA`:** Se uma consulta a `INFORMATION_SCHEMA` falhar com *deadlock* logo após o `refreshMetadata` (ou durante sincronização automática), aplique backoff curto (ex.: 5–10s, máximo 3 tentativas) e repita a leitura.

---

## 4. Consulta Read-Only ao SQL Endpoint com `mssql-python`

A `connectionString` retornada pela API contém apenas o host (sem credenciais). O token Entra ID é passado como struct UTF-16-LE no atributo `SQL_COPT_SS_ACCESS_TOKEN` (`1256`):

```python
import mssql_python

def build_token_struct() -> bytes:
    token_bytes = cred.get_token(SQL_SCOPE).token.encode("utf-16-le")
    return struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

def query_top_rows(sql_host: str, database_name: str, table_fqn: str, limit: int = 10) -> list[tuple]:
    conn_str = f"Server={sql_host};Database={database_name};Encrypt=yes;TrustServerCertificate=no;"
    with mssql_python.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: build_token_struct()}) as conn:
        cur = conn.cursor()
        # Sempre limitar linhas em sondagens exploratórias (FinOps)
        cur.execute(f"SELECT TOP ({int(limit)}) * FROM {table_fqn}")
        return cur.fetchall()
```

---

## 5. Verificação de Aceite (Somente Leitura)
1. Validar token Fabric (`az account get-access-token --resource https://api.fabric.microsoft.com --query expiresOn -o tsv`).
2. Confirmar listagem de workspaces e tabelas via `fabric-mcp-server`.
3. Ler `connectionString` pela API do Lakehouse usando bundle CA confiável.
4. Executar `SELECT TOP (1) ...` contra uma tabela validada e confirmar retorno sem erros de TLS ou autenticação.
