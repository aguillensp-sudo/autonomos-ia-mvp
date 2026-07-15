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
| `/api/proceso/p04/iniciar` | POST | `graph.invoke(estado_inicial, config={"configurable": {"thread_id": thread_id}})` — first invocation. Runs `detectar_periodo` → `verificar_duplicado` → `recopilar_datos` (interrupts immediately, `mensajes` still empty). Returns `proceso_id` (=`thread_id`), `ejercicio`, `periodo`, `fecha_limite` read off the interrupted state, plus the first agent message if `verificar_duplicado` set `presentacion_duplicada=True` (disclosed per Phase 3's system prompt). `409` if a `presentacion` row already exists in a non-restartable state for the detected period (mirrors `verificar_duplicado`'s own check — the endpoint surfaces it as an HTTP error before even reaching the interrupt, since CA-F5 requires the duplicate check to block, not silently continue). |
| `/api/proceso/p04/facturas/ocr` **(moved from `/facturas`, see feature.md gap 2)** | POST | Does not touch the graph. Calls `src.agent.ocr.extraer_factura_ocr` directly (pure Claude Vision call, same function Phase 3's `ocr_factura` node wraps), uploads the file to the `facturas` Storage bucket (`{tipo}/{user_id}/{filename}`, Phase 3's existing RLS-scoped path), returns `OcrResult` per `api-spec.yml`. The frontend's `FacturaReviewer` then sends the reviewed/corrected values to `/mensaje` (below) as a structured payload. |
| `/api/proceso/p04/mensaje/{proceso_id}` **(new — gap-filled)** | POST | The endpoint `docs/api-spec.yml` never defined but `ChatInterface` needs one to send anything. Two payload shapes: `{"tipo": "texto", "contenido": str}` → `graph.invoke(Command(resume={"mensaje": contenido}), config)` (free-text chat turn); `{"tipo": "factura_confirmada", "factura": {...}}` → resolves a pending OCR-confirmation interrupt or, if none pending, `graph.update_state(config, {"facturas_emitidas": [...]})` to append a reviewed invoice without a chat turn. Returns the new agent message(s) plus a `pendiente` field describing the current interrupt (`none` \| `revision_ocr` \| `confirmacion`) so the frontend knows which structured component to render next. |
| `/api/proceso/p04/calcular` | POST | If the graph's checkpointed state already has `resultado_m303` (chat path already reached `calcular`+`resumir`), this is idempotent — reads and returns the existing result, no recomputation. If the request body carries `facturas_emitidas`/`facturas_recibidas` arrays (structured-only path, user never used chat), `graph.update_state(config, {"facturas_emitidas": ..., "facturas_recibidas": ..., "sin_actividad": False})` merges them in, then `graph.invoke(None, config)` continues the graph forward through `calcular` → `resumir`, landing at the `confirmar` interrupt. Returns `ResultadoM303`. |
| `/api/proceso/p04/confirmar` | POST | `graph.invoke(Command(resume={"accion": "confirmar", "metodo_pago": ..., "iban": ...}), config)` — resumes the existing `confirmar` interrupt exactly as Phase 3 built it. This sets `confirmado=True`, which triggers `notificar` to upsert `presentacion.estado='confirmado'` (Phase 4's SPEC-F4-00 fix). **After** the graph call returns, this endpoint enqueues the ARQ job: `await arq_pool.enqueue_job("procesar_presentacion", presentacion_id=presentacion_id)` — the enqueueing Phase 4 deferred. Returns `202` with `proceso_id`, `rpa_job_id`. |
| `/api/proceso/p04/estado/{proceso_id}` | GET | Reads `presentacion` **directly from the DB**, not the graph — `presentacion.estado` is the single source of truth for RPA progress from `confirmado` onward (written by Phase 4's `rpa_worker.py`), and polling shouldn't require rehydrating a LangGraph checkpoint. Also computes a `qr_url` field (see SPEC-F5-04) when `estado='presentando'`. |
| `/api/proceso/p04/justificante/{proceso_id}` | GET | Reads `presentacion.justificante_path`, generates a 60-minute signed Supabase Storage URL. `404` if `estado != 'presentado'`. |

**Duplicate-declaration `409` at `/iniciar`.** `verificar_duplicado` already sets `presentacion_duplicada`/`csv_presentacion_previa` in state and Phase 3's prompt discloses it conversationally — but CA-F5 treats "already presented" as a hard stop for a *new* process, not a conversational nicety. This endpoint checks the same condition before returning and responds `409` (`docs/api-spec.yml`'s `Error` schema, `error="PRESENTACION_DUPLICADA"`) rather than silently proceeding into a graph that would only disclose it mid-chat.

## SPEC-F5-02 — ARQ `WorkerSettings` and retry policy

Phase 4 built `ejecutar_presentacion`/`procesar_presentacion` as correct, idempotent, callable functions but explicitly deferred queue registration. This phase adds:

```python
# src/workers/rpa_worker.py (amended)
class WorkerSettings:
    functions = [procesar_presentacion]
    max_tries = 3
    retry_delay = 60  # seconds between attempts

    @staticmethod
    async def on_job_failed(ctx, job_id: str) -> None:
        """Only re-enqueue if the failure was error_code='sesion_expirada'
        (CA-F5-03) — every other error_code is terminal, surfaced to the
        user via presentacion.estado='error', no automatic retry."""
```

Retry logic reads the just-written `presentacion.error_code` after a failed attempt: `sesion_expirada` → ARQ retries (a fresh call to `ejecutar_presentacion` re-authenticates from scratch via a new QR, per Phase 4's own idempotency guard — no data is re-entered, since `resultado_m303`/`perfil`/etc. are re-read from the same `presentacion_id`); anything else → `on_job_failed` is a no-op, the row stays `estado='error'` for the user to see via `/estado` or Realtime. This satisfies CA-F5-03 exactly ("agent requests a fresh PIN/QR and completes the presentation without losing any data") without inventing new retry semantics beyond what Phase 4's idempotency guard already supports.

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
