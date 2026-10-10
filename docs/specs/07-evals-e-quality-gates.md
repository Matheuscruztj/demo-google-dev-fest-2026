# Spec 07 — Evals e quality gates

## Avaliação offline

- `evals/cases.jsonl` mantém 40 cenários de agente: 20 normais e 20
  adversariais, incluindo agenda, FAQ, reserva e replay multi-turno.
- O loader valida formato, IDs, fontes, estado inicial, ferramentas permitidas e
  ações proibidas. Oráculos fixos e estado do banco conferem efeitos, não apenas
  texto retornado.
- Casos RAG lexical/híbrido e segurança ficam em `evals/rag_cases.jsonl` e
  `evals/rag_security_cases.jsonl`.
- Execução offline não chama Gemini nem consome quota. Evals live exigem
  configuração e confirmação explícita; são um protocolo separado.

## Gates

- `make lint`: Ruff, formatação e ESLint.
- `make typecheck`: mypy.
- `make test`: testes sem E2E e limite de cobertura de branches por módulos de
  domínio.
- `make e2e`: fluxo de browser com Playwright.
- `make eval-offline`: replay determinístico dos 40 casos.
- `make check`: gates offline de lint, tipos, teste, E2E e eval.
- `make build`: sdist/wheel e smoke de instalação fora do checkout.
- `make compose-check`: imagem e smoke local com persistência/reinício.
- `make postgres-check`: smoke descartável PostgreSQL/pgvector.
- `make pre-push`: `make check`, build e Compose; requer Docker.
- `make release-check`: release gate offline com verificação dos artefatos.

## Código, testes e evidência

- Harness e schemas: `app/evaluators.py`, `evals/harness.py`, `evals/*.jsonl`.
- Runners: `scripts/evals/`.
- Checks: `scripts/checks/`, `Makefile`, `.github/workflows/ci.yml`.
- Matriz de cenários: [`tests/SCENARIO_MATRIX.md`](../../tests/SCENARIO_MATRIX.md).
- Limitações do avaliador: [pendências](../pendencias.md).

Execute primeiro o alvo específico afetado; antes de promover um candidato,
execute os gates completos aplicáveis. Relatórios em `reports/`, coverage e
resultados de browser são artefatos locais e não devem ser commitados sem
sanitização e motivo explícito.
