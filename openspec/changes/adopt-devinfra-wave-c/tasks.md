# Adopt Devinfra Wave C — Tasks

## 1. OpenSpec + branch

- [x] 1.1 Branch `issue-95-adopt-devinfra-wave-c` from `main`
- [x] 1.2 OpenSpec change with `skip_specs: true` (proposal/design/tasks)

## 2. Bake product-app

- [x] 2.1 Thin `docker/Dockerfile.sql_to_arc` last stage (ODBC in last stage)
- [x] 2.2 Root `docker-bake.hcl`: `sql_to_arc-base` + `sql_to_arc`
- [x] 2.3 Align pre-commit CST env with Bake target; smoke bake + CST 13/13 PASS

## 3. CI callers

- [x] 3.1 Add `reusable-check-local.yml` (no Trivy licence; until Devinfra #74)
- [x] 3.2 Add `feature-pull-request.yml` / `pre-release.yml` / `release.yml`
      (CQ pin #72 SHA; build/release @main; check-local)
- [x] 3.3 Delete local `python-quality.yml`, `docker-build.yml`,
      `docker-release.yml`, `pull-request-tests.yml`

## 4. Docs

- [x] 4.1 Brief AGENTS note for Wave C callers + licence workaround

## 5. Verify / handoff

- [x] 5.1 `hadolint` clean on thin Dockerfile; bake + CST green
- [ ] 5.2 Pause for user commit / push / draft PR `Fixes #95`
