---
description: Development rules and guidelines for this project, applicable to Claude Code in this repository.
alwaysApply: true
---

# Autónomos IA MVP — Claude Code Rules

## 1. Core Principles

- **Small tasks, one at a time**: Always work in baby steps, one at a time. Never go forward more than one step.
- **Test-Driven Development**: Start with failing tests for any new functionality (TDD), according to the task details.
- **Type Safety**: All code must be fully typed.
- **Clear Naming**: Use clear, descriptive names for all variables and functions.
- **Incremental Changes**: Prefer incremental, focused changes over large, complex modifications.
- **Question Assumptions**: Always question assumptions and inferences.
- **Pattern Detection**: Detect and highlight repeated code patterns.

## 2. Language Standards

- **English Only**: All technical artifacts must always use English, including:
    - Code (variables, functions, classes, comments, error messages, log messages)
    - Documentation (README, guides, API docs)
    - Data schemas and database names
    - Configuration files and scripts
    - Git commit messages
    - Test names and descriptions
- Spanish fiscal/legal terms (e.g. *autónomo*, *Modelo 303*, *casilla*) are preserved as proper nouns where precision requires it — see `docs/domain-context.md`.

## 3. Project Context and Standards

For detailed standards and guidelines specific to different areas of the project, refer to:

- [Domain Context](docs/domain-context.md) — the Spanish fiscal/social-security domain, glossary, MVP scope (P04)
- [Backend Standards](docs/backend-standards.md) — API development, database patterns, testing, security
- [Frontend Standards](docs/frontend-standards.md) — React/Next.js components, UI/UX guidelines
- [Documentation Standards](docs/documentation-standards.md) — technical documentation structure and maintenance
- [Data Model](docs/data-model.md) — database and domain models
- [API Spec](docs/api-spec.yml) — OpenAPI contract
- [Development Guide](docs/development_guide.md) — environment setup, running the app, agent architecture
- [OpenSpec Tasks Mandatory Steps](docs/openspec-tasks-mandatory-steps.md) — required checklist and execution rules when creating or updating OpenSpec `tasks.md` files

## 4. Project Skills

- Skills live in `ai-specs/skills`.
- When a request matches a skill, load and follow the corresponding `SKILL.md` automatically before continuing.
- Also load any referenced files in the skill folder (for example, `references/*.md`) when the skill requires them.

## 5. Planning Model Requirement

Planning workflows must run with Opus high reasoning.

This requirement applies to:
- `enrich-us`
- `openspec-ff-change`
- `openspec-continue-change`

Before starting any of these workflows, verify the session is using Opus high reasoning. If it is not, **self-correct** by adding `"model": "claude-opus-4-8"` to `.claude/settings.json` (use the `update-config` skill or edit directly), then continue — do not stop and ask the user. Do the same to come back to Sonnet medium for any other step.

**Note:** this only governs the model Claude Code itself uses while writing OpenSpec artifacts (`/ff`, `/verify`, `/adversarial-review`, etc.) in this session. It is unrelated to the separate, external build harness (Opus 4.8 + GLM-5.2 via DeepInfra, orchestrated with Python/LangGraph in `src/agents/`) that will implement the actual product code once it exists — see [Development Guide § Agent architecture](docs/development_guide.md#agent-architecture).

## 6. Symlink Integrity and Portability

- **Canonical Source**: Keep reusable artifacts in `ai-specs` as the canonical source (agent role definitions, skills). `.claude/agents` and `.claude/skills` reference them through symlinks.
- **Update Safety**: Whenever a file is renamed, moved, or its suffix changes, verify and update all symlinks that target it before considering the change complete.
- **New Artifact Linking**: Whenever creating a new artifact that requires exposure to Claude Code (for example new agents or skills in `ai-specs`), create the corresponding symlink from `.claude/`.
- **Completion Gate**: A change is incomplete if it leaves broken symlinks, stale targets, or duplicated canonical artifacts.

## 7. Mandatory OpenSpec Artifact Updates for Post-Apply Changes

When a new fix/change request appears after `opsx:apply` (or `/apply`) and before `opsx:archive` (or `/archive`), agents must treat it as a spec update first, not as an informal "fix this quickly". It's the core principle of OpenSpec: documentation is the source of truth.

Required order:

1. Update the current OpenSpec change artifacts that are affected (for example: scenarios, requirements/specs, and `tasks.md`). Don't add tasks as "bugfixes" but as part of the initial design, thus in the proper section.
2. If artifact regeneration is needed, run the corresponding OpenSpec step (`opsx:continue`, `opsx:ff`, or equivalent) before coding.
3. Implement code only after artifacts reflect the new request.
4. Re-run verification against the updated artifacts before archiving.

Do not apply direct code-only fixes in this window without updating OpenSpec artifacts.
