# Pendências funcionais e controle de sessões

Revisão funcional: 2026-10-09; cloud: 2026-10-10. Escopo: funcionalidades e critérios de validação confrontados com o código. Infraestrutura remota, configuração de `GOOGLE_API_KEY` e execução de
gates dependentes dessas condições ficam fora da lista funcional abaixo. Em
10/10/2026, a infraestrutura temporária foi validada com agentes single/multi
e RAG híbrido remoto e removida após o smoke; o alerta de orçamento permanece.
Passar nos testes atuais não comprova requisitos que o avaliador ainda não verifica.

## Controle de sessões implementado

| ID | Estado | Entrega | Evidência |
|---|---|---|---|
| S01 | Concluído | API e MCP consultam o mesmo banco configurado; JSON é somente seed de banco vazio. MCP lê alterações a cada chamada, inclusive após iniciar o processo. | `mcp_server/server.py`, `app/mcp_client.py`, `tests/contracts/test_mcp.py`, `tests/integration/test_api.py` |
| S02 | Concluído | Histórico por sessão de navegador persistido, limitado a quatro turnos/oito mensagens, recuperado após recriar a aplicação. Identidade resolvida pelo hash do cookie opaco. | `app/chat_sessions.py`, `tests/unit/test_chat_sessions.py`, `tests/integration/test_api.py` |
| S03 | Concluído | Lease no banco impede chamadas simultâneas por conversa. Outra chamada recebe HTTP 409 `chat_busy`; falha/cancelamento libera o lease; após crash, expira em 120 s. Proprietário antigo não salva nem libera lease substituído. | `app/chat_sessions.py`, `tests/unit/test_chat_sessions.py`, `tests/integration/test_api.py` |
| S04 | Concluído | Sessões expiram em 24 h; cookie existente não recebe prazo novo sem renovar a validade no banco. Criar uma sessão limpa identidades expiradas e histórico/leases por cascade, preservando reservas e recibos. | `app/storage.py`, `app/main.py`, `tests/unit/test_chat_sessions.py` |
| S05 | Concluído | Schema SQLite v3 e migration PostgreSQL `0002_chat_sessions.sql`; atualização aditiva preserva catálogo/reservas. Cookies legados sem expiração são tratados como expirados. | `app/storage.py`, `app/migrations/0002_chat_sessions.sql`, `tests/unit/test_storage.py`, `scripts/checks/check_postgres.py` |

O banco contém texto das conversas fictícias. Histórico compartilhado exige o
mesmo banco e cookie. Os providers offline continuam determinísticos e não
interpretam histórico. O lease de 120 s supera o deadline máximo atual (65 s);
aumentar o deadline exige rever o lease. A limpeza é oportunista, ao criar uma
sessão, sem job periódico. Persistência local não aprova G6 cloud.

## Funcionalidades pendentes

| ID | Prioridade | Estado | Pendência | Critério de conclusão |
|---|---|---|---|---|
| F01 | Alta | Concluído local | Perguntas conhecidas sobre agenda, políticas e segurança usam ferramentas determinísticas com catálogo/fontes; single local seleciona IDs válidos, filtros e conflitos sem geração livre. Qwen3:8b permanece como fallback local para pedidos fora das intenções suportadas. GPU e runtime Ollama validados. | Verificado em `app/agent.py`, `app/agents/coordinator.py`; 120/120 avaliações por arquitetura no comparativo local guardado, três rodadas. O modelo cru sem guardas falhou vários casos adversariais; não é usado para decidir fatos, IDs ou ações cobertos pelas ferramentas. |
| F02 | Concluído local; avaliação Gemini encerrada no escopo | Comparador pareado oferece offline, local e live; modo local exige três rodadas, teto planejado, checkpoint atômico e intercala single/MCP. Comparação local guardada passou 120/120 tentativas por arquitetura. A validação Gemini externa retornou 402 por créditos e foi encerrada por decisão de escopo; isso não é aprovação G4 live. | `scripts/evals/run_comparison.py`, `make eval-compare`, `make eval-compare-local`; evidência `reports/20261011T011702Z-812a56e0/comparison.json`. Gemini não será executado neste ciclo. |
| F03 | Alta | Concluído local | Single offline extrai e aplica nível solicitado, inclusive formas acentuadas e plurais; trilha é reconhecida por palavra inteira. | `app/agent.py: OfflineProvider.respond`; casos fixos em `tests/unit/test_agent.py`. |
| F04 | Alta | Concluído local | Casos de agenda declaram trilha, nível, horário e quantidade; avaliador confere filtros, mínimo/exato e conflitos contra o catálogo. O pedido de três opções após 14h exige três resultados. | `app/evaluators.py`, `evals/cases.jsonl`. |
| F05 | Alta | Concluído local | Cada caso usa SQLite isolado e executa passos por HTTP com cookie/origem; cobre prévia abandonada sem confirmação, token inválido, capacidade esgotada, confirmação e replay idempotente. Estado persistido é lido ao final. | `app/evaluators.py: execute_case_state`, `scripts/evals/run_evals.py`, `scripts/evals/run_comparison.py`, casos `adv-duplicate` e `adv-last-seat`. O browser real continua coberto pelo gate E2E, fora do replay de eval. |
| F06 | Concluído local; retry Gemini fora do escopo | Breaker local compartilhado protege single/Ollama; breaker MCP protege multi; harness valida timeout e saída abrupta; runner limita chamadas locais observáveis antes do Ollama. | `app/agent.py`, `app/main.py`, `app/mcp_client.py`, `evals/harness.py`, `scripts/evals/run_comparison.py`. Retries internos do SDK Gemini só se aplicam ao modo live, encerrado neste ciclo por decisão de escopo. |
| F07 | Média | Concluído local | Tokens medidos por Ollama/ADK são agregados por chamada/retry; métricas mostram cobertura, sucesso, duração, chamadas e custo conhecido por tarefa. Dashboard HTML local acompanha o JSON. Custo de compute local permanece indisponível e fora do escopo. | `app/agent.py`, `app/data/model_prices.json`, `app/metrics.py`, `scripts/evals/report_metrics.py`. Preço live Gemini está fora do ciclo local. |
| F08 | Média | Concluído local | Metadados estruturados de versão, atualização, validade, status, conflito e confiança são validados e chegam às citações. Retrieval exclui regras futuras, expiradas, conflitantes e não confiáveis; fixture contaminada isolada exige abstenção. | `app/data/faq_metadata.json`, `app/data_validation.py`, `app/faq.py`, `evals/harness.py`, `tests/fixtures/adversarial/faq_poisoned_chunk.json`. A fixture não entra no catálogo publicado. |
| F09 | Média | Concluído local | `make release-check` executa gates offline, build e Compose; compara hash do candidato em eval/build/imagem, dataset/catálogo, wheel/sdist e digest Docker, falhando com evidência ausente ou divergente. | `scripts/checks/candidate.py`, `scripts/checks/release_check.py`, `scripts/checks/check_build.py`, `scripts/checks/check_compose.py`, `Makefile`. Gate live continua separado e exige execução autorizada. |

## RAG semântico com pgvector — status local e remoto

O armazenamento vetorial está implementado no Compose local e foi exercitado
em uma implantação temporária Cloud Run/Cloud SQL. No remoto foi usado
`gemini-embedding-001` com saída de 768 dimensões, PostgreSQL 17/pgvector e
busca híbrida com RRF. Os recursos remotos foram apagados após a validação;
o perfil continua opcional e lexical segue como padrão.

| ID | Prioridade | Estado | Pendência | Critério de conclusão |
|---|---|---|---|---|
| R01 | Alta | Implementado local | Contrato Ollama `nomic-embed-text:latest`, 768 dimensões, versão de índice, timeout, limite por texto e cache local; modelo configurável. | `app/rag.py`, `EVENTOPS_RAG_MODE`, `OLLAMA_EMBEDDING_MODEL`. Dimensão/provider/modelo divergentes são recusados. |
| R02 | Alta | Implementado local | Serviço PostgreSQL 17/pgvector, volume persistente, healthcheck e criação idempotente da extensão/schema. | Perfil `rag` em `compose.yaml`; smoke vetorial em `scripts/checks/check_postgres.py`. |
| R03 | Alta | Implementado local | Sincronização transacional de chunks e metadados, hash de conteúdo, atualização e remoção idempotentes. | `PgVectorFAQ.sync`; embedding é calculado só para chunk alterado. |
| R04 | Alta | Implementado local | Busca semântica com filtros de segurança e fusão por reciprocal rank fusion (RRF) com a busca lexical; fallback lexical em erro vetorial durante consulta. | `PgVectorFAQ.search`, `search_hybrid`; limite padrão de três e threshold inicial configurado. |
| R05 | Alta | Concluído local | Dataset versionado medido em lexical e híbrido: recall@3 0,600 → 0,667, MRR 0,567 → 0,622 e abstenção 0/1 → 1/1. A amostra tem 15 perguntas com fonte e uma pergunta fora do catálogo; manter calibração em novas perguntas antes de trocar o padrão. | `evals/rag_cases.jsonl`, `scripts/evals/eval_rag.py`; limiares iniciais: vetor 0,65 e lexical 0,34. |
| R06 | Alta | Concluído local | Seis casos híbridos cobrem injeção, metadados futuros/expirados/conflitantes/não confiáveis, duplicatas e dado fora de escopo: 0 fontes bloqueadas citadas, recall 1,0 nas fontes esperadas e 0 falhas de abstenção. | `evals/rag_security_cases.jsonl`, resultado local `reports/rag-local-20261009/rag-hybrid.json`. |
| R07 | Média | Concluído para POC Cloud | Cloud Run conectou ao Cloud SQL por socket gerenciado; extensão, schema, embeddings, sincronização e busca semântica foram exercitados. A busca multilíngue retornou `acessibilidade.md#Recursos`, score final 1.0. Não é aprovação de produção: sem backups, HA, pool dedicado ou persistência operacional. | Evidência: revisão `eventops-api-00038-4kh`, smoke em 10/10/2026 e [runbook](operacao-cloud.md). |
| R08 | Média | Parcial local | `eval-rag` e o benchmark de chat publicam chamadas/tokens/duração de embedding, cache, consulta vetorial e fallback; compute/energia local ainda não tem estimativa financeira. | `scripts/evals/eval_rag.py`, `scripts/evals/benchmark_rag_chat.py`; custo de API local é zero. |

## Validações e materiais restantes

- Smoke remoto single e multi/live foi aprovado em 10/10/2026; não é gate deste
  ciclo local. A comparação Gemini não será repetida, por decisão de escopo após
  a API indicar créditos esgotados.
- Ollama/CUDA e qualidade funcional das rotas locais foram validados neste
  ambiente; falta repetir na máquina de apresentação.
- `make pre-push` passou em 11/10/2026 para o commit `718ccf1`; relatórios
  avaliam somente o candidato registrado em cada execução.
- A2A é bônus. Comparar single/multi ambos via MCP é opcional para isolar a
  orquestração. Gravação de contingência ainda não foi produzida.
- Estimativa de custo de compute/energia local (R08) foi explicitamente deixada
  fora deste ciclo.
- Dataset atual: 40 casos, 20 normais e 20 adversariais. O bloqueio histórico de
  Playwright não representa a validação aprovada em 2026-10-09.

## Validação local desta revisão

Em 11/10/2026, `make pre-push` passou no commit `718ccf1`: Ruff, formatação,
ESLint, mypy, 153 testes unitários/integração, cobertura mínima de branches,
três testes E2E, eval offline, build/instalação isolada do pacote e smoke Docker
Compose (health, catálogo/MCP, histórico e reinício). O Docker foi removido pelo
próprio smoke ao terminar. Pytest usou Python 3.14.6; a imagem foi construída
com Python 3.11.

O Ollama já ativo em container respondeu em `127.0.0.1:11434`; preservamos o
container e baixamos `qwen2.5:3b`. Também validamos `qwen3:8b`, carregado 100% na
RTX 4060 Ti com contexto 4096. Sem guardas, Qwen3:8b passou 48/120 tentativas
single no dataset pareado e gerou conteúdo incorreto em agenda/segurança. Por
isso perguntas conhecidas agora usam as ferramentas determinísticas do catálogo
e FAQ; um fallback generativo fica reservado a pedidos não reconhecidos. A
agenda com filtro de horário/nível selecionou IDs corretos em menos de 0,1 s.
Um prompt direto isolado levou 30,8 s incluindo carga inicial (17,5 s), a
82,7 tokens/s; essa medição não representa o agente com schema completo.

Em 11/10/2026, `make eval-compare-local MAX_REQUESTS=246 LOCAL_MODEL=qwen3:8b`
passou 120/120 tentativas single e 120/120 multi em três rodadas, com 0
chamadas ao modelo: intents cobertas foram encaminhadas pelas regras/tools
locais. `make eval-compare` offline também passou anteriormente 120/120 por
arquitetura. O relatório contém escopo, tentativas e hashes do candidato.

Os gates locais não validam Gemini live, encerrado por decisão de escopo. A
repetição na máquina de apresentação e a gravação de contingência são materiais
operacionais ainda não produzidos neste ambiente.

## Comparador pareado local (F02)

O runner suporta modos offline, local e live. No modo local, exige três rodadas,
teto mínimo de 246 chamadas planejadas (123 por arquitetura) e intercalamento
por caso. O relatório JSON é checkpointado atomicamente antes e depois de cada
tentativa, incluindo falhas e traces. O callback reserva o teto antes das
chamadas Ollama observáveis. Neste dataset, as intenções conhecidas usam
especialistas determinísticos e não chamam o modelo; o relatório registra essa
contagem como zero.

Validação local: preflight recusou o teto 245; testes verificam cálculo de
chamadas, credenciais, confirmação, limite de runtime, callbacks e checkpoint.
`make eval-compare-local` passou 120/120 por arquitetura, três rodadas; intents
conhecidas usam o roteamento verificado e não gastaram chamadas Ollama. Isso
conclui a implementação e a validação dentro do escopo exclusivamente local.
Em 2026-10-11, a chave Gemini autenticou, mas um teste curto retornou 402 por
créditos pré-pagos esgotados. Conforme decisão de escopo, a comparação Gemini
foi encerrada sem execução e sem aprovação G4 live.

```bash
make eval-compare-local MAX_REQUESTS=246 LOCAL_MODEL=qwen3:8b
```

## Validação das mudanças de sessões e F05–F09

**Resultado local em 2026-10-09:** `make release-check` aprovado no candidato
`d41a164b016395eb5a998809e21812c1da0a874a4bc557de35526155f9739aa1`: Ruff,
formatação, ESLint, mypy, 137 testes sem navegador, cobertura de branches (FAQ
87,5%), três testes E2E, 40/40 evals offline, wheel/sdist e smoke Compose com
catálogo/MCP, histórico/identidade e reinício. `make postgres-check` aprovou
migrations, histórico/leases, idempotência e disputa da última vaga.
`make eval-compare` aprovou 40/40 casos por arquitetura em cada uma das três
rodadas; a fixture adversarial RAG, abstenção, citação e metadados passaram.

Relatórios locais, ignorados pelo Git: `reports/build.json`,
`reports/20261009T045651Z-a9e6ea93/evals.json`,
`reports/20261009T045738Z-ad08922e/comparison.json` e
`reports/compose.json`. O release-check confirmou hashes do candidato e dos
artefatos. Esses resultados locais não aprovam qualidade live G4 nem operação
cloud G6.

```bash
make release-check PYTHON=.venv/bin/python
make postgres-check PYTHON=.venv/bin/python
make eval-compare PYTHON=.venv/bin/python
```

PostgreSQL/Compose usam recursos locais descartáveis. Contratos verificam
API/MCP compartilhando catálogo, mudanças após iniciar MCP, histórico após
reinício, isolamento de cookies, concorrência, lease expirado, rollback e
limpeza do histórico sem apagar reservas.
