# Configuration — Spec

## Purpose

Define how the converter reads, validates, and exposes configuration so that
all code has a single, typed source of truth for runtime settings.

## Requirements

- [ ] Load configuration from a YAML file at startup (path via CLI `-c`).
- [ ] Allow any field to be overridden by an environment variable or Docker
      secret, using a consistent naming convention (`{PREFIX}_{FIELD_PATH}`).
- [ ] Validate and type-coerce all values via Pydantic before the application
      starts.
- [ ] Expose the resulting `Config` object through explicit dependency injection
      — no module reads environment variables or files after startup.
- [ ] All new settings MUST be added as typed, annotated fields in `Config` (or
      a sub-model referenced by `Config`). No ad-hoc env reads, no global
      variables.
- [ ] Secrets (`connection_string`, TLS keys) use `pydantic.SecretStr`. Access
      via `.get_secret_value()` only at the point of use; never pass to `str()`
      or log them.
- [ ] Configuration is loaded **once** in `main.py` and passed down via
      function arguments. Never re-loaded during a run.

## Key Files

| File | Role |
| ---- | ---- |
| `middleware/sql_to_arc/src/middleware/sql_to_arc/config.py` | Project `Config` class (extends `ConfigBase`) |
| `middleware/sql_to_arc/config.example.yaml` | Example configuration with all fields documented |
| `middleware/shared/config/config_wrapper.py` | `ConfigWrapper` — YAML + env/secret override engine (external) |
| `middleware/shared/config/config_base.py` | `ConfigBase` — shared base class with `log_level` and `otel` fields (external) |

## Project Usage

- Loaded once in `main.py`: `ConfigWrapper.from_yaml_file(args.config, prefix="SQL_TO_ARC")`
- Prefix `SQL_TO_ARC` applies to all env/secret overrides, e.g.:
  - `SQL_TO_ARC_CONNECTION_STRING`
  - `SQL_TO_ARC_API_CLIENT_API_URL`
  - `/run/secrets/sql_to_arc_connection_string`
- `client.key` uses `tmpfs` in Docker Compose — never written to disk.
- In integration tests: mock at `middleware.sql_to_arc.main.ConfigWrapper.from_yaml_file`
  and `middleware.sql_to_arc.main.Config.from_config_wrapper`.

## Override Resolution, Type Coercion & Extension Rules

See the `config-wrapper` skill (`.agents/skills/config-wrapper/SKILL.md`) for
the full override resolution order, type coercion rules, how to extend
`ConfigBase`, and general testing patterns.
