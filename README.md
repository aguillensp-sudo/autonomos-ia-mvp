# Agente IA para Autónomos

A conversational AI agent that handles the tax and social security obligations of Spanish self-employed workers (**autónomos**), replacing the traditional gestoría (accounting firm).

The autónomo uploads their invoices, the agent runs the corresponding fiscal calculation, files the declaration with the Spanish Tax Agency (AEAT), and delivers the official proof of filing — with no manual paperwork.

## Current status: MVP

The MVP covers a single process end to end:

- **P04 — IVA Trimestral (Modelo 303)**: quarterly VAT declaration. The agent reads issued and received invoices, calculates IVA repercutido/soportado, files the M303 with AEAT via RPA, and returns the signed justificante.

All other fiscal processes (P01 census registration, P09 IRPF M130, P24 RETA registration, and others) are already documented — see `docs/Autonomos.io/1. ANALISIS FUNCIONAL/` — but are out of scope until P04 is validated in production.

Full domain reference: [`docs/domain-context.md`](docs/domain-context.md).

## Architecture: two separate agent systems

This project has two layers that must not be confused, because they use different models and exist at different times:

### 1. Product (runtime) — what the autónomo actually uses

A single-agent conversational system built on **Claude Sonnet**, orchestrated with LangGraph, backed by:

- **Backend**: FastAPI + a deterministic Python fiscal engine (`src/fiscal/`) + Playwright RPA against AEAT's Sede Electrónica.
- **Frontend**: Next.js 15 + TypeScript.
- **Data**: Supabase (Postgres).

The fiscal engine never lets the LLM compute taxes — Sonnet explains results and drives the conversation; the deterministic engine calculates them. See [`docs/data-model.md`](docs/data-model.md) and [`docs/api-spec.yml`](docs/api-spec.yml).

### 2. Build harness (development-time only) — how this MVP gets written

A separate, temporary 3-agent pipeline used only while building the product, implemented directly with **Python + LangGraph** (not through this Claude Code session):

- **Orchestrator** — Opus 4.8: plans tasks from OpenSpec artifacts, decomposes work, evaluates exit criteria, reviews output for spec compliance.
- **Backend Agent** — GLM-5.2 via DeepInfra: implements Python code (API, fiscal engine, RPA) and its tests.
- **Frontend Agent** — GLM-5.2 via DeepInfra: implements Next.js/TypeScript components and Playwright E2E tests.

This pipeline disappears once the MVP is delivered — it is tooling, not part of the shipped product. See [`docs/development_guide.md`](docs/development_guide.md#agent-architecture).

## Repository structure

`backend/`, `frontend/`, and `src/` are the target layout — they do not exist yet. Everything else below is already in place.

```
autonomos-ia-mvp/
  backend/            # Product backend: FastAPI, fiscal engine, RPA, workers
  frontend/           # Product frontend: Next.js app
  src/            # Build-time only: LangGraph pipeline (Orchestrator + 2 build agents)
  docs/               # Project technical context (single source of truth)
    Autonomos.io/     # Archived source documentation (requirements, functional analysis, SDD specs)
  ai-specs/           # Agent role definitions and reusable workflow skills
  openspec/           # OpenSpec configuration
  specs/              # OpenSpec change artifacts (generated)
```

## Getting started

See [`docs/development_guide.md`](docs/development_guide.md) for prerequisites, environment setup, and how to run the backend, frontend, and tests locally.

## Methodology: Spec Driven Development

No code is written before its OpenSpec change artifacts exist. Documentation is the source of truth. Workflow:

```
/ff → /apply → /verify → /adversarial-review → /archive → /commit
```

- **`/ff`** — generate the change's `feature.md`, `design.md`, and `tasks.md`.
- **`/apply`** — implement the tasks (build harness runs the Orchestrator/Backend/Frontend loop).
- **`/verify`** — check the implementation against acceptance criteria.
- **`/adversarial-review`** — independent red-team review before archiving.
- **`/archive`** — archive the completed change.
- **`/commit`** — create focused commit(s) and manage the pull request.

Development standards: [`CLAUDE.md`](CLAUDE.md), [`docs/backend-standards.md`](docs/backend-standards.md), [`docs/frontend-standards.md`](docs/frontend-standards.md), [`docs/documentation-standards.md`](docs/documentation-standards.md).

## Roadmap after the MVP

- P05/P06/P07 — Q2/Q3/Q4 IVA (same engine as P04, different periods)
- P01/P02 — AEAT census registration (M036)
- P09 — IRPF fraccionado (M130)
- P24 — RETA registration (Importass)
- P08, P13, P14 — annual summaries and special regimes

## License

MIT — see [`LICENSE`](LICENSE).
