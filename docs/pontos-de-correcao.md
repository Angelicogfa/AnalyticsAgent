# AnalyticsAgent — Pontos que necessitam correção

- **Origem:** análise do repositório AnalyticsAgent e do PR #1 (Angelicogfa/AnalyticsAgent#1 — portabilidade Claude Code), com observação do projeto `analysis-turnover`.
- **Referência de linhas:** branch `main`, commit `c5fc524`.
- **Legenda de status:** 🔴 pendente · 🟢 tratado no PR #1 · ⚪ operacional (não é correção de código)

---

## A. Governança crítica (afeta o Antigravity; corrigir muda o comportamento atual)

### G1 🔴 Hook libera tudo quando a política falta ou é inválida
- **Onde:** `.agents/hooks/security_finops_gate.py:58` (`load_policy` retorna `{}`) e `:182` (`json.loads` sem tratamento).
- **Problema:** sem `policy.json` (ou com JSON inválido), todas as regras somem e tudo é permitido. Uma entrada inválida faz o script quebrar, e o resultado depende do harness.
- **Correção sugerida:** bloquear (fail-closed) quando a política estiver ausente ou inválida; tratar exceções retornando `deny`.

### G2 🔴 O veto pode ser desligado pelo próprio agente
- **Onde:** `security_finops_gate.py:113` — só `ops/governance/policy.json` é protegido.
- **Problema:** editar `.agents/hooks.json`, `.agents/hooks/*.py` ou `.agents/rules/*` passa livre. Escrever em `policy.json` via `run_command` (ex.: `echo > policy.json`) também passa, porque `evaluate_command` não verifica caminhos.
- **Correção sugerida:** `force_ask` para qualquer escrita em `.agents/**` e `ops/governance/**`, inclusive via `run_command`.

### G3 🔴 O plano executado não é o plano aprovado
- **Onde:** `.agents/workflows/data_task_orchestrator.py:196-265`.
- **Problema:** com `execute=true`, literatura, plano, crítica e auditoria são refeitos (de forma não determinística) e o plano novo é executado. O plano aprovado com `execute=false` não é persistido.
- **Correção sugerida:** persistir o plano aprovado (na SPEC ou em JSON com hash) e, no `execute=true`, apenas carregá-lo e executá-lo.

### G4 🔴 O orquestrador ignora o status da SPEC e não grava os resultados
- **Onde:** `data_task_orchestrator.py` (nunca chama `spec_cli transition`).
- **Problema:** a regra P0 "sem APPROVED, sem execução" depende só do veredito do LLM; as seções 3 a 6 da SPEC não são preenchidas; não há retomada a partir do status atual. Exemplo real: a SPEC-001 do `analysis-turnover` está em `REVIEWED`, e o orquestrador recomeçaria pela literatura.
- **Correção sugerida:** validar o status antes de cada fase, retomar do status atual, gravar as seções na SPEC e fazer a transição via `spec_cli`.

### G5 🔴 Lista de servidores MCP permitidos não é aplicada
- **Onde:** `ops/governance/policy.json:108` e `security_finops_gate.py:138-173`.
- **Problema:** `allowedServers` não é usado. Ferramenta MCP com nome desconhecido cai em `allow` por padrão (`:173`).
- **Correção sugerida:** negar servidores fora da lista; `force_ask` para ferramentas não classificadas.

---

## B. Importantes

### I1 🔴 Regra FinOps não vale para chamadas MCP
- **Onde:** `security_finops_gate.py:100-103` (só em `evaluate_command`) e `policy.json:203`.
- **Problema:** a regra contra `SELECT *` sem filtro não se aplica ao MCP, que é o caminho principal para Athena e Fabric. A regex também não reconhece um `WHERE` em outra linha (`.*` não atravessa quebra de linha).
- **Correção sugerida:** aplicar `costWarningCommandPatterns` aos argumentos MCP e usar `(?s)` na regex.

### I2 🔴 Seis scripts de skill quebram no modo plugin
- **Onde:** `Path(__file__).resolve().parents[4]` em:
  - `.agents/skills/spec-lifecycle/scripts/spec_cli.py:45`
  - `.agents/skills/finops-cost-estimator/scripts/estimate_finops.py:25`
  - `.agents/skills/internal-knowledge-base/scripts/knowledge_cli.py:25`
  - `.agents/skills/medallion-pipeline-scaffolder/scripts/scaffold_pipeline.py:14`
  - `.agents/skills/ops-telemetry-auditor/scripts/audit_metrics.py:14`
  - `.agents/skills/skill-extractor/scripts/scaffold_skill.py:14`
- **Problema:** no plugin, esse caminho aponta para a pasta de plugins, não para o workspace (ex.: `spec_cli create` não encontra os templates).
- **Correção sugerida:** aceitar `--workspace`, ou usar o diretório atual ou uma variável de ambiente, com o comportamento atual como último recurso.

### I3 🔴 Skills e prompts do orquestrador citam caminhos `.agents/...`
- **Onde:** 102 ocorrências em 41 arquivos. Exemplos: SKILL.md com `uv run .agents/skills/...`; `AGENT_ROLE_PATHS` em `data_task_orchestrator.py:35-46`.
- **Problema:** em workspaces externos (modo plugin, nos dois harnesses), scripts e papéis de agentes não são encontrados.
- **Correção sugerida:** referenciar pela raiz do plugin ou resolver os caminhos na instalação.

### I4 🔴 `assemble_plugin` apaga o destino sem verificar
- **Onde:** `src/data_products/harness/warmup.py:97` (`shutil.rmtree(target_dir)`).
- **Problema:** um `--target-dir` errado apaga o diretório indicado. O caminho do Claude já está protegido (🟢).
- **Correção sugerida:** só apagar se o destino contiver o `plugin.json` do próprio bundle.

### I5 🔴 MCPs sem versão fixa e instalação a partir de fonte externa
- **Onde:** `.agents/plugins/multicloud-mcp-connectors/mcp_config.json` (`@latest`, `npx -y`) e `warmup.py:224` (por padrão baixa o código de um repositório GitHub pessoal).
- **Problema:** risco de cadeia de suprimentos e conflito com a política de usar apenas conectores aprovados.
- **Correção sugerida:** fixar versões, permitir apontar para repositório e versão aprovados, e documentar o processo de aprovação.

### I6 🔴 Falhas na execução não interrompem o orquestrador
- **Onde:** `data_task_orchestrator.py:329-399`.
- **Problema:** tarefas `FAILED`/`BLOCKED` não param o fluxo; o status final é `COMPLETED` mesmo com `verified=false`; a curadoria roda de qualquer forma. O schema do plano (`:134-160`) não tem dependências entre tarefas, embora a documentação fale em "DAG".
- **Correção sugerida:** parar no primeiro `FAILED`; só marcar `COMPLETED` com `verified` e `compliance_ok`; adicionar `depends_on`.

### I7 🔴 Nomes de argumentos do Antigravity não verificados
- **Onde:** `security_finops_gate.py:109-110,140-141,191` e matcher em `.agents/hooks.json:16`.
- **Problema:** o código supõe `Path`, `Content`, `Replacement`, `CommandLine`, `ToolName` e `write_file|edit_file`. Se a API real for diferente, o hook não dispara ou não lê o conteúdo.
- **Correção sugerida:** confirmar na documentação do Antigravity e criar testes com payloads reais.

### I8 🔴 CI já falha no `main`
- **Onde:** passo `ruff` de `.github/workflows/ci.yml`.
- **Problema:** 132 erros: 79 `E501`, 28 `F821` (nomes injetados pelo runtime do orquestrador), 13 `UP017`, 7 `F704`, 3 `B905`, 2 `S110`.
- **Correção sugerida:** exceções por arquivo para o orquestrador e correção ou ajuste do restante.

---

## C. Menores

### M1 🔴 Detecção de segredos limitada
- **Onde:** `policy.json:71-92`.
- **Problema:** não reconhece tokens do GitHub, JWT nem segredos de cliente do Azure; `SEC-GENERIC-TOKEN` exige o valor entre aspas.

### M2 🔴 Falso positivo em `git push -f`
- **Onde:** `policy.json:51`.
- **Problema:** `-f\b` também casa com nomes de branch como `feature-f`.

### M3 🔴 YAML inválido no frontmatter de um agente
- **Onde:** `.agents/agents/data-engineering/de-finops-performance.md:3`.
- **Problema:** o trecho `multi-cloud: particionamento` quebra parsers YAML estritos. Já corrigido na cópia gerada para o Claude (🟢); a origem continua com o problema.

### M4 🔴 Testes fixam a contagem de agentes
- **Onde:** `tests/test_harness_integrity.py:58,347,358`.
- **Problema:** `== 22` contradiz o README, que orienta "escalar para N agentes".

### M5 🔴 Nomes de modelo não verificados
- **Onde:** `policy.json:142-199` e frontmatter dos agentes.
- **Problema:** não foi possível confirmar que "Gemini 4 Carbon/Neon/Hydrogen/Argon" existem.

### M6 🔴 Restrição gerente → próprios sub-agentes não é imposta
- **Onde:** existe apenas como texto nos agentes.
- **Problema:** no Claude, o frontmatter não consegue restringir quais sub-agentes um gerente chama; a alternativa seria um hook `PreToolUse` sobre a ferramenta `Agent` (decidido não implementar por ora). No Antigravity, não verificado.

---

## D. Camada Claude Code (PR #1)

### C1 🟢 Concluído
Paridade do gate com bloqueio em caso de falha, telemetria com campo `harness`, `CLAUDE.md`, artefatos gerados com checagem de divergência no CI, marketplace e plugin validados com `claude plugin validate`.

### C2 🔴 Runner do ciclo governado ausente do plugin Claude
`run_spec_cycle.py` só funciona dentro do repositório.

### C3 🔴 Limitações do modo plugin no Claude
As regras P0 não são carregadas (não há `CLAUDE.md`) e o `permissionMode` dos agentes é ignorado. Segundo a documentação do Claude Code, isso não pode ser contornado dentro do plugin.

### C4 ⚪ Hooks de projeto podem ser desativados pela política corporativa
Com `allowManagedHooksOnly`, hooks de projeto não rodam; o caminho é o administrador forçar o plugin via `extraKnownMarketplaces` + `enabledPlugins`. `onFailure: block` exige Claude Code v2.1.295 ou superior (versão local: 2.1.296).

### C5 ⚪ Não verificado
- Ciclo com `claude -p` real (testado só com `claude` simulado).
- Execução no Antigravity real.
- Instalação pelo marketplace (só funciona após o merge).
- Se `agent_type` chega ao hook quando um sub-agente chama a ferramenta `Agent`.

---

## E. Operacional do projeto `analysis-turnover` (não é correção de código)

- **O1 ⚪** O projeto não é um repositório git. Recomenda-se `git init` com `.gitignore` excluindo `.env` e `data/` antes de alternar entre harnesses.
- **O2 ⚪** Não usar os dois harnesses ao mesmo tempo na mesma SPEC (a SPEC-001 está em `REVIEWED`); sem git, não há como resolver edições conflitantes.
- **O3 ⚪** `data/` contém dados de RH, provavelmente com dados pessoais: manter uso apenas agregado (LGPD) nos dois harnesses.
