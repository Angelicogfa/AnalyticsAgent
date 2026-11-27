# RULE-02: FinOps e Otimização de Custos e Capacidade (P0 — Obrigatório)

- **Classificação:** `P0 — MANDATORY`
- **Escopo:** Consumo de LLM (família Gemini 4 / tiers de API) + Computação e Armazenamento em Azure (Microsoft Fabric) e AWS.

## 1. Otimização de Custos Agênticos (Roteamento Gemini 4 + API Tiering)
- **Mapeamento Oficial Gemini 4 (Antigravity / `/swarm`) × Tier de API (`run_workflow` / `invoke_subagent`):**
  - **Gemini 4 Carbon** *(tier `pro`)*: reservado exclusivamente para gates críticos de alto risco (`governance-auditor`, `plan-reviewer-critic` em modo Red Team) e escalações arquiteturais/causais difíceis.
  - **Gemini 4 Neon** *(tier `pro` / `flash` com 4 níveis de thinking: `Low` → `Extra High`)*: espinha dorsal equilibrada para `orchestrator`, `planner-architect`, `data-scientist-statistician` e `backend-mlops-specialist` (~32% menor custo que Carbon com inteligência quase-flagship).
  - **Gemini 4 Hydrogen** *(tier `flash` / `flash_lite`)*: motor rápido e econômico para execução disciplinada e paralela (`data-engineer`, `analytics-bi-specialist`, `literature-researcher`, `skill-curator`), com alta disciplina em *batching* de ferramentas.
  - **Gemini 4 Argon**: **não usar como primário**; mantido apenas como **fallback de contingência** caso Carbon ou Neon atinjam limite de cota/capacidade em sessões longas.
- **Payloads Estruturados e Enxutos:** Agentes devem se comunicar por contratos JSON/Markdown compactos ou arquivos no disco — nunca copie logs gigantes ou amostras brutas de DataFrames inteiros no contexto.
- **Saída em Arquivo:** Scripts de skills devem gravar resultados extensos em disco (`ops/telemetry/` ou diretórios de saída) e retornar no `stdout` apenas um resumo conciso e o caminho do arquivo.
- **Circuit Breakers:** Máximo de 3 tentativas por erro de código/query. Sem loops infinitos de debug.

## 2. Otimização Multi-Cloud (Microsoft Fabric + AWS)
- **Zero Cópia Desnecessária (Single Logical Data Lake):** Prefira **OneLake Shortcuts para Amazon S3** em vez de pipelines de cópia bruta AWS→Azure, sempre ativando **Cache para S3 Shortcuts** no workspace Fabric para cortar custos de *data egress* da AWS.
- **Formatos Abertos:** Padronize armazenamento em **Delta Lake** ou **Apache Iceberg** (catalogado no AWS Glue / OneLake) para leitura interoperável entre Athena, Glue e Fabric Spark/Direct Lake sem duplicação.
- **Particionamento e Compactação:** Toda query em Athena/Spark/Fabric SQL deve filtrar por coluna de partição (ex.: `dt_ref`, `ano/mes`) e evitar `SELECT *` sem `LIMIT`. Agende compactação (`OPTIMIZE` / Z-Order / V-Order) para mitigar *small files*.
- **Estimativa Antes da Execução:** Antes de rodar queries ou jobs Spark pesados, execute `finops-cost-estimator` (`estimate_finops.py`) + `EXPLAIN` / dry-run e registre a estimativa na SPEC.
- **Gestão de Fabric Capacity Units (CUs):** Jobs batch pesados devem ser agendados fora do horário de pico de BI e dimensionados para não causar *throttling* da capacidade compartilhada.
