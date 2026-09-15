## 1. Pytest markers

- [x] 1.1 In root `pyproject.toml` `[tool.pytest.ini_options].markers`, remove `system` and add `system_local` / `system_external` with API-compatible descriptions
- [x] 1.2 Confirm no `@pytest.mark.system` (or `pytestmark = … system`) under `middleware/`

## 2. Validate

- [x] 2.1 `openspec validate align-pytest-system-markers`
- [x] 2.2 `uv run pytest middleware/sql_to_arc/tests/ -q --collect-only` (or a short unit subset) succeeds with `--strict-markers`

## 3. Ready signal (after merge / with PR)

- [ ] 3.1 Comment on Devinfra [#120](https://github.com/fairagro/m4.2_middleware_devinfra/issues/120) that sql_to_arc markers are aligned (link PR)
