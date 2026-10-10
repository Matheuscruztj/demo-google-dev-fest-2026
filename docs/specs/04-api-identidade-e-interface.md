# Spec 04 — API, identidade e interface

## Contratos HTTP

- `GET /health`: saúde da aplicação.
- `GET /api/sessions`: catálogo, com filtros de consulta disponíveis.
- `POST /api/schedule`: sugestão de sessões respeitando os filtros enviados.
- `POST /api/faq`: resposta fundamentada ou abstenção.
- `POST /api/chat`: conversa single ou multi; single é o padrão.
- `POST /api/reservations/preview`: inicia confirmação para uma sessão.
- `POST /api/reservations`: confirma a reserva com token e chave idempotente.
- Schemas rejeitam campos extras e identidade enviada pelo cliente. Erros usam
  `error.code`, `error.message` e `error.request_id`; `X-Request-ID` repete o ID.

## Identidade e proteção

- A identidade demo vem de cookie opaco HttpOnly, SameSite=Lax, com validade de
  24 h; `Secure` é configurável. O banco guarda hash do cookie.
- Preview e confirmação devem usar o mesmo navegador. O cliente não escolhe
  `user_id`.
- Operações mutáveis exigem origem própria ou uma origem listada em
  `EVENTOPS_ALLOWED_ORIGINS`. Payload inválido resulta em 422; origem não
  permitida, em 403; ausência, em 404; conflito, em 409.
- Erros inesperados retornam mensagem genérica e request ID, sem expor exceção.

## Interface

- `app/static/` serve a interface do produto. Sugestões de reserva do chat não
  gravam diretamente: o fluxo deve passar por preview e confirmação.
- Conteúdo do modelo é renderizado como texto não confiável; não executar HTML
  retornado pelo provider.
- O browser E2E cobre fluxo de reserva, retry idempotente, layout móvel e saída
  de modelo não confiável.

## Código e validação

- Implementação: `app/main.py`, `app/schemas.py`, `app/static/`.
- Testes: `tests/integration/test_api.py`, `tests/e2e/test_browser_flow.py`.
- Comandos: `.venv/bin/python -m pytest tests/integration/test_api.py`; `make e2e`.

## Critérios de aceite

- Preview sem confirmação não cria reserva; confirmação repetida não duplica.
- Cookie/origem inválidos não permitem mutação nem cruzamento entre browsers.
- Contrato de erros preserva código e request ID no corpo/cabeçalho.
- Interface apresenta conteúdo externo como texto e mantém o fluxo usável em tela
  estreita.
