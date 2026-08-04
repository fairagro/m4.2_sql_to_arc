# Tooling Consistency

## Purpose

Ensure VS Code editor tools, pre-commit hooks, and GitHub CI workflows all
report identical results for the same code by sharing a single configuration
source of truth.

## Requirements

### Requirement: Same Tool Invocation Everywhere

Every quality tool (Ruff, mypy, pylint, bandit) MUST be invoked via
`uv run <tool>` in all three environments (VS Code extension, pre-commit
hook, CI workflow step), ensuring the same installed version is used.

#### Scenario: Lint locally and in CI

- GIVEN the same commit
- WHEN Ruff is run in the editor, pre-commit, and CI
- THEN all three use `uv run` and the same tool version

### Requirement: Shared Config Files Only

Every tool MUST read its configuration exclusively from `pyproject.toml`
(or the repo-root config file for tools that do not support
`pyproject.toml`, e.g. `.bandit`). Per-environment config overrides are
forbidden.

#### Scenario: Changing a Ruff rule

- GIVEN a Ruff setting is updated in `pyproject.toml`
- WHEN editor, hook, and CI run
- THEN all three apply the same rule without local overrides

### Requirement: Editor Uses Environment Binaries

VS Code extensions MUST be configured to use `importStrategy:
fromEnvironment` (or equivalent) so they pick up the same binary and
version as the `uv run` invocations in hooks and workflows.

#### Scenario: Extension resolves Ruff

- GIVEN `importStrategy: fromEnvironment` and the `.venv` interpreter
- WHEN the VS Code Ruff extension runs
- THEN it uses the same binary as `uv run ruff`

### Requirement: Matching Config Paths In Editor Settings

VS Code extension settings that reference a config file MUST pass the same
path that the hook and workflow use (e.g. `--config-file pyproject.toml`).

#### Scenario: Pylint config path

- GIVEN pylint is configured with `--config-file pyproject.toml` in CI
- WHEN the editor invokes pylint
- THEN it uses the same config path

### Requirement: Centralized Stub Suppressions

If a third-party library has no type stubs and no `py.typed` marker, the
suppression MUST be declared once in `pyproject.toml`
`[[tool.mypy.overrides]]`, not scattered across individual `# type: ignore`
comments.

#### Scenario: Untyped library used in multiple modules

- GIVEN a library without stubs is imported in several files
- WHEN mypy runs in editor, hook, and CI
- THEN the single `[[tool.mypy.overrides]]` entry applies equally everywhere

### Requirement: Add Tools To All Environments Together

Adding a new quality tool to any one environment MUST also add it to all
three in the same commit.

#### Scenario: Introducing a new checker

- GIVEN a new quality tool is adopted
- WHEN the commit lands
- THEN editor settings, pre-commit, and CI all invoke it

### Requirement: Glob Overrides Cover Submodules

When a library subpackage has a different dotted path from the top-level
package (e.g. `arctrl.py.Core.*` vs. `arctrl`), the mypy override MUST use
a glob that covers all submodules (`["arctrl", "arctrl.*"]`).

#### Scenario: arctrl submodule import

- GIVEN code imports `arctrl.py.Core.*`
- WHEN mypy runs in the editor and in pre-commit
- THEN both apply the same override
- AND the editor does not silently hide an error the hook would catch
