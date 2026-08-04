# AI Agent Workflow

This document describes how AI coding agents (GitHub Copilot, Cursor, etc.)
are integrated into this project and how the supporting artifacts are structured.

---

## Overview

The workflow is built on these standards:

| Standard | Purpose | URL |
| -------- | ------- | --- |
| **agents.md** | Central entry point — gives agents project context at startup | <https://agents.md/> |
| **OpenSpec** | Spec-driven development — domain specs + change deltas | <https://github.com/Fission-AI/OpenSpec> |
| **Agent Skills** | On-demand procedural knowledge — loaded by agents when relevant | <https://agentskills.io/> |

---

## VS Code / Cursor Integration

| Artifact | Mechanism |
| -------- | --------- |
| `AGENTS.md` | Loaded automatically as an instructions file. |
| `.agents/skills/*/SKILL.md` | Project skills (arctrl, config-wrapper). |
| `.cursor/commands/opsx-*.md` + `.cursor/skills/openspec-*/` | Cursor OpenSpec slash commands (`/opsx-propose`, …). |
| `.github/prompts/opsx-*.prompt.md` + `.github/skills/openspec-*/` | GitHub Copilot OpenSpec prompts/skills. |
| `openspec/specs/**/*.md` | Not auto-loaded — agents follow links from `AGENTS.md` or an active change. |

Restart the IDE after OpenSpec init/update so new commands appear.

---

## OpenSpec Workflow

Specs describe **current** behavior under `openspec/specs/<domain>/spec.md`.
Work happens in change folders under `openspec/changes/<name>/` with:

| Artifact | Purpose |
| -------- | ------- |
| `proposal.md` | Why and what is changing |
| `specs/` | Delta specs (`ADDED` / `MODIFIED` / `REMOVED`) |
| `design.md` | Technical approach for this change |
| `tasks.md` | Implementation checklist |

**Default loop (Cursor):**

```text
/opsx-explore  →  /opsx-propose  →  /opsx-apply  →  /opsx-archive
```

**GitHub Copilot:** use the matching `opsx-*` prompts from
**Chat: Open Customizations** / `.github/prompts/`.

After `/opsx-archive`, delta requirements merge into `openspec/specs/` and the
change moves to `openspec/changes/archive/`.

CLI helpers:

```bash
openspec list --specs
openspec validate --specs
openspec list
openspec validate <change-name>
```

Project context and artifact rules live in [`openspec/config.yaml`](../openspec/config.yaml).

### Domain layout

```text
openspec/specs/
├── principles/              # Foundation contract
├── configuration/           # ConfigWrapper / secrets
├── demo-environment/        # Local demo stack
├── tooling-consistency/     # Editor / hooks / CI parity
├── sql-to-arc-conversion/   # Pipeline orchestration
├── arc-building/            # mapper + builder
├── database-access/         # SQL views + row models
└── api-upload/              # Middleware API upload
```

Optional `design.md` next to a domain `spec.md` documents **current** Key
Decisions (not delta design for a change).

---

## When To Use Which Command

| Situation | Use |
| --------- | --- |
| Active change ready to implement | `/opsx-apply` |
| Exploring before committing to a change | `/opsx-explore` |
| New change from an idea | `/opsx-propose` |
| Fold deltas into main specs | `/opsx-archive` |
| Library how-to (arctrl / ConfigWrapper) | default Agent + matching skill |

No custom Copilot/VS Code agents are required — OpenSpec commands and skills
cover the workflow.

---

## Entry Point: `AGENTS.md`

[`AGENTS.md`](../AGENTS.md) is the single entry point for all AI agents. It
contains tech stack, structure, essential commands, and the OpenSpec domain
index. It links to specs instead of duplicating them.

---

## Agent Skills: `.agents/skills/`

```text
.agents/
└── skills/
    ├── arctrl/
    │   └── SKILL.md                  # How to use the arctrl Python library
    └── config-wrapper/
        └── SKILL.md                  # How to use ConfigWrapper / ConfigBase
```

OpenSpec workflow skills are installed separately under `.cursor/skills/` and
`.github/skills/` (`openspec-*`). Do not hand-edit those; refresh with
`openspec update`.

Skills are **project-neutral** where possible. Project-specific constraints
belong in OpenSpec domain specs or `openspec/config.yaml`.

---

## Workflow in Practice

When an agent starts a task it:

1. Loads `AGENTS.md` → project context, commands, OpenSpec domain links.
2. If an active change exists → reads `openspec/changes/<name>/`.
3. Else if the task touches a domain → reads `openspec/specs/<domain>/spec.md`
   (and `design.md` when present).
4. If library knowledge is needed → loads `arctrl` or `config-wrapper`.
5. After editing → `uv run ruff format .` and `uv run pytest`, then check
   Problems / diagnostics.

### Example: Adding a New Config Field

1. Prefer `/opsx-propose` for a change that modifies `configuration`.
2. Or read `openspec/specs/configuration/spec.md` + `config-wrapper` skill.
3. Edit `config.py`, format, run tests.

### Example: Fixing an ARC Serialization Bug

1. Read `openspec/specs/arc-building/spec.md` and `design.md`.
2. Load the `arctrl` skill.
3. Edit `builder.py` / `mapper.py`, format, run tests.

---

## Adding New Skills Or Spec Domains

### New project skill

Use `/create-skill` (Copilot) or create `.agents/skills/<name>/SKILL.md`
manually. Keep skills project-neutral; put FAIRagro constraints in OpenSpec.

### New behavior (preferred)

```text
/opsx-propose <short-change-name>
```

OpenSpec creates the change folder and delta specs. Implement with
`/opsx-apply`, then `/opsx-archive` to merge into `openspec/specs/`.

Do **not** create folders under a legacy Specifica layout (`spec/` or
`middleware/*/spec/`). Those paths were removed in favor of OpenSpec.
