# Base de Conhecimento Interna (`knowledge/`)

Esta camada armazena PDFs, artigos, livros técnicos e **fichamentos destilados em Markdown** que trazem dinâmicas, processos, premissas estatísticas e boas práticas que a rede de agentes **deve consultar e respeitar** antes de planejar ou executar tarefas.

---

## Como Alimentar a Base (Fluxo Simples em 2 Passos)

### 1. Solte seus PDFs ou documentos
- **Triagem rápida:** jogue PDFs novos em `knowledge/inbox/`.
- **Direto no domínio:** ou salve diretamente em:
  - `knowledge/data-science/` — dinâmicas de ciência de dados, modelagem, feature engineering, validação
  - `knowledge/statistics/` — testes de hipótese, distribuições, causalidade, séries temporais
  - `knowledge/data-engineering/` — Medallion, Fabric OneLake, AWS S3/Iceberg, contratos de dados
  - `knowledge/analytics-bi/` — modelagem dimensional, PBIP/TMDL, DAX, definição de KPIs
  - `knowledge/mlops-backend/` — serving, drift, CI/CD/CT, observabilidade

> **Atenção (`RULE-00`):** Nunca coloque arquivos contendo **PII real de clientes** ou **credenciais** em `knowledge/`.

### 2. Peça ao Antigravity para destilar e indexar
Basta dizer:
> *"Destile os PDFs novos em `knowledge/inbox/` usando a skill `internal-knowledge-base` e atualize o índice."*

O agente irá:
1. Ler cada PDF nativamente (`read_file`), extrair as dinâmicas/processos, premissas obrigatórias e citações de seção/página usando [knowledge-note.template.md](./templates/knowledge-note.template.md).
2. Salvar a nota destilada em `knowledge/<dominio>/KB-NNN-<slug>.md` e registrar no [catalog.json](./catalog.json).
3. Reconstruir o índice local SQLite FTS5 (`knowledge/.index/knowledge.db`) com:
   ```powershell
   uv run .agents/skills/internal-knowledge-base/scripts/knowledge_cli.py index --output ops/telemetry/kb_index_report.json
   ```

---

## Como os Agentes Consomem Automaticamente
- Na **Fase 1 (`LITERATURE_CHECK`)** de toda SPEC, o `literature-researcher` consulta **primeiro `knowledge/`** via `knowledge_cli.py search` (prioridade de metodologia interna) e depois complementa com a web.
- Se um processo recorrente de um PDF virar rotina operacional, o `skill-curator` promove para uma **`SKILL`** (`.agents/skills/`) ou **`RULE`** (`.agents/rules/`).
