## Resumo
- **SPEC de Origem:** `SPEC-NNN`
- **Domínio:** `engineering` | `science` | `analytics` | `mlops` | `harness`
- **Contrato de Dados (ODCS):** `contracts/<arquivo>.odcs.yaml` (ou N/A)

## Checklist de Governança e Qualidade (Obrigatório)
- [ ] SPEC passou por `LITERATURE_CHECK` (`knowledge/` + web), `PLANNED`, `REVIEWED`, `CRITIQUED` e `APPROVED` (`governance-auditor`).
- [ ] Código produtivo organizado em `src/data_products/` seguindo o padrão *src-layout* (sem código de produção solto em `notebooks/`).
- [ ] Testes determinísticos executados (`pytest`) e lint limpo (`ruff`).
- [ ] **Zero segredos**, **zero PII** em texto plano e **zero bypass de TLS** (`RULE-05`).
- [ ] **FinOps verificado:** filtros de partição, OneLake S3 Shortcut Cache (quando aplicável) e tiering de modelos/compute respeitado.
- [ ] Se altera Power BI: versionado em `.pbip` + TMDL + PBIR (zero `.pbix`) e `pbip_precheck.py` aprovado (`0` blockers).
- [ ] Avaliado pelo `skill-curator` se há padrão repetitivo (`>= 2x`) para extração de `SKILL`.
