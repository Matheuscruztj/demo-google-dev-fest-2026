# Spec 02 — FAQ e RAG

## Comportamento esperado

- O FAQ lexical usa oito documentos Markdown publicados e validados por catálogo.
- Respostas com evidência citam arquivo e seção e incluem trecho correspondente.
  O retrieval lexical retorna no máximo um melhor trecho por documento.
- Sem evidência suficiente, a resposta se abstém e não inventa fonte.
- Metadados de confiança, atualização, validade e conflito filtram fontes que não
  podem ser usadas. Fixtures adversariais permanecem fora do FAQ publicado.
- RAG híbrido é opcional. O modo padrão permanece lexical; o modo híbrido combina
  busca lexical e vetorial por RRF e usa fallback lexical se uma consulta vetorial
  falhar. Uma falha ao sincronizar o índice interrompe o startup para não servir
  índice desatualizado.
- Provider/modelo/dimensão do índice precisam corresponder à configuração atual.
  O perfil local usa Ollama e pgvector; Vertex AI foi exercitado na implantação
  temporária, que foi removida.

## Código e testes

- Retrieval lexical: `app/faq.py`, `app/data/faq/`,
  `app/data/faq_metadata.json`, `app/data_validation.py`.
- Retrieval vetorial: `app/rag.py`, perfil `rag` em `compose.yaml`.
- Testes e evals: `tests/unit/test_faq.py`, `tests/fixtures/adversarial/`,
  `evals/rag_cases.jsonl`, `evals/rag_security_cases.jsonl`.
- Comandos: `.venv/bin/python -m pytest tests/unit/test_faq.py`; `make eval-rag`;
  `make postgres-check`. Para avaliação híbrida, siga [operação local](../operacao-local.md#rag-semântico-local-opcional).

## Critérios de aceite

- Uma pergunta conhecida retorna fonte publicada e seção existentes.
- Pergunta fora do catálogo ou composta só por stopwords gera abstenção.
- Conteúdo futuro, expirado, conflitante ou não confiável não pode fundamentar
  resposta.
- Falha vetorial durante busca mantém o fallback lexical; incompatibilidade de
  índice não é ignorada.

O método e os resultados do benchmark ficam em [case de RAG](../case-benchmark-rag-local.md).
