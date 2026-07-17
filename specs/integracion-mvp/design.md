# Design: integracion-mvp

## Folder structure

```
src/
  api/
    main.py                 # FastAPI app, CORS, router mounting (extended)
    dependencies.py         # AuthedRequest, get_authed_request (existing, unchanged)
    routers/
      p04.py                 # extended: 6 new endpoints alongside Phase 1's existing /facturas CRUD
    graph_runtime.py          # NEW: thin helpers wrapping graph.invoke/update_state/Command(resume)
  workers/
    rpa_worker.py             # amended: WorkerSettings, retry policy (SPEC-F5-02)
  fiscal/
    alertas/
      programar_siguiente_trimestre.py  # NEW: CA-F5-07
frontend/                     # NEW — no frontend exists yet
  app/
    (auth)/login/page.tsx
    (auth)/register/page.tsx
    dashboard/page.tsx
    proceso/p04/page.tsx
  components/
    chat/ChatInterface.tsx
    chat/MessageBubble.tsx
    facturas/FacturaUploader.tsx
    facturas/FacturaReviewer.tsx
    resultado/ResumenIVA.tsx
    confirmacion/ConfirmacionModal.tsx
    rpa/RpaStatus.tsx          # NEW: 4-state component, QR display
    ui/                        # shadcn/ui, unmodified
  lib/
    supabase/client.ts
    supabase/server.ts
    api/p04.ts
    types/p04.ts
  e2e/
    happy-path.spec.ts
    ocr-upload.spec.ts
    session-expiry.spec.ts
    aeat-error.spec.ts
    cancel-confirmacion.spec.ts
```

`frontend/` does not exist yet — this change creates it, per `docs/frontend-standards.md`'s already-decided component list.

## SPEC-F5-01 — API endpoints: graph lifecycle mapping

Per the architectural decision in `feature.md`, every endpoint operates on the same LangGraph checkpointed state (`thread_id = proceso_id`). None re-implements fiscal logic (`config.yaml`'s *"No fiscal arithmetic in FastAPI route handlers"* — every handler calls into `src/agent/graph.py` or `src/fiscal/`, never computes itself).

| Endpoint | Method | Graph operation |
|---|---|---|
| `/api/proceso/p04/iniciar` | POST | **See the amendment below — does NOT invoke `recopilar_datos` yet.** Computes `detectar_periodo`/`verificar_duplicado` directly (both pure/near-pure, no LLM call) and seeds the checkpoint via `graph.update_state(config, values, as_node="verificar_duplicado")`. Returns `proceso_id` (=`thread_id`), `ejercicio`, `periodo`, `fecha_limite`. `409` if a `presentacion` row already exists in a non-restartable state for the detected period. |
| `/api/proceso/p04/facturas/ocr` **(moved from `/facturas`, see feature.md gap 2)** | POST | Does not touch the graph. Calls `src.agent.ocr.extraer_factura_ocr` directly (pure Claude Vision call, same function Phase 3's `ocr_factura` node wraps), uploads the file to the `facturas` Storage bucket (`{tipo}/{user_id}/{filename}`, Phase 3's existing RLS-scoped path), returns `OcrResult` per `api-spec.yml`. The frontend's `FacturaReviewer` then sends the reviewed/corrected values to `/mensaje` (below) as a structured payload. |
| `/api/proceso/p04/mensaje/{proceso_id}` **(new — gap-filled)** | POST | The endpoint `docs/api-spec.yml` never defined but `ChatInterface` needs one to send anything. Two payload shapes: `{"tipo": "texto", "contenido": str}` → appends the message to state then `graph.invoke(None, config)` **or** `graph.invoke(Command(resume=...), config)` depending on whether the thread is currently paused at an interrupt (see amendment below — the first real message is what actually triggers `recopilar_datos`, which per the amendment may run all the way to the `confirmar` interrupt in this one call); `{"tipo": "factura_confirmada", "factura": {...}}` → resolves a pending OCR-confirmation interrupt (`Command(resume={"confirmaciones": [...]})`) or, if none pending, `graph.update_state(config, {"facturas_emitidas": [...]})`. Returns the new agent message(s) plus a `pendiente` field (`none` \| `revision_ocr` \| `confirmacion`). |
| `/api/proceso/p04/calcular` | POST | If the checkpointed state already has `resultado_m303`, idempotent — reads and returns it, no recomputation. Otherwise (structured-only path, user never chatted): `graph.update_state(config, {"facturas_emitidas": ..., "facturas_recibidas": ..., "sin_actividad": False})`, appends a synthetic wrap-up user message ("He terminado de introducir mis facturas, calcula mi IVA.") to `mensajes` (see amendment — `recopilar_datos` needs *some* message to act on even when nothing more needs extracting), then `graph.invoke(None, config)` runs `recopilar_datos`→`calcular`→`resumir` in one call, landing at the `confirmar` interrupt. Returns `ResultadoM303`. |
| `/api/proceso/p04/confirmar` | POST | `graph.invoke(Command(resume={"accion": "confirmar", "metodo_pago": ..., "iban": ...}), config)` — resumes the existing `confirmar` interrupt exactly as Phase 3 built it. This sets `confirmado=True`, which triggers `notificar` to upsert `presentacion.estado='confirmado'` (Phase 4's SPEC-F4-00 fix). **After** the graph call returns, this endpoint enqueues the ARQ job: `await arq_pool.enqueue_job("procesar_presentacion", presentacion_id=presentacion_id)` — the enqueueing Phase 4 deferred. Returns `202` with `proceso_id`, `rpa_job_id`. |
| `/api/proceso/p04/estado/{proceso_id}` | GET | Reads `presentacion` **directly from the DB**, not the graph — `presentacion.estado` is the single source of truth for RPA progress from `confirmado` onward (written by Phase 4's `rpa_worker.py`), and polling shouldn't require rehydrating a LangGraph checkpoint. Also computes a `qr_url` field (see SPEC-F5-04) when `estado='presentando'`. |
| `/api/proceso/p04/justificante/{proceso_id}` | GET | Reads `presentacion.justificante_path`, generates a 60-minute signed Supabase Storage URL. `404` if `estado != 'presentado'`. |

### Amendment (found during implementation, Task 10) — there is no runtime "stub AEAT" mode; Phase 4's stubs are pytest-only mocks

**Problem.** Task 9's own wording ("ARQ worker running against the Phase 4 AEAT stubs, never real AEAT") assumed Phase 4's stub fixtures (`tests/rpa/_stubs_aeat.py`) are a runtime mode the RPA worker can be pointed at. They are not — they only exist to mock Playwright's `Page` object inside `tests/rpa/aeat/*.py`'s own unit tests (per the Phase 4 report: "Playwright fully mocked in every test this phase — no real browser session against AEAT was opened"). The real, running `procesar_presentacion`/`ejecutar_presentacion` (`src/workers/rpa_worker.py`) has no stub switch: given a real enqueued job, it launches a real Playwright browser against the real AEAT Sede Electrónica and requires a real Cl@ve Móvil session — exactly the same blocker as `test_autenticar_clave_movil_sesion_real` (Phase 4, still pending manual Product Owner execution). This was surfaced when Claude Code's own safety classifier blocked a live `/confirmar` curl call in Task 9 for exactly this reason.

**Resolution for Task 10's E2E suite.** The Playwright frontend E2E tests never let a real ARQ job reach real AEAT. `happy-path.spec.ts`, `session-expiry.spec.ts`, and `aeat-error.spec.ts` intercept the browser's own `POST /confirmar` network call (Playwright's `page.route()`) and fulfill a mocked `202` response instead of letting it hit the real backend — the real `graph_runtime.confirmar_graph`/ARQ-enqueue path is never exercised by these tests (it's already covered by `tests/api/test_p04_router_f5.py`'s mocked unit tests). The RPA-outcome states (`presentando`→`presentado`, `sesion_expirada`→retry→`presentado`, a non-retryable error→`failed`) are simulated by writing directly to the local Supabase `presentacion` table via the Supabase admin client (service role key, test-only), mirroring exactly what a real `rpa_worker.py` run would have written — this exercises `RpaStatus`'s real Realtime subscription and its 4-state rendering, which is what CA-F5-03/04 actually require, without ever invoking real Playwright-against-AEAT automation.

### Amendment (found during implementation, Task 10) — four frontend bugs surfaced while writing the E2E specs

1. **`RpaStatus.tsx`'s Realtime filter used the wrong identifier.** Same class of bug as the 9.0c fix: `filter: id=eq.${procesoId}` compares `presentacion.id` (a server-generated UUID) against `procesoId` (the thread_id string) — the subscription's server-side filter can never match, so it silently never fired. Fixed: subscribe to `presentacion` UPDATE events unfiltered (RLS already scopes rows to the authenticated user) and re-fetch `/estado` on any event.
2. **The "Ver justificante" link pointed at a nonexistent frontend route** (`/proceso/p04/justificante/{id}` was never built — only the backend API endpoint `/api/proceso/p04/justificante/{proceso_id}` exists). Fixed: fetch the signed URL from that endpoint on click and render a real `<a href>` once resolved.
3. **The P04 page always restarted at the chat phase on mount**, even when a `presentacion` row already existed past `confirmado` — reloading mid-RPA (or after a session-expiry/failure) lost the `RpaStatus` view and dropped the user back into a fresh chat, discovered while writing `aeat-error.spec.ts`'s "process state persists across reload" assertion. Fixed: after `/iniciar`, check `/estado`; if the process is already past `calculado`, resume directly at the `confirmado` phase instead of `chat`.
4. **A Base UI console error on every dashboard render.** `<Button render={<Link/>}>` (fixed in Task 6) triggers `nativeButton` semantics warning logged at `console.error` level — violates CA-F5-08's zero-console-errors bar, caught by Task 10.8's manual Chrome check. Fixed: `nativeButton={false}`.

All four are frontend-only fixes with no backend/API surface change; each is exercised by the E2E specs that found it (1-3) or verified manually (4, since it's a pure DOM/console assertion, not something these specs assert on directly).

### Amendment (found during implementation, Task 9) — `/estado` and `/justificante` queried `presentacion` by the wrong identifier

**Problem.** Both endpoints did `.eq("id", proceso_id)` — but `proceso_id` is the LangGraph `thread_id` (`"{user_id}:P04:{ejercicio}:{periodo}"`, per `construir_thread_id`), while `presentacion.id` is an internal, server-generated UUID the API caller never sees (`docs/data-model.md`: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`). `notificar.py`'s own upsert already establishes the real lookup key: `on_conflict="user_id,proceso,ejercicio,periodo"`. Querying by `id` with a non-UUID string doesn't 404 gracefully — Postgres rejects the value outright (`invalid input syntax for type uuid`), a 500 for every single call, discovered running Task 9's mandatory curl sequence.

**Resolution.** Both endpoints parse `proceso_id` into `user_id`/`ejercicio`/`periodo` (splitting on `:`, matching `construir_thread_id`'s exact format) and query `presentacion` by `.eq("user_id", ...).eq("proceso", "P04").eq("ejercicio", ...).eq("periodo", ...)` instead — the same 4 columns `notificar.py`'s upsert already keys on.

### Amendment (found during implementation, Task 9) — `get_authed_request`'s client never authenticated Storage, only PostgREST

**Problem.** `src/api/dependencies.py::get_authed_request()` calls `client.postgrest.auth(jwt)` but never authenticates `client.storage` — supabase-py's `Client.storage` property snapshots headers from `client.options.headers` (the anon key alone) the first time it's accessed, and mutating it afterward has no effect on real requests (`storage3`'s file API keeps its own `_headers` snapshot). `src/agent/supabase_client.py::crear_cliente_usuario` (Phase 3/4) already solved this correctly by replacing `client._storage` with a freshly built `SyncStorageClient` carrying the JWT — but the API layer's own `get_authed_request` never replicated the fix, since Phase 1-4 never had an endpoint that touched Storage directly through `req.client`. Discovered running Task 9's mandatory curl sequence: `POST /facturas/ocr` 500'd with `storage3.exceptions.StorageApiError: new row violates row-level security policy` — the anon-key-only storage client has no `auth.uid()`, so the `facturas` bucket's INSERT policy rejects every upload. This also silently affected `/estado`'s and `/justificante`'s `create_signed_url` calls (SELECT-policy reads), though those degrade to a null/404 `qr_url`/`justificante_url` rather than a loud 500, making them easy to miss without deliberately re-testing storage-touching endpoints.

**Resolution.** `get_authed_request` now applies the exact same fix as `crear_cliente_usuario`: after `client.postgrest.auth(jwt)`, replace `client._storage` with a `SyncStorageClient` built with `Authorization: Bearer {jwt}` merged into its headers.

### Amendment (found during implementation, Task 9) — `/health`'s `redis` field was a stale hardcoded stub

**Problem.** `src/api/routers/health.py` (Phase 1) hardcodes `"redis": "not_configured"` with a comment noting "ARQ workers not wired yet this phase" — true when written, but this phase (Task 3) wires `WorkerSettings` and Task 2 adds the enqueueing endpoint. Discovered running Task 9's mandatory `curl http://localhost:8000/health` check, which per `docs/openspec-tasks-mandatory-steps.md` expects `{"status": "ok", "db": "ok", "redis": "ok"}` — the stub made that assertion permanently false regardless of Redis's actual state.

**Resolution.** `/health` now pings Redis for real (`redis.from_url(os.environ["REDIS_URL"]).ping()`), returning `"ok"`/`"error"` like the existing `db` check, instead of a hardcoded string.

### Amendment (found during implementation, Task 6) — `/calcular`'s response never included `fecha_limite`

**Problem.** `calcular_graph` (`src/api/graph_runtime.py`) returns `estado["resultado_m303"]` verbatim — the fiscal engine's own `ResultadoM303` model (`src/fiscal/`), which has no concept of a filing deadline (that's a graph/domain concern set by `detectar_periodo`, not something `calcular_m303` computes). But `docs/api-spec.yml`'s `ResultadoM303` response schema and this phase's own `ResumenIVA`/`ConfirmacionModal` components (SPEC-F5-05, discovered via this task's mandatory manual browser verification) require `fecha_limite` to render the due date. The field was silently absent from every real `/calcular` response, leaving the due date blank in both components.

**Resolution.** `calcular_graph` merges `estado["fecha_limite_presentacion"]` into the returned dict as `fecha_limite` before returning, for both the idempotent-read branch and the freshly-computed branch — this is integration-layer merging of two already-computed state values, not fiscal arithmetic, so it stays in `graph_runtime.py` rather than `src/fiscal/`.

### Amendment (found during implementation, Task 6) — CORS was never configured

**Problem.** `src/api/main.py` never registers `CORSMiddleware`. This phase's own frontend (`http://localhost:3000`) calls the FastAPI backend (`http://localhost:8000`) cross-origin — every browser-issued request to `/api/proceso/p04/*` is preceded by a CORS preflight (`OPTIONS`), and with no CORS middleware registered FastAPI has no route matching `OPTIONS`, so it returns `405 Method Not Allowed` and the browser blocks the real request before it's ever sent. This was discovered manually testing `ChatInterface`/`iniciarProceso()` against the local stack (per this task's mandatory 375px browser verification), not by a unit or E2E test — none of the existing tests exercise a real browser-to-server cross-origin call.

**Resolution.** Add `CORSMiddleware` to `src/api/main.py`, allowing the frontend origin(s) from `NEXT_PUBLIC_API_URL`'s counterpart — `http://localhost:3000` for local dev (the only origin this MVP serves; no deployed frontend origin exists yet per the deployment note below). Allow `GET`/`POST` and the `Authorization`/`Content-Type` headers the frontend actually sends (`lib/api/p04.ts`).

**Duplicate-declaration `409` at `/iniciar`.** `verificar_duplicado` already sets `presentacion_duplicada`/`csv_presentacion_previa` in state and Phase 3's prompt discloses it conversationally — but CA-F5 treats "already presented" as a hard stop for a *new* process, not a conversational nicety. This endpoint checks the same condition before returning and responds `409` (`docs/api-spec.yml`'s `Error` schema, `error="PRESENTACION_DUPLICADA"`) rather than silently proceeding into a graph that would only disclose it mid-chat.

### Amendment (found during implementation, Task 1) — the graph has no "wait for the first message" pause point

**Problem.** `_ruta_tras_recopilar_datos` (`src/agent/graph.py`) unconditionally routes to `"calcular"` unless `facturas_pendientes_ocr` is set — there is no conditional routing back to `recopilar_datos` for "the user might still be describing more invoices." Combined with `recopilar_datos` itself only ever pausing via `interrupt()` when `facturas_baja_confianza` has pending entries (never simply "no message to process yet"), this means: **a single `graph.invoke()` that reaches `recopilar_datos` with a non-empty `mensajes` list runs straight through to the `confirmar` interrupt in that one call** — there is no native multi-turn "describe invoice 1, then invoice 2, then say done" loop over separate HTTP requests. This is exactly how Phase 3's own `test_flujo_completo_perfil_1_token_budget` is written (one user message, `facturas_emitidas` already pre-seeded in the initial state, first `invoke()` reaches `"__interrupt__"` directly) — not an oversight discovered now, but a real behavioral constraint this phase must design around rather than silently assume away.

A direct consequence: **`recopilar_datos` cannot be called with an empty `mensajes` list** — the Anthropic Messages API rejects an empty `messages` array. `/iniciar`'s original design (invoke the graph immediately, let it interrupt with `mensajes` still empty) is not just suboptimal, it would 400 on the very first real conversation.

**Resolution:**
1. `/iniciar` does not invoke the graph node-by-node at all. It calls `detectar_periodo`/`verificar_duplicado` as plain Python functions (both already pure/near-pure, independently unit-tested since Phase 3) and seeds the checkpoint with their combined output via `graph.update_state(config, values, as_node="verificar_duplicado")` — LangGraph records this as if `verificar_duplicado` just ran, so the *next* real `invoke()` correctly resumes at `recopilar_datos`. No LLM call happens at `/iniciar` time.
2. The user's first real message, sent via `/mensaje`, is what actually triggers `recopilar_datos` for the first time — and per the constraint above, that single call may run all the way to the `confirmar` interrupt (extracting whatever invoices the message described, then immediately calculating and summarizing). The frontend must be able to render `ResumenIVA`/`ConfirmacionModal` as a direct response to *any* `/mensaje` call, not only after some separate "I'm done" signal.
3. For the structured-only path (`FacturaUploader`/`FacturaReviewer`, no chat), `/calcular` appends a synthetic system-authored user message ("He terminado de introducir mis facturas, calcula mi IVA.") before invoking — `recopilar_datos`'s LLM call needs *something* to process even when `facturas_emitidas`/`facturas_recibidas` were already populated via `update_state` and there's nothing left to extract. The system prompt (unchanged from Phase 3) already handles a message that describes no new invoices correctly — this is not a new prompt-engineering task, just supplying a valid non-empty turn.
4. **Consequence for multi-invoice chat descriptions:** if a user describes invoices one at a time in separate chat messages *and* expects the agent to keep asking "anything else?" before calculating, that loop does not exist yet — each `/mensaje` call reaching `recopilar_datos` proceeds straight to `calcular` once it returns. This is a real, load-bearing UX gap, not something this change silently papers over: it's flagged here as a **known limitation carried over from Phase 3's own architecture**, out of scope to fix in this change (fixing it means adding a genuine "more invoices?" routing/interrupt to `src/agent/graph.py`, a Phase 3 architectural change, not an F5 integration task). The MVP's primary invoice-entry path is `FacturaUploader` (structured, one invoice at a time, no premature calculation); free-text chat is best suited to describing *all* invoices in one message or relying on `sin_actividad`, matching exactly how Phase 3's own tests already exercise it.

## SPEC-F5-02 — ARQ `WorkerSettings` and retry policy

Phase 4 built `ejecutar_presentacion`/`procesar_presentacion` as correct, idempotent, callable functions but explicitly deferred queue registration. This phase adds:

```python
# src/workers/rpa_worker.py (amended)
class WorkerSettings:
    functions = [procesar_presentacion]
    max_tries = 3
    retry_delay = 60  # seconds between attempts
```

**Correction (found while implementing):** `arq.worker.Worker` has no `on_job_failed` hook — the sketch above in an earlier draft of this spec referenced one that doesn't exist in ARQ's real API. ARQ's actual retry mechanism is simpler and cruder: **any exception a job function raises triggers an automatic retry** (up to `max_tries`) — there's no built-in way to retry conditionally. Selective retry-only-for-`sesion_expirada` has to be implemented *inside* `procesar_presentacion` itself: catch the exception from `ejecutar_presentacion`, inspect its `codigo_error`, and only **re-raise** (letting ARQ's automatic retry fire) when it's `sesion_expirada` — every other `codigo_error` is caught and swallowed (the job "succeeds" from ARQ's point of view; `presentacion.estado='error'` is already durably written by `ejecutar_presentacion`'s own except-block, so nothing is lost by not retrying). A fresh retried call to `ejecutar_presentacion` re-authenticates from scratch via a new QR, per Phase 4's own idempotency guard — no data is re-entered, since `resultado_m303`/`perfil`/etc. are re-read from the same `presentacion_id`. This satisfies CA-F5-03 exactly ("agent requests a fresh PIN/QR and completes the presentation without losing any data") without inventing retry semantics ARQ doesn't actually support.

## SPEC-F5-03 — Next-quarter alert scheduling (CA-F5-07)

`src/fiscal/alertas/programar_siguiente_trimestre.py::programar_alerta_siguiente_trimestre(client, user_id, ejercicio, periodo) -> None` — pure date arithmetic (next quarter's `fecha_limite`, minus 15 days for `fecha_alerta`, per the domain-context deadline table), inserts one `alerta` row (`tipo='vencimiento_m303'`). Called by the ARQ worker immediately after `ejecutar_presentacion` returns `estado='presentado'` (in `procesar_presentacion`, after the underlying call succeeds) — not inside Phase 4's own `rpa_worker.py` functions, since alert scheduling is an F5-owned orchestration concern layered on top of F4's filing logic, not a fiscal or RPA concept itself.

## SPEC-F5-04 — Supabase Realtime + QR display

**Realtime.** `ALTER PUBLICATION supabase_realtime ADD TABLE presentacion;` (migration). The frontend subscribes to `postgres_changes` on `presentacion` filtered by `id=eq.{proceso_id}` — RLS applies to Realtime subscriptions the same as to queries, so cross-user leakage is structurally impossible, not just filtered client-side.

**QR display.** Phase 4's `guardar_qr_clave()` writes to a fully deterministic path: `qr-clave/{user_id}/{ejercicio}_{periodo}.png` — no new `presentacion` column is needed. `/estado` computes `qr_url` by attempting a signed URL for that exact path whenever `estado='presentando'`; if the file doesn't exist yet (QR not generated yet this attempt) or the signed-URL call 404s, `qr_url` is `null` and the frontend shows a "esperando código QR" placeholder instead. A retry (SPEC-F5-02) overwrites the same path with a fresh QR — the frontend's existing Realtime subscription on `presentacion` doesn't fire for a Storage write, so `RpaStatus` polls `/estado` every 5s specifically while `estado='presentando'` to pick up a refreshed `qr_url` (Realtime handles the `estado` transitions themselves; this narrow poll only exists to refresh the QR image mid-`presentando`).

## SPEC-F5-05 — Frontend components

Per `docs/frontend-standards.md`'s already-decided structure and `openspec/config.yaml`'s `ui_integrity_checks`:

- **`ChatInterface`** — renders `mensajes` from the current graph state (fetched via `/estado` or returned by `/mensaje`), a text input wired to `POST /mensaje`, and conditionally mounts `FacturaReviewer`/`ConfirmacionModal` inline when the response's `pendiente` field says so.
- **`FacturaUploader`** — drag-and-drop, calls `POST /facturas/ocr`, shows a loading skeleton during OCR (`docs/frontend-standards.md` "loading states always handled").
- **`FacturaReviewer`** — editable table of OCR-extracted fields. **Every field with `confidence < 0.8` renders amber and blocks the "continuar" action until the user explicitly edits or confirms it** (`ui_integrity_checks`, CA-F3-03's original contract) — this is a hard client-side gate, not just a visual hint, mirroring Phase 3's own server-side `facturas_baja_confianza` interrupt (defense in depth: even if a client bug let a low-confidence value through, `recopilar_datos`'s interrupt loop still catches it server-side).
- **`ResumenIVA`** — renders `resumir` node's structured fields in plain language ("IVA que has cobrado a tus clientes", never "Casilla 27"; raw casillas as secondary/collapsed detail). Every euro amount paired with its period (`ui_integrity_checks`).
- **`ConfirmacionModal`** — shows período, ejercicio, total a ingresar/compensar, IBAN (last 4 digits only), due date. **The confirm button requires a deliberate click; there is no auto-advance, no default-focused submit-on-Enter.** Calls `POST /confirmar` only on that click. Logs `timestamp`+`user_id` client-side for the E2E test to assert against, mirroring the server-side write.
- **`RpaStatus`** — the 4-state component `ui_integrity_checks` requires:

  | State | Condition | UI |
  |---|---|---|
  | `waiting` | `estado ∈ {confirmado, presentando}` and `error_code` is null | Progress indicator + QR panel (SPEC-F5-04) if `presentando` |
  | `needs-re-auth` | `estado='error'` and `error_code='sesion_expirada'` **and an automatic retry is in flight** (ARQ hasn't exhausted `max_tries`) | "Tu sesión ha caducado, generando un nuevo código QR..." — same QR panel, refreshed |
  | `failed` | `estado='error'` and (`error_code != 'sesion_expirada'` or retries exhausted) | `error_detail` (Phase 4's HIGH-2 fix makes this human-readable) + a manual "reintentar" action |
  | `done` | `estado='presentado'` | Link to `/justificante/{proceso_id}`, CSV shown |

  All 4 states are driven by `presentacion.estado`+`error_code` via the same Realtime subscription — no separate polling loop except the narrow QR-refresh poll in SPEC-F5-04.

## SPEC-F5-06 — Context management (D11)

**Amendment on the original D11 wording.** The PDR (`docs/Autonomos.io/0. REQUERIMIENTOS/PDR.md`, decision D11) conditions *building* this feature on production data showing an average session length over 15-20 turns — "sin ese dato real, la implementación sería prematura." No production data exists yet (there are no real users). This change builds the mechanism anyway, per explicit instruction, using the stated threshold as a **per-session runtime trigger** rather than the fleet-average decision gate D11 originally described — a deliberate reinterpretation, not an oversight, since there's no fleet average to measure yet.

**Implementation.** Rolling window only (the simpler of D11's two options, no extra LLM call/cost) — periodic summarization stays a documented, unbuilt V2 fallback. Inside `recopilar_datos`, before the Claude Sonnet 5 call: if `len(estado["mensajes"]) > 15`, keep the first message (often the sin_actividad/duplicate-disclosure context) plus the most recent 14, dropping the middle. This is a pure state transform, no new node, no new interrupt — it does not change `recopilar_datos`'s existing interrupt-loop-then-LLM-call structure (SPEC-F3-06 in the archived F3 design), only what's sent as conversation history.

## Deployment note (explicitly flagged, not covered by this change)

The functional spec's own F5 section (`docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §7.2) lists `SPEC-F5-05: Especificación del despliegue` (Dockerfile, docker-compose.yml, rollback procedure) as a spec to complete before coding this phase. This change does not include it — CA-F5-09 ("`/health` responds correctly on the deployed server") is verified against local `uvicorn`/`npm run dev`, not a real deployment. Flagging this now rather than silently treating F5 as fully done: a deployment-focused follow-up change is needed before `docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §8's "Definición de Hecho" bar (*"Existe un procedimiento de despliegue documentado y probado... en menos de 2 horas"*) can be met.

## Fiscal / UI integrity checks applicable this phase (from `openspec/config.yaml`)

- *"No fiscal arithmetic in FastAPI route handlers"* — every new endpoint calls `src/agent/graph.py` or `src/fiscal/`; `/calcular`'s handler never computes a euro amount itself, only orchestrates the graph call.
- *"LangGraph interrupt node present in every graph that leads to AEAT submission"* — unchanged, satisfied by Phase 3's `confirmar` node; this phase only wraps it in HTTP, never bypasses it (the structured `/calcular` fast-path still lands at the same `confirmar` interrupt before anything reaches Phase 4's RPA).
- *"RLS enabled on every new Supabase table"* — no new tables this phase (`presentacion`/`alerta` both pre-existing, RLS already enabled); Realtime publication inherits the same RLS.
- *"ConfirmacionModal confirm button requires deliberate click"*, *"OCR fields < 0.8 block progress"*, *"4 RPA states"*, *"fiscal terms from the glossary only"*, *"every euro amount paired with its period"*, *"375px minimum width"* — all addressed in SPEC-F5-05 above, verified by the Playwright E2E suite (`tasks.md` frontend mandatory steps).
