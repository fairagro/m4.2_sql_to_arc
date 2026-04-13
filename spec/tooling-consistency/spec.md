# Tooling Consistency

The VS Code editor tools, the pre-commit hooks, and the GitHub CI workflows
must all report identical results for the same code. All three execution
environments must draw their configuration from a single source of truth
(`pyproject.toml` or the respective config file at the repo root) so that a
passing local commit never fails in CI, and the editor never silently hides an
issue that the hook or workflow would catch.

## Requirements

- [ ] Every quality tool (Ruff, mypy, pylint, bandit) is invoked via
      `uv run <tool>` in all three environments (VS Code extension, pre-commit
      hook, CI workflow step), ensuring the same installed version is used.
- [ ] Every tool reads its configuration exclusively from `pyproject.toml` (or
      the repo-root config file for tools that do not support `pyproject.toml`,
      e.g. `.bandit`); no per-environment config overrides are permitted.
- [ ] VS Code extensions are configured to use `importStrategy:
      fromEnvironment` (or equivalent) so they pick up the same binary and
      version as the `uv run` invocations in hooks and workflows.
- [ ] VS Code extension settings that reference a config file pass the same
      path that the hook and workflow use (e.g. `--config-file pyproject.toml`).
- [ ] If a third-party library has no type stubs and no `py.typed` marker, the
      suppression is declared once — in `pyproject.toml`
      `[[tool.mypy.overrides]]` — not scattered across individual `# type:
      ignore` comments. This ensures the suppression applies equally in the
      editor, the hook, and CI.
- [ ] Adding a new quality tool to any one environment requires adding it to
      all three in the same commit.

## Edge Cases

A library subpackage has a different dotted path from the top-level package
(e.g. `arctrl.py.Core.*` vs. `arctrl`) → the mypy override must use a glob
that covers all submodules (`["arctrl", "arctrl.*"]`), otherwise the VS Code
daemon silences the error while the pre-commit hook still fails.

A VS Code extension runs its tool outside the `uv` virtual environment →
`importStrategy: fromEnvironment` combined with `python.defaultInterpreterPath`
pointing at the `.venv` interpreter resolves this; the extension then uses the
same binary and config as `uv run`.
