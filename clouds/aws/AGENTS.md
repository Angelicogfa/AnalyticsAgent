# Regras de Escopo — AWS Data Platform (`clouds/aws/`)

Aplicadas automaticamente quando agentes operam em artefatos relacionados à AWS (S3, Glue, Athena, Redshift, SageMaker, EMR).

## Padrões Obrigatórios AWS
1. **Armazenamento e Formatos Abertos (S3 + Glue Data Catalog):**
   - Utilize **Apache Iceberg** ou **Delta Lake** (ou Parquet compactado Snappy/Zstd para camadas intermediárias) catalogados no **AWS Glue Data Catalog**, garantindo leitura direta tanto pelo Athena quanto por OneLake Shortcuts do Microsoft Fabric.
   - Aplique **S3 Lifecycle Policies** para transição de camadas raw/logs antigos para `S3 Standard-IA` ou `Glacier`.
   - Controle o problema de *small files* com jobs periódicos de compactação (target: 128 MB – 512 MB por arquivo).
2. **FinOps em Queries e Computação:**
   - **Amazon Athena:** Toda query deve usar filtro explícito nas colunas de partição e projetar apenas as colunas necessárias (proibido `SELECT *` sem `LIMIT` em tabelas grandes). Respeite workgroups com **Data Usage Control** (limite de scan por query).
   - **AWS Glue / EMR:** Prefira processamento incremental (Glue Job Bookmarks / Iceberg incremental reads) e dimensione DPUs com auto-scaling habilitado.
   - **Egress Cross-Cloud:** Antes de mover dados da AWS para Azure, avalie processamento pesado na própria AWS e exposição apenas da camada curada (Silver/Gold) via OneLake Shortcut com cache.
3. **Segurança, IAM e MCP (`aws-mcp` — `RULE-05` / `SPEC-000`):**
   - Use **IAM Roles** temporárias (IAM Identity Center / SSO via `aws login`, conferido com `aws sts get-caller-identity`) com políticas de menor privilégio restritas a prefixos S3 específicos (`arn:aws:s3:::bucket/domain/*`).
   - Utilize `aws-mcp` (`uvx mcp-proxy-for-aws`) sem credenciais no `mcp_config.json`; se `uvx` selecionar Python 3.13+ atrás de proxy TLS corporativo, fixe `uvx --python 3.12`.
   - Criptografia obrigatória em repouso (SSE-S3 / SSE-KMS) e em trânsito (TLS sem bypass).
   - Jamais habilite acesso público em buckets S3 ou exponha chaves estáticas `AKIA...`.
