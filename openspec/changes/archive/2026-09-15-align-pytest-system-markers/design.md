## Context

See `proposal.md`. Root `pyproject.toml` already uses `--strict-markers` and lists `system`. Fleet SoT for marker names
is the API checkout (`system_local` / `system_external`). Devinfra #120 will filter those two names in synced pre-push.

## Goals / Non-Goals

**Goals:**

- Register the fleet marker names with compatible descriptions.
- Drop unused `system` so we do not keep a dead alias.

**Non-Goals:**

- Dual-registering `system` temporarily (no call sites to migrate).
- Implementing Devinfra #120 itself.

## Decisions

1. **Replace `system` outright with `system_local` + `system_external`** — reasoning: zero `@pytest.mark.system` usages;
   dual-register only adds noise.
2. **Copy API description wording** — reasoning: keep fleet docs/agents aligned; choose `system_local` vs
   `system_external` when adding tests later by the same criteria as the API.
3. **`skip_specs: true`** — reasoning: no domain REQUIREMENTS change.

## Risks / Trade-offs

- **[Risk] A forgotten external script still passes `-m system`** → Mitigation: grep shows none in-repo; CI uses default
  discovery without that filter today.
- **[Risk] Devinfra #120 lands before this PR** → Mitigation: merge this first (ready signal on #120); product would
  otherwise fail strict-markers on the new `-m` expression.

## Migration Plan

1. Land marker rename on issue branch; user commits/pushes; draft PR `Fixes #141`.
2. Comment on Devinfra #120 that sql_to_arc is ready.
3. No runtime rollback needed beyond reverting `pyproject.toml`.
