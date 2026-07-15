# Change: integracion-mvp

## Phase

F5 — Integración y MVP completo (`docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §7). Maps to `openspec/config.yaml` → `acceptance_criteria.phase_5`.

## Objective

Integrate every prior phase into a single working system: a real autónomo can log in, talk to the agent, upload invoices, review the calculation, confirm, and receive the official AEAT justificante — without any human intervention beyond their own clicks. This phase builds the FastAPI layer wrapping Phase 3's LangGraph graph, the minimal Next.js frontend, the ARQ worker registration Phase 4 deliberately deferred, and Supabase Realtime notifications tying RPA progress to the UI.

## Agents involved (per `openspec/config.yaml`)

- **orchestrator** (`claude-opus-4-8`) — plans this change, evaluates exit criteria, runs `fiscal_integrity_checks` and `ui_integrity_checks`
- **backend_developer** (`claude-sonnet-4-6`) — FastAPI endpoints, LangGraph wiring, ARQ `WorkerSettings`/retry, Supabase Realtime publication, alert scheduling
- **frontend_developer** (`claude-sonnet-4-6`) — Next.js 15 App Router components, Playwright E2E

## Architectural decision found during research — the chat is the single source of truth

`docs/api-spec.yml` was written before Phase 3's LangGraph decision existed. Its `/calcular` endpoint describes accepting `facturas_emitidas`/`facturas_recibidas` arrays directly and running the fiscal engine independently — a **second, parallel calculation path** that would compete with Phase 3's `EstadoP04`/checkpointer as the source of truth for a declaration in progress.

**Resolution, in scope for this change:** there is exactly one source of truth per declaration — the LangGraph checkpointed state (`thread_id = f"{user_id}:P04:{ejercicio}:{periodo}"`, already built in Phase 3). Every endpoint in this phase is a thin HTTP wrapper over `graph.invoke()` / `graph.update_state()` / `Command(resume=...)`, keyed by `proceso_id` (= `thread_id`). The frontend's structured components (`FacturaUploader`, `FacturaReviewer`, `ResumenIVA`, `ConfirmacionModal`) are not a bypass of the chat — they are alternate **renderings** of specific graph interrupts or node outputs, and structured invoice data reaches the graph via `graph.update_state()`, never a second fiscal computation. See `design.md` SPEC-F5-01 for the full endpoint-to-graph-lifecycle mapping.

## Second gap found during research — the OCR upload endpoint collides with an existing path

`docs/api-spec.yml`'s `POST /api/proceso/p04/facturas` (multipart, OCR extraction) uses the exact same path and method as Phase 1's already-shipped `POST /api/proceso/p04/facturas` (`src/api/routers/p04.py`, JSON body, manual invoice CRUD). FastAPI cannot dispatch two route handlers on identical path+method by content-type alone.

**Resolution, in scope for this change:** the OCR upload endpoint moves to `POST /api/proceso/p04/facturas/ocr` — a new, distinct path. Phase 1's existing `/facturas` JSON CRUD endpoint is untouched. This is a documented deviation from `docs/api-spec.yml`'s literal path, not a silent one — see `design.md` SPEC-F5-01.

## Third gap found during research — ARQ retry for Cl@ve Móvil session expiry

Phase 4 explicitly deferred ARQ `WorkerSettings` (queue registration, retry policy) to this phase (`specs/archive/rpa-aeat/design.md`, MEDIUM-2 amendment). CA-F5-03 requires that an expired Cl@ve Móvil session (>10 minutes between QR display and confirmation) triggers a fresh QR and completes the filing without losing any entered data — this is exactly the retry logic Phase 4 left undone.

**Resolution, in scope for this change:** this phase builds the `WorkerSettings` class and a retry policy that distinguishes `error_code='sesion_expirada'` (retryable — re-run `ejecutar_presentacion`, which re-authenticates with a fresh QR from scratch, per Phase 4's idempotency guard) from every other error code (terminal — surfaced to the user as `estado='error'`, no automatic retry). See `design.md` SPEC-F5-02.

## Scope

In scope:
- `src/api/main.py`, `src/api/routers/p04.py` — five endpoints per `docs/api-spec.yml` (adjusted per the two resolutions above): `POST /iniciar`, `POST /facturas/ocr`, `POST /mensaje/{proceso_id}` (new — gap-filled, see SPEC-F5-01), `POST /calcular`, `POST /confirmar`, `GET /estado/{proceso_id}`, `GET /justificante/{proceso_id}`.
- `src/agent/graph.py` wiring: every endpoint above drives the existing Phase 3 graph via `graph.invoke()`/`graph.update_state()`/`Command(resume=...)` — no new LangGraph nodes, no new fiscal logic.
- `src/workers/rpa_worker.py` amendment: `WorkerSettings` class (queue registration, `max_tries`, retry-on-`sesion_expirada` policy) — the piece Phase 4 explicitly deferred.
- `src/api/routers/p04.py`'s `/confirmar` handler enqueues the ARQ job (`procesar_presentacion`) after the graph's `confirmar` interrupt resolves to `confirmado=True` — this is the enqueueing Phase 4 deferred.
- Next-quarter alert scheduling (CA-F5-07): after a successful presentation, insert an `alerta` row for the following quarter's deadline.
- Supabase Realtime: enable replication on `presentacion` (and read-only exposure of the deterministic `qr-clave` Storage path) so the frontend can react to RPA state changes without polling.
- Frontend (`frontend/`, new — no frontend exists yet): `ChatInterface`, `FacturaUploader`, `FacturaReviewer`, `ResumenIVA`, `ConfirmacionModal`, RPA status component (4 states), QR display panel.
- Context management (D11): a rolling-window trim of `EstadoP04.mensajes` when a session's turn count exceeds 15, applied inside `recopilar_datos` before the LLM call. Per-conversation summarization is the documented V2 alternative if the window proves too lossy in practice.
- Full E2E happy path (CA-F5-01/02) and the 4 other Playwright scenarios CA-F5-03 through CA-F5-06 require.

Out of scope (later phases / explicitly excluded per `openspec/config.yaml`):
- P05/P06/P07 (Q2/Q3/Q4 IVA), P08, P09, P13, P14, P24-P26, régimen foral.
- Authentication Model A (certificate vault).
- Any UI beyond the minimal conversational interface (no dashboard, no settings screens) — per the PDR's "Frontend completo con dashboard: V2" decision.
- D11's periodic-summarization alternative — only the rolling window ships this phase; summarization stays a documented fallback, not built.
- Docker/deployment (`SPEC-F5-05` in the functional spec) — **flagged as a real gap**: the functional spec's own `Specs a completar antes de codificar` list includes a deployment spec (Dockerfile, docker-compose.yml, rollback procedure) that this change does not cover. Deployment is tracked as a follow-up, not silently dropped — see `design.md`'s closing note.

## Acceptance criteria

Maps directly to CA-F5-01 through CA-F5-10:

| ID | Criterion |
|---|---|
| CA-F5-01 | Full happy path end-to-end with a real test autónomo: chat → invoices → calculation summary → confirm → AEAT justificante, under 5 minutes |
| CA-F5-02 | Same flow works when 3 invoices are uploaded as PDF/image instead of typed — OCR extracts, user reviews, flow continues |
| CA-F5-03 | If the Cl@ve Móvil session expires mid-presentation (>10 min), the agent requests a fresh QR and completes the filing without losing any entered data |
| CA-F5-04 | A simulated AEAT error during presentation notifies the user clearly, persists process state, and lets them resume when they choose |
| CA-F5-05 | Two concurrent users never see each other's data (RLS) |
| CA-F5-06 | The justificante PDF is stored in Supabase Storage, accessible to its owner, `403` for anyone else |
| CA-F5-07 | Next-quarter alert is correctly scheduled after a successful presentation |
| CA-F5-08 | Chat, uploader, resumen, and confirmation modal render with zero console errors in Chrome and Safari |
| CA-F5-09 | `/health` returns 200; first agent response arrives in under 3 seconds |
| CA-F5-10 | At least 2 real (or realistically simulated) autónomos complete a successful presentation with a valid AEAT CSV |

## References

- `docs/api-spec.yml` — endpoint contracts (two documented deviations: OCR path move, `/mensaje` addition)
- `docs/backend-standards.md`, `docs/frontend-standards.md` — stack, mandatory UI/UX rules
- `docs/data-model.md` — `presentacion`, `alerta` tables (both already RLS-enabled, no new tables needed)
- `docs/domain-context.md` — fiscal-term glossary (frontend copy constraint)
- `specs/archive/agente-conversacional/design.md` — `EstadoP04`, graph structure, `confirmar`/`recopilar_datos` interrupts this phase wraps
- `specs/archive/rpa-aeat/design.md` — `presentacion.estado` state machine, the T04-E1 precheck, the deferred `WorkerSettings`/retry this phase completes
- `openspec/config.yaml` — `fiscal_integrity_checks`, `ui_integrity_checks`, dual backend/frontend mandatory steps
