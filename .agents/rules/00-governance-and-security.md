# RULE-00: Governança, Segurança e Compliance (P0 — Obrigatório)

- **Classificação:** `P0 — MANDATORY`
- **Responsável pela Auditoria:** `governance-auditor`

## 1. Controles de Acesso e Menor Privilégio
- Toda interação com **AWS** (S3, Glue, Athena, Redshift, SageMaker) deve usar IAM Role com menor privilégio (preferencialmente somente leitura em ambientes produtivos; escrita restrita a prefixos `dev/` ou `staging/` definidos na SPEC).
- Toda interação com **Azure / Microsoft Fabric** deve respeitar grupos de segurança do **Microsoft Entra ID** e isolamento por Workspace (`dev` → `homolog` → `prod`).
- É proibido executar alterações em produção diretamente a partir de sessões exploratórias sem SPEC `APPROVED` e gate humano (HITL).

## 2. Privacidade e Proteção de Dados (LGPD / PII)
- Qualquer tabela contendo colunas sensíveis (`cpf`, `email`, `telefone`, `nome_completo`, `data_nascimento`, etc.) deve ser mascarada, anonimizada ou tokenizada antes de sair da camada Bronze ou ser exposta a notebooks exploratórios/BI.
- Nunca imprima amostras de registros com PII no `stdout`, em artefatos Markdown ou em mensagens entre agentes.

## 3. Defesa em Profundidade
- Regras em prompt **nunca** substituem guardrails determinísticos.
- Todo comando bloqueado pelo hook `.agents/hooks/security_finops_gate.py` deve ser tratado como violação real: revise a SPEC ou solicite aprovação formal humana — jamais tente reformular o comando para burlar o regex do hook.

## 4. Rastreabilidade e Linhagem
- Toda execução relevante deve referenciar o `SPEC_ID` (ex.: `SPEC-001`) em commits, metadados de experimentos, tabelas criadas e relatórios de auditoria.
- Todos os eventos de ferramentas são registrados automaticamente em `ops/telemetry/events.jsonl` para auditoria contínua.
