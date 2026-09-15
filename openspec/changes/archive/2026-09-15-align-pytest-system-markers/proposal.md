## Why

Devinfra [#120](https://github.com/fairagro/m4.2_middleware_devinfra/issues/120) will change the synced pre-push pytest
invocation to:

```bash
uv run pytest -m "not system_external and not system_local"
```

This product registers only a legacy `system` marker (unused) and would fail under `--strict-markers` once that
expression lands. Align with the fleet vocabulary (`system_local` / `system_external`) used by the API.

## What Changes

- Replace `system` in `[tool.pytest.ini_options].markers` with API-compatible `system_local` and `system_external`
  descriptions.
- No test-body migration needed: there are currently **zero** `@pytest.mark.system` usages under `middleware/`.
- After merge: comment on Devinfra #120 as the ready signal.

## Capabilities

### New Capabilities

_None — `skip_specs: true` (tooling / pytest config only)._

### Modified Capabilities

_None._

## Impact

- `pyproject.toml` only (product-owned; not synced).
- Pre-push / CI behavior unchanged until Devinfra #120 syncs the `-m` filter; after that, heavy system suites (if added
  later) stay excluded by default.

## Non-goals

- Adding new system tests.
- Forking synced `.pre-commit-config.yaml` / pre-push.
- Changing coverage thresholds or other pytest `addopts`.
