# Contribuindo com o AnalyticsAgent (Template MIT)

Obrigado pelo interesse em evoluir este template aberto de repositório agêntico para produtos de dados!

## Princípios do Template
1. **Spec-First:** Toda nova funcionalidade, pipeline, modelo ou melhoria relevante nasce como uma SPEC em `specs/active/` seguindo `specs/templates/`.
2. **Padrão de Mercado para Data Products:** Todo código produtivo vive em `src/data_products/` (*src-layout*), acompanhado de contrato de dados em `contracts/` (ODCS v3.x) e testes determinísticos em `tests/`.
3. **Earned Rules Only:** Não infle `.agents/rules/` com preferências genéricas; promova apenas restrições P0 ou lições de falhas reais, mantendo cada arquivo abaixo de `24 KB`.
4. **Sanitização Absoluta:** Jamais inclua nomes de empresas, tenant IDs, nomes de workspaces/buckets privados, credenciais, tokens, certificados corporativos ou PII neste template.

## Fluxo de Contribuição
1. Crie uma branch descritiva (`feat/...`, `fix/...`, `docs/...`).
2. Instale o ambiente Python 3.12 via `uv`:
   ```bash
   uv sync --group dev
   ```
3. Execute as validações locais antes de abrir o PR:
   ```bash
   uv run pytest
   uv run .agents/skills/powerbi-pbip-semantic-ops/scripts/pbip_precheck.py --path src/data_products/analytics/pbip --output ops/telemetry/pbip_precheck_report.json
   uv run .agents/skills/internal-knowledge-base/scripts/knowledge_cli.py index --output ops/telemetry/kb_index_report.json
   ```
4. Abra o Pull Request preenchendo o checklist em `.github/PULL_REQUEST_TEMPLATE.md`.

## Licença
Ao contribuir, você concorda que suas contribuições serão licenciadas sob a [MIT License](./LICENSE).
