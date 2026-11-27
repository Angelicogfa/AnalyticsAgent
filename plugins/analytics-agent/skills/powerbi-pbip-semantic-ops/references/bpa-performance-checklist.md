# Checklist de Pré-Check de Performance & Boas Práticas (PBIP / TMDL / Direct Lake)

Use esta referência junto com `scripts/pbip_precheck.py` e o MCP `powerbi-modeling-mcp` antes de promover qualquer modelo semântico para o Microsoft Fabric.

---

## 1. Ferramentas Oficiais de Pré-Check por Camada

| Camada | Ferramenta | O que Valida | Quando Rodar |
| :--- | :--- | :--- | :--- |
| **Estrutura & Sintaxe** | `pbip_precheck.py` (local) | Ausência de `.pbix`, uso de TMDL/PBIR, JSONs válidos, Auto Date/Time, relacionamentos bidirecionais/M2M, padrões DAX básicos | Todo commit / antes de `VERIFIED` |
| **Regras de Modelagem (BPA)** | **Tabular Editor CLI (`Best Practice Analyzer`)** com `BPARules.json` oficial Microsoft | ~60+ regras de performance, formatação, DAX, manutenção e metadados | Todo PR / antes de deploy |
| **Memória & Compressão** | **VertiPaq Analyzer** (via DAX Studio ou `Semantic Link Labs` no Fabric) | Tamanho total do modelo, colunas de alta cardinalidade (> 1M valores distintos), dicionários pesados, colunas sem uso | Após carga de amostra representativa / antes de produção |
| **Execução DAX (SE vs FE)** | **DAX Studio (`Server Timings` / `dscmd`)** + **`powerbi-modeling-mcp`** | Tempo total, % Storage Engine (SE) vs Formula Engine (FE), número de callbacks (`CallbackDataID`) e materialização excessiva | Medidas críticas de KPI / dashboards executivos |
| **Visuais do Relatório** | **Power BI Performance Analyzer** (Desktop) | Tempo de DAX query, renderização visual e excesso de visuais por página no `.Report` (PBIR) | Antes de publicar relatório |

---

## 2. Comandos Padrão de Referência

### Tabular Editor CLI (Best Practice Analyzer em pasta TMDL)
```powershell
TabularEditor.CLI.exe "src/analytics/pbip/<Projeto>/<Projeto>.SemanticModel/definition" -A "ops/governance/BPARules.json" -V
```

### Validação de Consultas DAX via `powerbi-modeling-mcp` (Power BI Desktop)
1. Abrir o arquivo `<Projeto>.pbip` no **Power BI Desktop**.
2. Conectar via `powerbi-modeling-mcp` à instância local do Power BI Desktop (ou à pasta `.pbip` em modo TMDL).
3. Executar consultas `EVALUATE` das principais medidas de negócio (comparando contra totais de reconciliação Gold vs Silver) e validar que não há erros de contexto de filtro ou degradação severa de latência.

---

## 3. Limiares Recomendados (Critério de Aprovação)
- **BLOCKER (impede aprovação):**
  - Presença de arquivo binário `.pbix` ou `model.bim` legado.
  - Tabelas automáticas `LocalDateTable_*` (Auto Date/Time ligado).
  - Erro de sintaxe TMDL/PBIR ou regra BPA classificada como `Error`.
  - Fallback silencioso de **Direct Lake** para **DirectQuery** sem justificativa formal na SPEC.
- **MAJOR (exige mitigação ou justificativa explícita na SPEC):**
  - Relacionamento bidirecional (`bothDirections`) ou `many-to-many`.
  - Medida crítica com > 30% do tempo em *Formula Engine* ou presença de `CallbackDataID` em tabelas grandes.
  - Coluna de texto de alta cardinalidade não utilizada em visuais/relacionamentos (ex.: GUIDs, timestamps com milissegundos sem separação Data/Hora).
  - Mais de 10–12 visuais simultâneos em uma mesma página PBIR impactando tempo de carga.
