---
name: internal-knowledge-base
description: >-
  Gerencia, destila, indexa (SQLite FTS5 / BM25) e consulta a base de conhecimento interna do repositório (knowledge/).
  Use para consultar processos, dinâmicas e premissas extraídas dos PDFs e notas da equipe antes da busca web,
  ou para fichar e indexar novos PDFs colocados em knowledge/inbox/ e subpastas de domínio.
---

# Skill: Internal Knowledge Base (`knowledge/`)

## Visão Geral
Permite que todos os agentes consumam o conhecimento proprietário/curado da equipe (PDFs de ciência de dados, estatística, engenharia, BI e MLOps) de forma **determinística, offline, auditável e econômica em tokens** via índice **SQLite FTS5** com ranking **BM25**.

## Comandos da CLI (`scripts/knowledge_cli.py`)

### 1. Reconstruir índice FTS5 e detectar PDFs pendentes de fichamento
```powershell
uv run ${CLAUDE_PLUGIN_ROOT}/skills/internal-knowledge-base/scripts/knowledge_cli.py index --output ops/telemetry/kb_index_report.json
```

### 2. Buscar conhecimento relevante por tópico e domínio (antes da busca web!)
```powershell
uv run ${CLAUDE_PLUGIN_ROOT}/skills/internal-knowledge-base/scripts/knowledge_cli.py search --query "validacao out-of-time calibracao" --domain data-science --limit 5 --output ops/telemetry/kb_search.json
```
*(O argumento `--domain` é opcional; omita para buscar em todos os domínios.)*

### 3. Listar status do catálogo e PDFs pendentes em `knowledge/inbox/`
```powershell
uv run ${CLAUDE_PLUGIN_ROOT}/skills/internal-knowledge-base/scripts/knowledge_cli.py status --output ops/telemetry/kb_status.json
```

### 4. Registrar nova nota destilada no catálogo (`knowledge/catalog.json`)
```powershell
uv run ${CLAUDE_PLUGIN_ROOT}/skills/internal-knowledge-base/scripts/knowledge_cli.py register --kb-id KB-002 --title "Titulo do PDF" --domain data-science --source-file "knowledge/data-science/meu-arquivo.pdf" --note-file "knowledge/data-science/KB-002-meu-arquivo.md" --tags "series-temporais,sazonalidade"
```

## Protocolo para Destilar um Novo PDF Depositado pelo Usuário
1. Rode `status` para listar PDFs pendentes em `knowledge/inbox/` ou pastas de domínio.
2. Leia o PDF diretamente com `read_file` (por faixas de páginas se for longo).
3. Crie a nota destilada em `knowledge/<dominio>/KB-NNN-<slug>.md` seguindo rigorosamente `knowledge/templates/knowledge-note.template.md` (incluindo citações de página/seção, dinâmicas/processos e matriz de premissas).
4. Mova o PDF original de `knowledge/inbox/` para `knowledge/<dominio>/` (se o usuário quiser manter o original junto) e execute `register` + `index`.
5. Se a nota indicar `candidate_for_skill: true` ou `candidate_for_rule: true`, sinalize ao `skill-curator`.
