# Regras de Escopo — Produtos de Dados (`src/data_products/`)

Este diretório segue o padrão de mercado para **Produtos de Dados**: **Python `src`-layout** (`pyproject.toml` + `uv` + `hatchling`), **Open Data Contract Standard (ODCS v3.x)** em `contracts/`, **Cookiecutter Data Science v2** (`data/`, `notebooks/`, `tests/`) e **Power BI `.pbip`/TMDL/PBIR**.

## Regras Obrigatórias para Artefatos em `src/`
1. **Estrutura Canônica (`src/data_products/`):**
   - `common/` — configuração segura via env (`RuntimeConfig`, zero segredos hardcoded, zero bypass TLS), utilitários e logging sem PII.
   - `engineering/` — pipelines Medallion (Bronze/Silver/Gold), ingestões, compactação e contratos multi-cloud.
   - `science/` — diagnósticos estatísticos, feature engineering sem leakage, modelagem e validação OOT.
   - `analytics/` — reconciliação Gold/Silver, definições de KPIs e projetos Power BI em `analytics/pbip/<dominio>/`.
   - `mlops/` — APIs de inferência (Pydantic/OpenAPI), healthchecks (`/health`, `/ready`), empacotamento MLflow/SageMaker e monitoramento de drift.
2. **Rastreabilidade por SPEC & Contrato ODCS:**
   - Todo módulo em `src/data_products/` deve referenciar no cabeçalho o `SPEC-ID` (ex.: `SPEC-ID: SPEC-001`).
   - Todo dataset Silver/Gold produzido deve ter contrato formal em `contracts/<dominio>-<produto>.odcs.yaml` (baseado em `contracts/templates/data-contract.odcs.yaml`).
3. **Idempotência & Testes Determinísticos (`tests/`):**
   - Pipelines devem ser reexecutáveis sem duplicar registros (`MERGE`, overwrite por partição, checkpoints).
   - Toda entrega em `src/data_products/` exige testes determinísticos em `tests/` executáveis via `pytest` em sandbox (schema/contrato, nulos, edge cases, API contract ou diagnósticos estatísticos) e código limpo no `ruff`.
4. **Reprodutibilidade & Separação de EDA:**
   - Notebooks em `notebooks/` servem **apenas para EDA**; código de produção vive exclusivamente em `src/data_products/`.
   - Fixe `random_state` / seeds e separe treino/validação/teste (OOT para séries temporais).
5. **Segurança & TLS (`RULE-00` / `RULE-05`):**
   - Zero segredos hardcoded (use `AzureCliCredential`, `aws login`, Key Vault / Secrets Manager).
   - Use `RuntimeConfig.from_env().tls_verify_arg()` para HTTP/REST — **nunca** `verify=False`.
