# Regras de Escopo — Base de Conhecimento (`knowledge/`)

- **Prioridade de Conhecimento Interno:** Dinâmicas, processos metodológicos e premissas documentados em `knowledge/` têm precedência sobre recomendações genéricas da web quando aplicáveis à SPEC ativa.
- **Sempre Citar a Fonte (`KB-NNN`):** Todo agente que utilizar conhecimento de `knowledge/` deve referenciar explicitamente o `kb_id` (ex.: `KB-001`), o documento de origem e a seção/página.
- **Busca Antes de Leitura Integral (Otimização de Tokens):** Use `knowledge_cli.py search` (SQLite FTS5) para localizar seções exatas antes de abrir documentos extensos.
- **Zero PII e Zero Segredos:** Jamais armazene datasets reais com PII, senhas ou tokens dentro de `knowledge/`.
- **Destilação de PDFs:** PDFs depositados em `knowledge/inbox/` devem ser fichados em Markdown usando `knowledge/templates/knowledge-note.template.md` e indexados via `knowledge_cli.py index`.
