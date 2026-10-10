# Spec 08 — Execução local e infraestrutura

## Execução local

- Aplicação padrão funciona offline, sem Google API key, serviço Ollama ou rede
  externa. Docker Compose é o caminho rápido; Python 3.11 é o caminho de
  desenvolvimento.
- SQLite fica no volume `eventops-data`; `docker compose down` preserva dados e
  `docker compose down -v` remove os volumes do Compose.
- Ollama CPU/GPU e PostgreSQL/pgvector são profiles opcionais. CUDA não é
  requisito para a aplicação offline ou CI.
- Reset via Python usa `scripts/local/reset_demo.py`, com validação de modo e
  caminho restrito para evitar apagar dados fora da demo.

## CI e pacote

- `Dockerfile` constrói imagem com dependências fixadas e usuário sem privilégios.
- O wheel inclui interface, FAQ e migrations e é validado fora do checkout.
- GitHub Actions executa `make pre-push`; Husky conecta o mesmo gate ao push
  local. `make pre-push` requer daemon Docker.

## Cloud

- Terraform define Cloud Run, Artifact Registry, identidade de runtime, IAM,
  secrets e opção de Cloud SQL/pgvector. State local pode conter credenciais e
  nunca deve ser versionado.
- Os recursos temporários EventOps foram validados em 10/10/2026 e depois
  removidos. O projeto Google, APIs habilitadas e alerta geral de orçamento
  permanecem; não existe endpoint remoto ativo agora.
- Um novo smoke remoto requer recriar infraestrutura, revisar permissões e custos
  e validar a URL recém-gerada. Não reutilize state antigo nem URL documentada.
- O smoke histórico aprovou health, agenda, FAQ, Gemini single/multi, MCP,
  reserva e RAG híbrido. Isso não equivale a disponibilidade atual ou aprovação
  de produção.

## Código e validação

- Configuração: `compose.yaml`, `compose.gpu.yaml`, `Dockerfile`, `.env.example`.
- Infraestrutura: `infra/terraform/`, `scripts/cloud/`.
- Operação: [`operação local`](../operacao-local.md),
  [`runbook Cloud`](../operacao-cloud.md),
  [`quality gates`](../quality-gates.md).
- Comandos: `make pre-push`, `make postgres-check`. Para Cloud, siga o runbook e
  faça novo inventário após provisionar.
