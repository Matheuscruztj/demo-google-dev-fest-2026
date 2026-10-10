# Spec 05 — Agentes, MCP e resiliência

## Modos

- `EVENTOPS_MODE` seleciona o perfil do produto e permanece `offline` no demo.
- `EVENTOPS_AGENT_MODE=offline` dá respostas determinísticas e não chama APIs.
- `local` usa Ollama; `live` usa Google ADK/Gemini. Credenciais e configuração
  Vertex AI usam API key ou ADC conforme o provider/configuração selecionados.
- A interface pode escolher arquitetura `single` ou `multi`. O coordenador
  escolhe especialistas; agenda/FAQ são verificadas por ferramentas locais e o
  especialista de agenda pode usar MCP stdio.

## Limites de segurança

- Ferramentas de agente são somente de leitura. O agente pode propor reserva,
  mas só a interface/API de preview e confirmação pode gravá-la.
- Saídas são validadas contra IDs, fontes e schema conhecidos. Fonte desconhecida,
  sessão conflitante ou campos extras não são aceitos como resultado válido.
- Limite de ferramentas/delegações é por requisição. Harness de falha é interno
  aos testes e não pode ser ativado por mensagem pública.
- O MCP usa o mesmo banco/catalogo configurado, valida ferramentas e payloads,
  fecha o processo/transporte após uso e trata cancelamento/falha.

## Resiliência

- Deadline total limita a duração da chamada; retry só ocorre em falhas
  transitórias elegíveis e dentro do deadline.
- Circuit breaker do provider e proteção do transporte MCP impedem repetição
  contínua em falhas. Falhas não são reportadas como sucesso.
- O controle de retries internos do SDK Gemini permanece uma limitação de
  integração; veja [pendências](../pendencias.md).

## Código e validação

- Providers e agente: `app/agent.py`, `app/config.py`.
- Coordenador: `app/agents/coordinator.py`.
- MCP: `app/mcp_client.py`, `mcp_server/server.py`.
- Políticas: `app/resilience.py`.
- Testes: `tests/unit/test_agent.py`, `tests/unit/test_coordinator.py`,
  `tests/contracts/test_mcp.py`, `tests/unit/test_resilience.py`.
- Comandos: `.venv/bin/python -m pytest tests/unit/test_agent.py tests/unit/test_coordinator.py tests/contracts/test_mcp.py tests/unit/test_resilience.py`; `make eval-offline`.

## Limite da evidência

O smoke Gemini single/multi/MCP foi aprovado na implantação temporária em
10/10/2026. A cloud foi removida depois do smoke. Os especialistas continuam
determinísticos; isso não demonstra agentes especialistas independentes com
LLMs nem aprovação da comparação live.
