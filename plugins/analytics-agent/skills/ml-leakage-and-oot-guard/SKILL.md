---
name: ml-leakage-and-oot-guard
description: >-
  Auditoria estática determinística de pipelines de Ciência de Dados/ML em src/data_products/science/ para
  prevenir data leakage (fit_transform antes de split, shuffle em séries temporais, ausência de random_state
  e training-serving skew). Otimizada para Gemini 4 Neon e Carbon.
---

# Skill: ML Data Leakage & OOT Guard

## Execução Determinística (`scripts/check_leakage.py`)
```powershell
uv run ${CLAUDE_PLUGIN_ROOT}/skills/ml-leakage-and-oot-guard/scripts/check_leakage.py `
  --path src/data_products/science `
  --output ops/telemetry/ml_leakage_report.json
```

## Padrões Auditados
- **`ML-LEAK-FIT-BEFORE-SPLIT` (BLOCKER):** `fit_transform(` chamado em módulo antes de `train_test_split` / split temporal (risco de vazamento estatístico de treino/teste).
- **`ML-LEAK-SHUFFLE-SPLIT` (MAJOR):** `train_test_split(` sem `shuffle=False` quando há indicadores temporais (`dt_`, `date`, `time`, `oot`).
- **`ML-REPRO-NO-SEED` (MAJOR):** modelos/splits estocásticos sem `random_state=` explícito.
- **`ML-TLS-BYPASS` (BLOCKER):** qualquer `verify=False` (`RULE-05`).
