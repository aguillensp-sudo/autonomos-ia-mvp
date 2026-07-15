# Development Guide

## Prerequisites

- Python 3.14 (deviation from the original 3.12 spec — spec was written before the 3.14 release; 3.14 is fully compatible with the stack used here)
- Node.js 20.19+
- Docker + Docker Compose
- Supabase CLI (`npm install -g supabase`)
- OpenSpec CLI (`npm install -g @fission-ai/openspec@latest`)

## Environment setup

### 1. Clone and bootstrap

```bash
git clone https://github.com/aguillensp-sudo/autonomos-ia-mvp.git
cd autonomos-ia-mvp
```

### 2. Backend environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...      # Opus 4.8 + Sonnet 5
DEEPINFRA_API_KEY=...             # GLM-5.2
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...       # For migrations only
REDIS_URL=redis://localhost:6379
LANGSMITH_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true        # Enables LangSmith tracing (Phase 3 onwards)
LANGCHAIN_PROJECT=autonomos-ia-mvp
```

**`ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY`, `LANGCHAIN_TRACING_V2`, and `LANGCHAIN_PROJECT` are mandatory from Phase 3 (`agente-conversacional`) onwards.** Phases 1–2 (`src/fiscal/`) never call an LLM, so these keys were optional placeholders until then. Starting Phase 3, `src/agent/` and its test suite make real Claude Sonnet 5 calls — tool-calling in `recopilar_datos`, Vision OCR in `ocr.py`, the `interrupt()`/confirmation flow — and real LangSmith tracing via `crear_cliente_anthropic()`. `LANGCHAIN_TRACING_V2=true` turns tracing on and `LANGCHAIN_PROJECT` names the LangSmith project (`autonomos-ia-mvp`) traces are grouped under. Running `pytest tests/agent/` without a valid `ANTHROPIC_API_KEY` fails outright; without `LANGSMITH_API_KEY`/`LANGCHAIN_TRACING_V2` the client falls back to an unwrapped Anthropic client (tests still pass, but tracing is unavailable).

### 3. Frontend environment

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

Fill in `.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Local services (Redis + Supabase local)

```bash
# Start Redis
docker compose up redis -d

# Start Supabase local (first time takes a few minutes — pulls Docker images)
supabase start

# Migrations under src/db/migrations/ are mirrored into supabase/migrations/
# (Supabase CLI naming convention: YYYYMMDDHHMMSS_description.sql) and are
# applied automatically by `supabase start`. To apply new ones incrementally:
supabase migration up
```

**Local vs. remote Supabase — why both exist:** development uses **local Supabase** (via Docker, as above); production uses the **remote Supabase project** (`autonomos-ia-mvp`). This split was adopted during Phase 1 (`fiscal-engine-fundamentos`) because the remote project got stuck in `COMING_UP` status during a Supabase Cloud incident. Local development is not blocked by remote Cloud availability, so it remains the default for day-to-day work even after the incident resolves — the remote project is provisioned and used for production/staging only.

**Windows note:** if `supabase start` fails with `supabase_analytics_... container is not ready: unhealthy`, this is a known Windows limitation (Logflare/analytics needs the Docker daemon exposed over TCP, which we don't configure). Set `enabled = false` under `[analytics]` in `supabase/config.toml` — analytics is not used by this project.

### 5. Seed data

```bash
cd backend
python scripts/seed_data.py      # Creates 3 autónomo test profiles with invoices
```

## Running locally

### Start all services

```bash
# Terminal 1 — Backend API
cd backend
uvicorn src.api.main:app --reload --port 8000

# Terminal 2 — ARQ worker (RPA jobs)
cd backend
python -m arq src.workers.rpa_worker.WorkerSettings

# Terminal 3 — Frontend
cd frontend
npm run dev
```

App available at: `http://localhost:3000`
API docs at: `http://localhost:8000/docs`

## Running tests

### Backend unit tests (fiscal engine)

```bash
cd backend
pytest tests/fiscal/ -v --cov=src/fiscal --cov-report=term-missing
```

Coverage must be 100% on `src/fiscal/` before any PR.

### Backend integration tests

```bash
# Requires local Supabase running
pytest tests/integration/ -v
```

### Conversational agent tests (Phase 3 onwards)

```bash
# Requires ANTHROPIC_API_KEY (real Claude Sonnet 5 calls), local Supabase
# running (checkpointing + Storage), and LANGSMITH_API_KEY for tracing
pytest tests/agent/ -v --cov=src/agent --cov-branch --cov-report=term-missing
```

Coverage must be 100% (line + branch) on `src/agent/`, same bar as `src/fiscal/`.

### RPA / AEAT tests (Phase 4 onwards)

```bash
pytest tests/rpa/ tests/workers/ -v --cov=src/rpa --cov=src/workers --cov-branch --cov-report=term-missing
```

Playwright is fully mocked in every test above — no real browser session against AEAT is opened, and no live AEAT credentials are required to run this suite. **One exception**: `tests/rpa/aeat/test_autenticacion.py::test_autenticar_clave_movil_sesion_real` is marked `@pytest.mark.integration` and drives a *real* Cl@ve Móvil (QR) login against the live AEAT Sede Electrónica. It cannot be run by an agent — it requires a human to supply their real NIF and scan the displayed QR with their own phone's Cl@ve Móvil app:

```bash
pytest tests/rpa/aeat/test_autenticacion.py -m integration -v
```

`pytest -m "not integration"` (the default TDD cycle) always excludes it.

### Frontend E2E tests (Playwright)

```bash
cd frontend
npx playwright install chromium     # First time only
npx playwright test
```

## OpenSpec workflow

This project follows Spec Driven Development with the OpenSpec CLI.

```bash
# Initialize OpenSpec (first time)
openspec init

# Create a new change from a spec
/ff <change-name>          # Generate feature.md + design.md + tasks.md

# Implement a change
/apply <change-name>       # Orchestrator runs the implementation loop

# Verify implementation
/verify <change-name>      # Orchestrator checks against acceptance criteria

# Review before merging
/adversarial-review <change-name>

# Archive and commit
/archive <change-name>
/commit
```

**Important:** The orchestrator (Opus 4.8) switches automatically between models during the workflow. Opus handles planning and review; GLM-5.2 handles code generation. This is configured in `openspec/config.yml`.

## Agent architecture

The development pipeline uses a 3-agent system:

```
Opus 4.8 (Orchestrator)
  ├── Reads specs from ai-specs/
  ├── Decomposes tasks
  ├── Evaluates exit criteria
  └── Reviews output for spec compliance

GLM-5.2 via DeepInfra (Backend Agent)
  ├── Implements Python code (FastAPI, fiscal engine, RPA)
  ├── Writes pytest tests
  └── Iterates on test failures

GLM-5.2 via DeepInfra (Frontend Agent)
  ├── Implements Next.js/TypeScript components
  ├── Runs Playwright E2E tests
  └── Iterates on test failures
```

## Project structure

```
autonomos-ia-mvp/
  backend/
    src/
      api/          # FastAPI routes and dependencies
      agents/       # LangGraph graphs and agent nodes
      fiscal/       # Deterministic tax calculation engine
      rpa/          # Playwright automation for AEAT
      workers/      # ARQ async workers
      db/           # Supabase client and migrations
    tests/
      fiscal/       # Unit tests (100% coverage required)
      integration/  # Integration tests against real Supabase
  frontend/
    app/            # Next.js App Router pages
    components/     # React components
    lib/            # Supabase client, API wrappers, types
    e2e/            # Playwright E2E tests
  ai-specs/
    agents/         # Agent role definitions
    skills/         # Reusable workflow skills
  docs/             # This folder — project technical context
  specs/            # OpenSpec change artifacts (generated)
  openspec/
    config.yml      # OpenSpec configuration
```

## Key decisions

- **No code before specs.** Every feature starts with an OpenSpec change (`/ff`). The implementation follows the tasks.md — never the other way around.
- **Fiscal engine is sacred.** Never modify `src/fiscal/` without a failing test first (TDD). A wrong calculation is a legal problem.
- **RPA selectors in config.** Never hardcode AEAT selectors in Python code. `src/rpa/selectors/aeat_m303.yml` is the only place they live.
- **Human confirmation is non-negotiable.** The `/api/proceso/p04/confirmar` endpoint must only be called after the user has clicked the ConfirmacionModal. No auto-confirmation under any circumstances.
- **Phase 3 stops at `confirmado=True`.** The `agente-conversacional` graph (`src/agent/graph.py`) ends at the `notificar` node once the user confirms via the `confirmar` `interrupt()` — it never files anything with the AEAT. `notificar` upserts a `presentacion` row in `estado='confirmado'` (SPEC-F4-00, added in Phase 4) so the RPA worker has something to pick up.
- **Phase 4 (`rpa-aeat`) is the RPA module + ARQ worker only — not the enqueueing endpoint.** `src/workers/rpa_worker.py::procesar_presentacion` drives one `presentacion` row through `estado='confirmado' -> presentando -> presentado|error`, but nothing in Phase 4 enqueues that ARQ job. `/api/proceso/p04/confirmar` (Phase 5) is what will actually enqueue it once a chat UI exists — Phase 4 does not touch `src/api/`.
- **Deducible casilla-group mapping is data, not logic.** `src/rpa/casilla_map.py::TABLA_CASILLA_DEDUCIBLE` (Product-Owner-approved) maps each `categoria_gasto` to its AEAT casilla group (corriente/inversión/intracomunitario). Adding a new expense category updates this file, never `m303_form.py`.

## Troubleshooting

**Supabase local not starting:**
```bash
supabase stop && supabase start
```

**RPA job failing with AEAT session expired:**
The Cl@ve Móvil session lasts 10 minutes from authentication. If the user took longer than that to scan the QR and confirm, the job must restart from a fresh QR. This is handled in `src/rpa/aeat/autenticacion.py` (`SesionExpiradaError`).

**GLM-5.2 not responding via DeepInfra:**
Check DEEPINFRA_API_KEY in `.env`. GLM-5.2 model ID is `Zhipu-AI/GLM-5.2`. Rate limits apply — check DeepInfra dashboard.
