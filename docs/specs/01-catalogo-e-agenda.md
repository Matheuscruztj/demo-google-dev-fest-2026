# Spec 01 — Catálogo e agenda

## Comportamento esperado

- O catálogo contém 20 sessões fictícias, com IDs estáveis `S01`–`S20`, nível
  permitido, capacidade positiva e horários com fuso explícito.
- A inicialização valida os dados antes de servi-los. Contagem, IDs, datas,
  duração, enums ou capacidades inválidas interrompem a carga.
- A API e o servidor MCP consultam o mesmo catálogo persistido. O arquivo JSON
  é seed inicial e não deve substituir alterações já gravadas.
- A sugestão aceita trilha, nível, horário mínimo e limite de 1 a 3. Resultados
  respeitam os filtros e não se sobrepõem; sessões adjacentes são compatíveis.
- Se houver menos opções que o limite, a resposta informa o motivo. Um filtro
  sem correspondência retorna lista vazia.

## Código e testes

- Dados e validação: `app/data/sessions.json`, `app/data_validation.py`,
  `app/schedule.py`, `app/schemas.py`.
- Testes: `tests/unit/test_data.py`, `tests/unit/test_schedule.py`,
  `tests/integration/test_api.py`.
- Execute: `.venv/bin/python -m pytest tests/unit/test_data.py tests/unit/test_schedule.py tests/integration/test_api.py`.

## Critérios de aceite

- Os 20 IDs são únicos e válidos e usam uma data e fuso consistentes.
- Uma sugestão não ultrapassa três sessões e não contém sobreposição.
- Filtros combinados são respeitados; nenhum resultado inventado é aceito.
- Alteração incompatível do catálogo é rejeitada, especialmente quando há
  reservas existentes.

Detalhes adicionais e casos fixos estão em [matriz de cenários](../../tests/SCENARIO_MATRIX.md).
