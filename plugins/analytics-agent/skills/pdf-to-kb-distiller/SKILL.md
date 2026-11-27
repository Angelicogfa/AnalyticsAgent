---
name: pdf-to-kb-distiller
description: >-
  Fluxo rápido de destilação de PDFs depositados em knowledge/inbox/ em notas estruturadas KB-NNN
  com citações de página, registro em knowledge/catalog.json e reindexação SQLite FTS5.
  Otimizada para Gemini 4 Hydrogen (literature-researcher e skill-curator).
---

# Skill: PDF-to-Knowledge Distiller (Hydrogen)

## Quando Ativar
Sempre que o hook `SessionStart` ou `knowledge_cli.py status` detectar PDFs pendentes em `knowledge/inbox/` (ou pastas de domínio em `knowledge/`).

## Fluxo em 5 Passos
1. **Listar PDFs pendentes:**
   ```powershell
   uv run .agents/skills/internal-knowledge-base/scripts/knowledge_cli.py status --output ops/telemetry/kb_status.json
   ```
2. **Ler o PDF nativamente (`read_file`):**
   - Extraia **dinâmicas/processos**, **premissas estatísticas/operacionais**, **antipadrões** e **citações de página/seção** (nunca copie páginas inteiras literalmente; destile com precisão).
3. **Gerar nota `KB-NNN`:**
   - Salve em `knowledge/<dominio>/KB-NNN-<slug>.md` seguindo `knowledge/templates/knowledge-note.template.md`.
   - Marque `candidate_for_skill: true` ou `candidate_for_rule: true` se houver rotina repetitiva ou invariante obrigatório.
4. **Registrar e Reindexar (FTS5):**
   ```powershell
   uv run .agents/skills/internal-knowledge-base/scripts/knowledge_cli.py register --kb-id KB-NNN --title "<Titulo>" --domain <dominio> --source-file "<caminho-pdf>" --note-file "<caminho-nota>" --tags "<tags>"
   uv run .agents/skills/internal-knowledge-base/scripts/knowledge_cli.py index --output ops/telemetry/kb_index_report.json
   ```
5. **Validar Busca:** Execute `knowledge_cli.py search` com 2 termos-chave da nova nota para confirmar que o índice BM25 retorna os trechos esperados.
