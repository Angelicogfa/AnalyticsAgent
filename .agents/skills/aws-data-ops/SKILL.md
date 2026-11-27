---
name: aws-data-ops
description: >-
  Padrões operacionais, integração MCP (aws-mcp), segurança e FinOps para AWS Data Platform
  (Amazon S3, Apache Iceberg / Delta Lake, AWS Glue Data Catalog/ETL, Amazon Athena, IAM Least Privilege
  e controle de Egress para Azure/Fabric). Use ao planejar, revisar ou implementar cargas de trabalho na AWS.
---

# Skill: AWS Data Platform Operations

## 1. Interface Primária via MCP (`aws-mcp`)
- Utilize o servidor `aws-mcp` (configurado via `uvx mcp-proxy-for-aws@latest` em `.agents/plugins/multicloud-mcp-connectors/mcp_config.json`) com autenticação SigV4 baseada exclusivamente na sessão local do usuário (`aws login` / IAM Identity Center SSO) e região definida em `~/.aws/config`.
- **Validação de sessão (read-only):** `aws sts get-caller-identity --query Arn --output text` (ou via `multicloud-mcp-runtime`).
- **Troubleshooting de conexão (`failed` / `Invalid request parameters`):**
  1. Renove `aws login` e reconecte o servidor MCP.
  2. Rode o probe stdio (`verify_mcp_env.py --probe-aws-mcp`).
  3. Se o `uvx` selecionar Python 3.13+ atrás de proxy TLS corporativo, fixe o runtime com `uvx --python 3.12 mcp-proxy-for-aws@latest ...`.
  4. Se `@latest` quebrar, fixe a versão conhecida estável (ex.: `mcp-proxy-for-aws==<versão>`) no `mcp_config.json`.
- **Governança:** Operações destrutivas (`delete`, `remove`, `rm --recursive`, `destroy`) são bloqueadas pelo hook `PreToolUse`; mutações exigem SPEC `APPROVED` e confirmação explícita.

## 2. Armazenamento Aberto no S3 & Glue Catalog
- Utilize **Apache Iceberg** ou **Delta Lake** catalogados no **AWS Glue Data Catalog** (interoperabilidade nativa com Athena e Microsoft Fabric OneLake Shortcuts).
- Particione por chave de alta seletividade temporal (`ano/mes/dia` ou *hidden partitioning* do Iceberg) evitando *over-partitioning*.
- Configure **S3 Lifecycle Policies** (`Standard -> Standard-IA -> Glacier`) para camadas brutas históricas.

## 3. Controle de Custos (Athena, Glue & Egress)
- Toda consulta Athena exige projeção explícita de colunas e filtro de partição; teste antes com `EXPLAIN` e respeite o Workgroup Data Usage Limit.
- Compacte arquivos pequenos (*small files* < 32 MB) via jobs Iceberg/Glue periódicos (alvo: 128–512 MB).
- Prefira processamento incremental (Glue Bookmarks / Iceberg snapshots) em vez de *full-reload*.
- Execute transformações pesadas dentro da própria região AWS; exponha ao Microsoft Fabric apenas tabelas curadas com **OneLake S3 Shortcut Cache** ativo.

## 4. Segurança & IAM
- IAM Roles temporárias (SSO/STS) com menor privilégio restritas ao prefixo do domínio (`arn:aws:s3:::bucket/domain/*`), bloqueio de acesso público e criptografia SSE-KMS/SSE-S3 obrigatória.
- Zero chaves estáticas `AKIA...` no repositório, logs ou `mcp_config.json`.
