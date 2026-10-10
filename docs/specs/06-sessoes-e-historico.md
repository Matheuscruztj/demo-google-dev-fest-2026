# Spec 06 — Sessões e histórico

## Comportamento esperado

- Cookie opaco identifica a sessão do navegador; o banco armazena somente seu
  hash. Navegadores diferentes têm identidades e históricos isolados.
- Histórico mantém no máximo os quatro turnos mais recentes (oito mensagens) e
  sobrevive à reinicialização se o mesmo banco for mantido.
- Lease no banco permite uma chamada ativa por conversa. Outra chamada recebe
  `409 chat_busy`. Lease órfão expira após 120 s; o proprietário antigo não pode
  salvar resposta nem liberar lease novo.
- Sessão expira em 24 h. Criar sessão nova remove identidades expiradas e seus
  históricos/leases, sem apagar reservas nem recibos.
- SQLite e PostgreSQL compartilham o contrato de persistência/migrations.

## Código e testes

- Sessões: `app/chat_sessions.py`, `app/storage.py`,
  `app/migrations/0001_initial.sql`, `app/migrations/0002_chat_sessions.sql`.
- Testes: `tests/unit/test_chat_sessions.py`, `tests/unit/test_storage.py`,
  `tests/integration/test_api.py`, `tests/contracts/test_mcp.py`.
- Comandos: `.venv/bin/python -m pytest tests/unit/test_chat_sessions.py tests/integration/test_api.py`; `make postgres-check`.

## Critérios de aceite

- Cookies diferentes não compartilham histórico ou confirmação.
- Reinício com o mesmo banco preserva histórico; conversa expirada não é lida.
- Duas conexões concorrentes produzem um lease válido e um `chat_busy`.
- Expiração do lease permite recuperação e rejeita gravações do proprietário
  anterior.
- Limpeza de sessão preserva estado de reserva.

Mais limites e comportamento legado estão em [pendências — controle de sessões](../pendencias.md#controle-de-sessões-implementado).
