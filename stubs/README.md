# Product-local type stubs

Keep third-party silence **out of** synced `mypy.ini` (Devinfra sync overwrites it).

Incomplete stubs here use `__getattr__ -> Any` so imports resolve without listing every
symbol. Append `stubs` to `MYPYPATH` in hooks/CI; basedpyright via `stubPath` in
`pyrightconfig.json` (Devinfra [#64](https://github.com/fairagro/m4.2_middleware_devinfra/issues/64)).

## What belongs where

| Stub / silence | Where | Why |
| -------------- | ----- | --- |
| `arctrl/`, `fable_library/` | Local until Devinfra → sync ([#67](https://github.com/fairagro/m4.2_middleware_devinfra/issues/67)) | Shared across middleware products |
| Extra `arctrl.py.Core.Table.*` | Product-local (this tree) | sql_to_arc imports `composite_cell` |
| One-off libs | `# type: ignore[import-untyped]` on the import | Few call sites — stubs not worth it |

Do **not** use `# type: ignore[import-untyped]` for packages covered by stubs above.
Do not patch per-module `[mypy-…]` into synced `mypy.ini`.
