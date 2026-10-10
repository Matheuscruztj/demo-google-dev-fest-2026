# Specs funcionais

Este diretório descreve o comportamento implementado e como validá-lo. Use as
specs como roteiro de onboarding: leia o contrato, siga os arquivos de código e
execute os testes indicados. Os testes são a evidência executável; a spec resume
o comportamento esperado e aponta limites conhecidos.

## Mapa

| Spec | Funcionalidade | Implementação principal | Validação principal |
|---|---|---|---|
| [01 — Catálogo e agenda](01-catalogo-e-agenda.md) | Dados fictícios, filtros e sugestões sem conflito | `app/data/`, `app/data_validation.py`, `app/schedule.py` | `tests/unit/test_data.py`, `tests/unit/test_schedule.py` |
| [02 — FAQ e RAG](02-faq-e-rag.md) | Busca lexical, fontes, abstenção e retrieval híbrido opcional | `app/faq.py`, `app/rag.py`, `app/data/faq_metadata.json` | `tests/unit/test_faq.py`, `scripts/evals/eval_rag.py`, `make postgres-check` |
| [03 — Reserva e persistência](03-reservas-e-persistencia.md) | Preview, confirmação, capacidade, idempotência e adapters de banco | `app/reservations.py`, `app/storage.py`, `app/migrations/` | `tests/unit/test_reservations.py`, `tests/unit/test_storage.py`, `make postgres-check` |
| [04 — API, identidade e interface](04-api-identidade-e-interface.md) | Endpoints, cookie demo, proteção de origem, erros e fluxo no browser | `app/main.py`, `app/schemas.py`, `app/static/` | `tests/integration/test_api.py`, `tests/e2e/test_browser_flow.py` |
| [05 — Agentes, MCP e resiliência](05-agentes-mcp-e-resiliencia.md) | Single/multi, ferramentas permitidas, transporte MCP e providers | `app/agent.py`, `app/agents/`, `app/mcp_client.py`, `mcp_server/` | `tests/unit/test_agent.py`, `tests/unit/test_coordinator.py`, `tests/contracts/test_mcp.py`, `tests/unit/test_resilience.py` |
| [06 — Sessões e histórico](06-sessoes-e-historico.md) | Histórico persistido, isolamento, expiração e leases | `app/chat_sessions.py`, `app/storage.py`, `app/migrations/` | `tests/unit/test_chat_sessions.py`, `tests/integration/test_api.py`, `make postgres-check` |
| [07 — Evals e quality gates](07-evals-e-quality-gates.md) | Avaliação offline/adversarial, build e release gates | `evals/`, `scripts/evals/`, `scripts/checks/` | `make check`, `make pre-push`, `make release-check` |
| [08 — Execução e infraestrutura](08-execucao-e-infraestrutura.md) | Docker local, profiles opcionais, CI e ciclo cloud | `Dockerfile`, `compose.yaml`, `.github/`, `infra/terraform/` | `make compose-check`, `make postgres-check`, runbook Cloud |

## Como validar uma funcionalidade

1. Leia a spec e identifique o contrato e os casos que ela não cobre.
2. Inspecione os arquivos de implementação e os testes apontados.
3. Execute primeiro os testes da spec; depois rode `make check` para a suíte
   offline completa.
4. Para mudanças que afetam pacote ou container, rode `make build` e
   `make compose-check`; para adapter PostgreSQL, rode `make postgres-check`.
5. Trate resultados cloud registrados nos documentos como evidência histórica.
   Os recursos temporários foram removidos e precisam ser recriados antes de um
   novo smoke remoto.

As instruções de setup e variáveis estão em [operação local](../operacao-local.md).
Os critérios gerais e gates estão em [quality gates](../quality-gates.md); os
itens ainda parciais estão em [pendências](../pendencias.md).
