---
name: statistical-diagnostics-runner
description: >-
  Executa diagnósticos estatísticos determinísticos obrigatórios (RULE-03) sobre datasets CSV antes da modelagem:
  taxa de nulos, assimetria/curtose, outliers (IQR), correlação alta, estabilidade temporal (PSI entre treino e OOT)
  e calibração (Brier Score). Otimizada para Gemini 4 Neon (data-scientist-statistician).
---

# Skill: Statistical Diagnostics Runner (Neon)

## Visão Geral
Garante determinismo estatístico antes de treinar qualquer modelo ou executar inferência (`RULE-03`), eliminando cálculos manuais no LLM. Funciona com Python stdlib puro (sem dependências pesadas obrigatórias).

## Execução Determinística (`scripts/run_diagnostics.py`)
```powershell
uv run .agents/skills/statistical-diagnostics-runner/scripts/run_diagnostics.py `
  --train-csv data/processed/train.csv `
  --oot-csv data/processed/oot.csv `
  --target-col churn_60d `
  --prob-col pred_prob `
  --output ops/telemetry/diagnostics_report.json
```

## O que é Verificado
- **Por coluna numérica:** contagem, taxa de nulos, média, desvio padrão, mediana, IQR, taxa de outliers (> 1.5 IQR), assimetria (*skewness*) e excesso de curtose.
- **Colinearidade:** pares de variáveis numéricas com $|r| \ge 0.85$ sinalizados para checagem de VIF.
- **Estabilidade Temporal (PSI):** quando `--oot-csv` é fornecido, calcula PSI (*Population Stability Index*) por decil para cada feature numérica (`PSI >= 0.25` = *drift* severo; `0.10–0.25` = moderado).
- **Desbalanceamento & Calibração:** taxa positiva da variável alvo e **Brier Score** quando `--prob-col` está presente.
