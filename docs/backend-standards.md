# Backend Standards

## Stack

- **Language:** Python 3.14 (strict typing, Pydantic v2 for all models). Deviation from the original 3.12 spec: written before the 3.14 release, fully compatible.
- **API framework:** FastAPI 0.115+ with async/await throughout
- **Agent orchestration:** LangGraph 0.4+ (StateGraph, interrupt nodes, PostgresSaver checkpointing)
- **LLM — Orchestrator:** Claude Opus 4.8 (planning, evaluation, exit-criteria, reviewer nodes)
- **LLM — Agents:** GLM-5.2 via DeepInfra (backend-agent and frontend-agent execution nodes)
- **LLM — Conversational interface:** Claude Sonnet 5 (claude-sonnet-5, user-facing conversation and OCR)
- **RPA:** Playwright 1.45+ Python, headless Chromium, selector map in external config file
- **Database:** Supabase (PostgreSQL 16, Row Level Security enforced on all tables)
- **Storage:** Supabase Storage (PDF justificantes, uploaded invoices)
- **Auth:** Supabase Auth (JWT, per-user RLS enforcement)
- **Queue:** ARQ + Redis 7 (async workers for RPA jobs)
- **Server:** Uvicorn (ASGI), single Docker Compose service in MVP

## Architecture principles

- **LLM never calculates taxes.** All fiscal logic lives in deterministic Python functions in `src/fiscal/`. The LLM is conversational interface only.
- **Human-in-the-loop is mandatory.** Every presentation to AEAT requires explicit user confirmation. LangGraph `interrupt` node handles this — never skip it.
- **Stateful agents via checkpointing.** LangGraph state persists in PostgreSQL via `PostgresSaver`. If a session is interrupted, it resumes exactly where it stopped using `thread_id`.
- **RPA selector map is external.** All Playwright CSS/aria selectors for the AEAT website live in `src/rpa/selectors/aeat_m303.yml`. When AEAT updates their UI, only that file changes — no code changes needed.
- **Fiscal correctness over speed.** A wrong tax calculation is a sanction for the user. Tests must cover all casuísticas documented in the Excel process files before any feature is considered done.

## Project structure

```
src/
  api/
    routers/
      p04.py          # IVA trimestral endpoints
      health.py
    dependencies.py   # Auth, DB session injection
    main.py
  agents/
    orchestrator/     # Opus 4.8 — supervisor node
    backend_agent/    # GLM-5.2 — backend execution
    frontend_agent/   # GLM-5.2 — frontend execution
    graphs/
      p04_graph.py    # LangGraph StateGraph for P04
    state.py          # TypedDict state definition
  fiscal/
    iva/
      calcular_devengado.py    # includes rectificativa routing (Phase 2)
      calcular_deducible.py
      calcular_resultado.py    # includes devolucion vs compensacion (Phase 2)
      validar_coherencia.py
      tabla_deducibilidad.py   # 22-category table (Phase 2)
      calcular_isp.py          # Phase 2: Inversion del Sujeto Pasivo
      calcular_bloque_informativo.py  # Phase 2: casillas 59-63
      criterio_caja.py         # Phase 2: filtro por cobro/pago
      actualizar_saldo_iva_compensar.py  # Phase 2: unico modulo con I/O a Supabase
      calcular_m303.py         # Phase 2: orquestador end-to-end
      prorrata_alerta.py       # Phase 2: casuistica C07, solo alerta
    models.py         # Pydantic models: Factura, ResultadoM303, etc.
  rpa/
    aeat/
      autenticacion.py
      m303_form.py
      justificante.py
    selectors/
      aeat_m303.yml   # External selector map — never hardcode selectors in Python
  workers/
    rpa_worker.py     # ARQ worker definition
  db/
    supabase.py       # Client, RLS-aware queries
    migrations/       # SQL migration files
```

## API endpoints (MVP P04)

```
POST /api/proceso/p04/iniciar          → Start P04 process for authenticated user
POST /api/proceso/p04/facturas         → Upload invoice (PDF/image), returns OCR extraction
POST /api/proceso/p04/calcular         → Run fiscal engine, return M303 calculation
POST /api/proceso/p04/confirmar        → User confirms — enqueues RPA job
GET  /api/proceso/p04/estado           → Poll process state (pending/running/done/error)
GET  /api/proceso/p04/justificante     → Download PDF justificante from Supabase Storage
GET  /health                           → Health check
```

## Fiscal engine rules

- All fiscal functions are **pure functions**: same input always produces same output.
- Every function has **full type annotations** and **docstrings** with the legal reference (e.g. `Art. 92 LIVA`).
- **No rounding in intermediate steps.** Round only at the final output, to 2 decimal places.
- The `tabla_deducibilidad.py` module is a **data file**, not logic. It maps expense categories to deductibility percentages. Update data there, never in calculation functions.
- The **ISP (Inversión del Sujeto Pasivo)** path is mandatory: invoices from foreign suppliers without Spanish NIF trigger ISP auto-liquidation.

## Testing requirements

- **100% coverage** on all `src/fiscal/` modules before any feature is done.
- Use **pytest** with fixtures defined in `tests/fixtures/facturas.py` (seed data for 3 autónomo profiles).
- Each casuística documented in the P04 Excel (Hoja 5) must have at least one test.
- Integration tests use **real Supabase** (test project), never mocks for DB.
- RPA tests use **mock responses** (stub AEAT HTTP responses) — never hit real AEAT in tests.
- Test naming: `test_<function>_<scenario>` e.g. `test_calcular_deducible_vehiculo_uso_mixto`.

## Database conventions

- All tables have `user_id UUID REFERENCES auth.users(id)` with RLS policy `user_id = auth.uid()`.
- Never query without RLS. Never use service role key in application code — only in migrations.
- Migration files: `YYYYMMDD_HHMMSS_description.sql` in `src/db/migrations/`.
- Table names: snake_case, singular nouns matching Excel Hoja 6 spec: `factura_emitida`, `factura_recibida`, `presentacion`, `saldo_iva_compensar`, `alerta`.
- Timestamps: always `TIMESTAMPTZ`, always UTC.

## LangGraph agent architecture

```
Orchestrator (Opus 4.8)
  ├── plans tasks from specs
  ├── evaluates exit criteria
  ├── reviews output against OpenSpec
  └── escalates to user (HitL interrupt) when needed

Backend Agent (GLM-5.2)
  ├── implements Python code
  ├── writes and runs tests
  └── iterates on failures

Frontend Agent (GLM-5.2)
  ├── implements Next.js components
  ├── runs Playwright E2E
  └── iterates on failures
```

Node exit criteria evaluated by Opus 4.8:
- All tests green
- Coverage ≥ 100% on fiscal modules
- No TypeScript errors
- OpenSpec artifacts up to date

## Error handling

- All FastAPI endpoints return structured errors: `{"error": "CODE", "detail": "...", "proceso": "P04"}`.
- RPA failures save a screenshot to Supabase Storage and set process state to `error` with `error_code`.
- LangGraph errors trigger the `escalation` node → user notification with clear description and retry option.
- Never swallow exceptions silently. Every except block must log with context.

## Environment variables

```
ANTHROPIC_API_KEY          # Claude Opus 4.8 + Sonnet 5
DEEPINFRA_API_KEY          # GLM-5.2
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_KEY       # Migrations only
REDIS_URL
LANGSMITH_API_KEY          # Observability
```
