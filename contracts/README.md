# Contratos de Dados (`contracts/` — Open Data Contract Standard v3.x)

Todo produto de dados exposto em camada **Silver** ou **Gold** (AWS S3/Iceberg ou Microsoft Fabric OneLake/Delta) **DEVE** declarar seu contrato formal em YAML seguindo o padrão aberto **Open Data Contract Standard (ODCS v3.x — Linux Foundation / Bitol)**.

## Convenções
- Crie um arquivo por produto de dados: `contracts/<dominio>-<produto>.odcs.yaml` a partir de [data-contract.odcs.yaml](./templates/data-contract.odcs.yaml).
- Referencie o `spec_id` correspondente (ex.: `SPEC-001`) e o pacote Python responsável em `src/data_products/`.
- Valide o contrato nos testes automatizados em `tests/` antes de promover qualquer alteração de schema.
