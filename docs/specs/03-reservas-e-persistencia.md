# Spec 03 — Reservas e persistência

## Comportamento esperado

- Criar preview valida a sessão e a capacidade e emite token de confirmação com
  validade curta. O banco armazena hash do token, não seu valor bruto.
- Confirmar a reserva exige identidade, sessão, token vigente e chave de
  idempotência. Uma reserva só é gravada após confirmação explícita.
- A reserva, consumo de confirmação e recibo/idempotência são transacionais.
  Falha no meio não pode deixar gravação parcial.
- A mesma chave e intenção retorna o mesmo recibo. Reutilizar a chave para outra
  intenção, reservar a mesma sessão duas vezes pela mesma identidade ou exceder a
  capacidade resulta em conflito.
- SQLite é o adapter local padrão; PostgreSQL é suportado pelo adapter comum e
  usado no smoke local descartável. Dados e reservas permanecem após reinício
  quando o mesmo banco/volume é reutilizado.
- Alterar catálogo com reservas incompatíveis falha de modo explícito.

## Código e testes

- Domínio e persistência: `app/reservations.py`, `app/storage.py`,
  `app/postgres_compat.py`, `app/migrations/`.
- Testes: `tests/unit/test_reservations.py`, `tests/unit/test_storage.py`,
  `tests/integration/test_api.py`.
- Comandos: `.venv/bin/python -m pytest tests/unit/test_reservations.py tests/unit/test_storage.py tests/integration/test_api.py`; `make postgres-check`.

## Critérios de aceite

- Token expirado, sessão desconhecida, usuário diferente ou token de outra
  sessão não cria reserva.
- Duas conexões disputando a última vaga produzem um sucesso e um conflito.
- Replay idempotente devolve o recibo original e consome uma vaga apenas uma vez.
- Falha transacional não deixa reserva, token consumido ou recibo parcial.

Todos os dados do evento e as identidades são fictícios. O produto não realiza
reservas reais, pagamentos ou integração com agenda externa.
