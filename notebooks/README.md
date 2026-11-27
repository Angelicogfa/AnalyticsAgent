# Notebooks Exploratórios (`notebooks/`)

Seguindo o padrão **Cookiecutter Data Science v2**:
- Use este diretório **exclusivamente** para análise exploratória (EDA), prototipação visual e investigação ad-hoc.
- Adote prefixo numérico padronizado: `01-eda-<topico>.ipynb`, `02-diagnostics-<topico>.ipynb`.
- **Regra de Produção:** Nenhum código de produção, pipeline, feature engineering ou inferência pode ficar apenas em notebooks — toda lógica validada deve ser refatorada para módulos testáveis em `src/data_products/` com testes em `tests/`.
- Limpe outputs com amostras de dados antes de commitar (jamais commite PII em células de saída).
