# RULE-03: Rigor Estatístico, Comportamento dos Dados e Validação Científica (P0 — Obrigatório)

- **Classificação:** `P0 — MANDATORY`
- **Responsáveis:** `literature-researcher` (fundamentação) + `data-scientist-statistician` / `analytics-bi-specialist` (diagnóstico em código)

## 1. Premissas Antes de Algoritmos
Nenhum modelo estatístico, teste de hipótese, previsão ou KPI derivado pode ser entregue sem:
1. **Verificação Bibliográfica:** Referência explícita (artigo, livro-texto clássico ou documentação oficial) justificando o método escolhido para a natureza dos dados.
2. **Diagnóstico Empírico Obrigatório:** Antes de assumir qualquer distribuição ou método paramétrico, executar e documentar testes diagnósticos nos dados reais:
   - **Distribuição e Cauda:** Assimetria, curtose, testes de aderência (Shapiro-Wilk / Anderson-Darling / KS conforme $N$), detecção de zero-inflation, heavy-tails e outliers.
   - **Dependência Temporal / Espacial:** Estacionariedade (ADF / KPSS), autocorrelação (ACF/PACF), sazonalidade, quebras estruturais e split estritamente temporal (proibido random split em séries temporais).
   - **Regressão / Inferência:** Multicolinearidade (VIF), heterocedasticidade (Breusch-Pagan / White), independência dos resíduos, correção para múltiplos testes (Bonferroni / Benjamini-Hochberg FDR) e análise de poder estatístico.
   - **Classificação / ML:** Desbalanceamento de classes, calibração de probabilidades (Brier score / ECE), prevenção rigorosa de **data leakage** (fit de scalers/imputers/encoders exclusivamente dentro do fold de treino), validação out-of-time (OOT).
   - **Causalidade:** Diferenciar explicitamente correlação de causalidade; alertar para variáveis de confusão, viés de seleção e Paradoxo de Simpson.

## 2. Premissas Operacionais dos Dados
- Validar explicitamente: granularidade (chave primária esperada vs real), taxa de nulos, unicidade, dados tardios (*late-arriving data*), *schema drift*, fuso horário (padronizar UTC internamente) e definição de janelas de observação vs performance.

## 3. Proibição de "Silent Failure"
Se uma premissa estatística falhar nos dados reais, o agente **DEVE** relatar a violação, consultar a literatura para método robusto/não-paramétrico/alternativo (ex.: GLM/Tweedie, regressão quantílica, bootstrap, modelos hierárquicos) e atualizar a SPEC antes de prosseguir.
