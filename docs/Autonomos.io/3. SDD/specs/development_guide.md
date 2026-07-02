# Development Guide

## Prerequisites

- Python 3.12+
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
```

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

# Start Supabase local (first time takes a few minutes)
supabase start

# Run migrations
supabase db push
```

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

## Troubleshooting

**Supabase local not starting:**
```bash
supabase stop && supabase start
```

**RPA job failing with AEAT session expired:**
The Cl@ve PIN session lasts 10 minutes. If the user took longer to confirm, the agent will request a new PIN. This is handled in `src/rpa/aeat/autenticacion.py`.

**GLM-5.2 not responding via DeepInfra:**
Check DEEPINFRA_API_KEY in `.env`. GLM-5.2 model ID is `Zhipu-AI/GLM-5.2`. Rate limits apply — check DeepInfra dashboard.
