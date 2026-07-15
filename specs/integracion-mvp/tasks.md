# Tasks: integracion-mvp

`openspec/config.yaml` read: yes. `docs/openspec-tasks-mandatory-steps.md` read: yes. Branch naming: `feature/integracion-mvp`. Agents: `backend_developer` for Tasks 1-4/7-9, `frontend_developer` for Tasks 5-6/10-11 (both `claude-sonnet-4-6` per `openspec/config.yaml`).

**This is the first phase touching both backend and frontend mandatory steps** — `openspec/config.yaml` defines separate mandatory-step lists for each; both apply here (curl testing for the API, Playwright E2E for the frontend), not just one.

**Blocking prerequisite:** several tasks below make real Claude Sonnet 5 calls (via the existing graph) and require `ANTHROPIC_API_KEY`/`LANGSMITH_API_KEY` (mandatory since Phase 3). Frontend E2E tests additionally require a running `uvicorn` backend and `npm run dev` frontend simultaneously, plus local Supabase + Redis (for the ARQ worker). If any of these can't be started, the agent must stop and report the blocker explicitly rather than mark a step `[x]` unexecuted.

**No real AEAT/Cl@ve Móvil session in any automated test** — Phase 4's precedent (Playwright fully mocked, one `@pytest.mark.integration` test requiring manual execution) continues here: this phase's E2E tests exercise the API + frontend + ARQ wiring using Phase 4's existing AEAT stubs (`tests/rpa/_stubs_aeat.py`) and a mocked Playwright `page`, never a real browser session against AEAT.

## 0. Setup: Create Feature Branch (MANDATORY — FIRST STEP)

- [x] 0.1 Create feature branch `feature/integracion-mvp` from `main`
- [x] 0.2 Verify branch creation: `git branch --show-current`

## 1. Backend: `graph_runtime.py` — thin LangGraph HTTP wrapper (SPEC-F5-01 prerequisite)

Acceptance criteria: prerequisite for all endpoint tasks below — no endpoint calls `graph.invoke()`/`Command`/`update_state` directly, all go through this module so the graph-lifecycle logic is unit-testable independent of FastAPI.

### 1.0 — Prerequisite (found during implementation): `/iniciar` cannot invoke `recopilar_datos` with empty `mensajes`

Per `design.md`'s amendment: the graph has no native pause point between `verificar_duplicado` and `recopilar_datos`'s first LLM call, and that call requires a non-empty `mensajes` list (the Anthropic API rejects an empty array). `iniciar_graph` must seed the checkpoint via `detectar_periodo`/`verificar_duplicado` called as plain functions + `graph.update_state(..., as_node="verificar_duplicado")`, never a graph `invoke()` that would reach `recopilar_datos` with nothing to process.

- [x] 1.0.1 Design amendment written (this session) — see `design.md`'s "Amendment (found during implementation, Task 1)"

- [ ] 1.1 Write failing test `test_iniciar_graph_siembra_checkpoint_sin_invocar_recopilar_datos` (mocked checkpointer/graph): `iniciar_graph(user_id, user_jwt) -> dict` returns `thread_id`, `ejercicio`, `periodo`, `fecha_limite`; asserts `graph.update_state` was called with `as_node="verificar_duplicado"` and that no Anthropic client call occurred (proving `recopilar_datos` never ran)
- [ ] 1.2 Write failing test `test_iniciar_graph_detecta_presentacion_duplicada`: given an existing `presentacion` row in `estado='presentado'` for the detected period, `iniciar_graph` raises `PresentacionDuplicadaError` (mapped to `409` at the router layer)
- [ ] 1.3 Write failing test `test_enviar_mensaje_primer_turno_avanza_hasta_confirmar` (mocked graph/Anthropic client returning a tool-call + text response): the first `/mensaje` call on a freshly-seeded thread invokes the graph with the user's message appended, and can return a `pendiente="confirmacion"` result in that single call — proving the endpoint doesn't assume a separate "done adding invoices" turn exists
- [ ] 1.4 Write failing test `test_enviar_mensaje_resume_con_texto_libre_cuando_pausado`: when the thread IS currently paused at an interrupt (e.g. `confirmacion_baja_confianza`), a `{"tipo": "texto", ...}` message resumes via `Command(resume=...)` rather than a fresh `invoke(None, ...)`
- [ ] 1.5 Write failing test `test_enviar_mensaje_factura_confirmada_actualiza_estado`: a `{"tipo": "factura_confirmada", "factura": {...}}` payload results in `graph.update_state` being called with the reviewed invoice appended to `facturas_emitidas`/`facturas_recibidas`, not a chat turn
- [ ] 1.6 Write failing test `test_calcular_graph_idempotente_si_ya_calculado`: if the checkpointed state already has `resultado_m303`, `calcular_graph(thread_id, facturas=None)` returns it without re-invoking `calcular`/`resumir`
- [ ] 1.7 Write failing test `test_calcular_graph_estructurado_fusiona_facturas_y_agrega_mensaje_sintetico`: given `facturas_emitidas`/`facturas_recibidas` arrays and no prior `resultado_m303`, `calcular_graph` merges them via `update_state`, appends the synthetic wrap-up user message, then invokes forward through `recopilar_datos`→`calcular`→`resumir`, landing at the `confirmar` interrupt
- [ ] 1.8 Write failing test `test_confirmar_graph_resume_interrupt_y_devuelve_confirmado`: `confirmar_graph(thread_id, metodo_pago, iban)` resumes the `confirmar` interrupt and returns `confirmado=True`
- [ ] 1.9 Verify tests fail: `pytest tests/api/test_graph_runtime.py -v -m "not integration"`
- [ ] 1.10 Implement `src/api/graph_runtime.py` (`iniciar_graph`, `enviar_mensaje`, `calcular_graph`, `confirmar_graph`, `PresentacionDuplicadaError`) per `design.md` SPEC-F5-01 and its amendment, using `src.agent.checkpointer`/`src.agent.graph.construir_grafo` (Phase 3, unchanged — this module wraps it, never modifies it)
- [ ] 1.11 Run unit tests (mocked graph/checkpointer) — must pass: `pytest tests/api/test_graph_runtime.py -v -m "not integration" --cov=src.api.graph_runtime --cov-branch --cov-report=term-missing`
- [ ] 1.12 Write and run `@pytest.mark.integration` test(s) against the REAL graph + real Postgres checkpointer + real Claude Sonnet 5 (mirroring Phase 3's own `test_flujo_completo_perfil_1_token_budget` pattern) proving `iniciar_graph` → `enviar_mensaje` → `calcular_graph`/`confirmar_graph` actually work end-to-end against the live graph, not just mocks — per this task's CRITICAL instruction, these are the ONLY tests in this module allowed to touch a real Anthropic client, and they must be marked so `pytest -m "not integration"` (the default TDD cycle) never runs them

## 2. Backend: API Endpoints (SPEC-F5-01)

Acceptance criteria: CA-F5-01, CA-F5-02, CA-F5-05

- [ ] 2.1 Write failing test `test_post_iniciar_devuelve_proceso_id_y_periodo` (FastAPI `TestClient`, mocked graph_runtime): `POST /api/proceso/p04/iniciar` returns `200` with `proceso_id`/`ejercicio`/`periodo`/`fecha_limite`
- [ ] 2.2 Write failing test `test_post_iniciar_presentacion_duplicada_devuelve_409`: `PresentacionDuplicadaError` maps to `409` with the `Error` schema (`error="PRESENTACION_DUPLICADA"`)
- [ ] 2.3 Write failing test `test_post_facturas_ocr_devuelve_ocr_result`: `POST /api/proceso/p04/facturas/ocr` (multipart) calls `extraer_factura_ocr`, returns `OcrResult` shape; **regression guard**: the existing Phase-1 `POST /api/proceso/p04/facturas` (JSON body) is untouched and still passes its own existing tests
- [ ] 2.4 Write failing test `test_post_mensaje_texto_libre_y_factura_confirmada`: both payload shapes route correctly through `enviar_mensaje`
- [ ] 2.5 Write failing test `test_post_calcular_devuelve_resultado_m303`: both the idempotent and the structured-merge paths return `200` with the `ResultadoM303` shape
- [ ] 2.6 Write failing test `test_post_confirmar_enqueues_arq_job` (mocked ARQ pool): `POST /api/proceso/p04/confirmar` returns `202` with `rpa_job_id`, and `arq_pool.enqueue_job` is called with `procesar_presentacion`/the correct `presentacion_id` **only after** `confirmar_graph` returns `confirmado=True`
- [ ] 2.7 Write failing test `test_post_confirmar_no_enqueues_si_grafo_no_confirma`: if `confirmar_graph` returns `confirmado=False` (user said "revisar"/"cancelar"), no ARQ job is enqueued — regression guard for the critical negative path
- [ ] 2.8 Write failing test `test_get_estado_lee_presentacion_directo_de_bd`: `GET /api/proceso/p04/estado/{proceso_id}` reads `presentacion` (mocked Supabase client), returns `ProcesoEstado` shape including `qr_url` when `estado='presentando'`
- [ ] 2.9 Write failing test `test_get_estado_qr_url_null_si_archivo_no_existe`: a missing/expired QR file at the deterministic path results in `qr_url: null`, not a 500
- [ ] 2.10 Write failing test `test_get_justificante_devuelve_url_firmada`: `GET /api/proceso/p04/justificante/{proceso_id}` returns a signed URL only when `estado='presentado'`, `404` otherwise
- [ ] 2.11 Write failing test `test_endpoints_requieren_jwt`: every new endpoint returns `401`/`403` without a valid `Authorization: Bearer` header (regression guard for the existing `AuthedRequest` dependency)
- [ ] 2.12 Verify tests fail: `pytest tests/api/test_p04_router_f5.py -v`
- [ ] 2.13 Implement all 6 endpoints in `src/api/routers/p04.py`, calling only `graph_runtime.py` (Task 1) and Supabase — no fiscal arithmetic in the handlers themselves (`fiscal_integrity_checks`)
- [ ] 2.14 Run tests — must pass: `pytest tests/api/ -v --cov=src.api --cov-branch --cov-report=term-missing`

## 3. Backend: ARQ `WorkerSettings` + Retry Policy (SPEC-F5-02)

Acceptance criteria: CA-F5-03

- [ ] 3.1 Write failing test `test_worker_settings_registra_procesar_presentacion`: `WorkerSettings.functions` includes `procesar_presentacion`, `max_tries=3`
- [ ] 3.2 Write failing test `test_on_job_failed_reintenta_si_sesion_expirada` (mocked ARQ job context + a `presentacion` row with `error_code='sesion_expirada'`): `on_job_failed` triggers a retry (asserted via the mocked ARQ re-enqueue call, or via ARQ's own retry return contract — whichever the implementation uses)
- [ ] 3.3 Write failing test `test_on_job_failed_no_reintenta_si_error_code_distinto`: any other `error_code` (e.g. `'discrepancia_resultado'`, `'nrc_invalido'`) results in no retry — regression guard, a fiscal discrepancy must never be silently retried
- [ ] 3.4 Write failing test `test_reintento_sesion_expirada_no_pierde_datos_ya_ingresados`: simulates one failed attempt (`sesion_expirada`) followed by a successful retry using the *same* `presentacion_id`/`resultado_m303` — asserts the final `presentacion` row's `total_devengado`/`total_deducible`/`csv_aeat` match the original calculation, proving no data was lost or re-entered (CA-F5-03's exact wording)
- [ ] 3.5 Verify tests fail: `pytest tests/workers/test_worker_settings.py -v`
- [ ] 3.6 Implement `WorkerSettings` in `src/workers/rpa_worker.py` per `design.md` SPEC-F5-02
- [ ] 3.7 Run tests — must pass: `pytest tests/workers/ -v --cov=src.workers --cov-branch --cov-report=term-missing` (must remain 100%)

## 4. Backend: Next-Quarter Alert Scheduling + Realtime/QR (SPEC-F5-03, SPEC-F5-04)

Acceptance criteria: CA-F5-07

- [ ] 4.1 Write failing test `test_programar_alerta_siguiente_trimestre_1t_a_2t`: presenting 1T 2026 schedules an `alerta` row for 2T 2026 with the correct `fecha_limite`/`fecha_alerta` (per `docs/domain-context.md`'s deadline table)
- [ ] 4.2 Write failing test `test_programar_alerta_siguiente_trimestre_4t_a_1t_ano_siguiente`: 4T→1T crosses a calendar year correctly
- [ ] 4.3 Write failing test `test_procesar_presentacion_llama_programar_alerta_tras_exito`: `procesar_presentacion`, on `estado='presentado'`, calls `programar_alerta_siguiente_trimestre` exactly once; a failed presentation does not schedule an alert
- [ ] 4.4 Verify tests fail: `pytest tests/fiscal/alertas/ tests/workers/ -k "alerta" -v`
- [ ] 4.5 Implement `src/fiscal/alertas/programar_siguiente_trimestre.py` and wire the call into `procesar_presentacion`
- [ ] 4.6 Write the Realtime migration: `ALTER PUBLICATION supabase_realtime ADD TABLE presentacion;` (`src/db/migrations/<timestamp>_presentacion_realtime.sql`, mirrored into `supabase/migrations/`)
- [ ] 4.7 Apply the migration against local Supabase; confirm via `supabase db diff`/direct query that `presentacion` is in the publication
- [ ] 4.8 Run tests — must pass: `pytest tests/fiscal/alertas/ tests/workers/ -v --cov=src.fiscal --cov=src.workers --cov-branch --cov-report=term-missing` (must remain 100%)

## 5. Frontend: Project Scaffold + API Client (prerequisite for Tasks 6-7)

Acceptance criteria: prerequisite — no CA directly

- [ ] 5.1 Scaffold `frontend/` (Next.js 15, App Router, TypeScript strict, Tailwind, shadcn/ui) per `docs/frontend-standards.md`'s folder structure
- [ ] 5.2 Implement `lib/supabase/client.ts`, `lib/supabase/server.ts` (per `@supabase/auth-helpers-nextjs`), `lib/types/p04.ts` (typed to match the Pydantic models exactly — `docs/frontend-standards.md`'s TypeScript conventions)
- [ ] 5.3 Implement `lib/api/p04.ts` — typed fetch wrappers for all 7 endpoints (Phase 1's existing `/facturas` CRUD + this phase's 6)
- [ ] 5.4 `(auth)/login`, `(auth)/register`, `dashboard/page.tsx` — minimal, Supabase Auth only, no custom UI beyond shadcn defaults (out of scope: any dashboard beyond the entry point, per the PDR's V2 deferral)

## 6. Frontend: P04 Flow Components (SPEC-F5-05)

Acceptance criteria: CA-F5-08, `ui_integrity_checks`

- [ ] 6.1 `ChatInterface.tsx` + `MessageBubble.tsx` — renders `mensajes`, text input → `POST /mensaje`, conditionally mounts `FacturaReviewer`/`ConfirmacionModal` per the response's `pendiente` field
- [ ] 6.2 `FacturaUploader.tsx` — drag-and-drop → `POST /facturas/ocr`, loading skeleton during OCR
- [ ] 6.3 `FacturaReviewer.tsx` — editable OCR field table; **fields with `confidence < 0.8` render amber and block the continue action until edited/confirmed** (client-side gate, `ui_integrity_checks`)
- [ ] 6.4 `ResumenIVA.tsx` — plain-language rendering of the M303 result (glossary terms only, from `docs/domain-context.md`); every amount paired with its period; raw casillas as secondary/collapsed detail
- [ ] 6.5 `ConfirmacionModal.tsx` — período, ejercicio, total, IBAN (last 4 digits), due date; confirm button requires deliberate click, no auto-advance; calls `POST /confirmar` only on click
- [ ] 6.6 `RpaStatus.tsx` — the 4-state component (`waiting`/`needs-re-auth`/`failed`/`done`) per `design.md` SPEC-F5-05's state table, driven by a Supabase Realtime subscription on `presentacion` filtered by `proceso_id`, plus the narrow 5s QR-refresh poll while `presentando`
- [ ] 6.7 Verify every component renders at 375px width (`config.yaml`'s `min_viewport_width`) — manual check or a Playwright viewport assertion per component
- [ ] 6.8 Verify no fiscal term outside `docs/domain-context.md`'s glossary appears in any component's copy (manual review against the glossary table)

## 7. Backend: Context Management — D11 Rolling Window (SPEC-F5-06)

Acceptance criteria: none directly (D11 is `MEDIA` priority, not a CA-F5 item), but explicitly requested in scope

- [ ] 7.1 Write failing test `test_recopilar_datos_recorta_historial_si_supera_15_turnos`: given an `EstadoP04` with 20 messages, `recopilar_datos` sends only the first + last 14 to the LLM (assert via the mocked Anthropic client's call args), while `estado["mensajes"]` itself keeps the full history for display purposes (the trim is a per-call view, not a destructive mutation of the persisted state)
- [ ] 7.2 Write failing test `test_recopilar_datos_no_recorta_bajo_15_turnos`: regression guard, unchanged behavior below the threshold
- [ ] 7.3 Verify tests fail: `pytest tests/agent/nodes/test_recopilar_datos.py -k "recorta" -v`
- [ ] 7.4 Implement the rolling-window trim inside `recopilar_datos` (`src/agent/nodes/recopilar_datos.py`), applied only to the LLM-facing message list, per `design.md` SPEC-F5-06
- [ ] 7.5 Run tests — must pass; run the full agent suite to confirm no regression: `pytest tests/agent/ -v --cov=src.agent --cov-branch --cov-report=term-missing` (must remain 100%)

## 8. Backend: Unit Test and DB Verification Report (MANDATORY)

- [ ] 8.1 Agent executes the full backend suite itself: `pytest tests/ -v --cov=src/fiscal --cov=src/agent --cov=src/rpa --cov=src/workers --cov=src/api --cov-branch --cov-report=term-missing`
- [ ] 8.2 Verify DB state pre/post (presentacion, alerta, factura_emitida/recibida row counts) — restore if any test left residue
- [ ] 8.3 Write the report to `specs/integracion-mvp/reports/YYYY-MM-DD-step-8-unit-test-and-db-verification.md` per the standard template

## 9. Backend: Manual Endpoint Testing with curl (MANDATORY)

- [ ] 9.1 Start `uvicorn src.api.main:app --reload --port 8000` (agent starts it itself, per `config.yaml`'s `never_delegate` rule)
- [ ] 9.2 `curl http://localhost:8000/health` — confirm `{"status": "ok", "db": "ok", "redis": "ok"}`
- [ ] 9.3 Using `$TEST_JWT` from `.env.test`: `curl -X POST .../iniciar`, `.../facturas/ocr` (with a real test invoice image), `.../mensaje/{proceso_id}`, `.../calcular`, `.../confirmar`, `GET .../estado/{proceso_id}`, `GET .../justificante/{proceso_id}` — full sequence against the local stack, ARQ worker running against the Phase 4 AEAT stubs (never real AEAT)
- [ ] 9.4 Confirm each response matches `docs/api-spec.yml`'s schema (adjusted for the two documented deviations)
- [ ] 9.5 Write the report to `specs/integracion-mvp/reports/YYYY-MM-DD-step-9-curl-testing.md`

## 10. Frontend: E2E Testing with Playwright (MANDATORY)

- [ ] 10.1 Start backend (`uvicorn`) + frontend (`npm run dev`) + local Supabase + Redis + ARQ worker, all itself, per `never_delegate`
- [ ] 10.2 `e2e/happy-path.spec.ts` — CA-F5-01: login → chat/upload invoices → review → confirm → `RpaStatus` reaches `done` → justificante link works. Timed, asserted under the CA-F5-01 threshold framing (documented in the report, real 5-minute wall-clock timing is only meaningful against a real AEAT session — this test times the *system's own* steps, not AEAT's response time, since AEAT is stubbed)
- [ ] 10.3 `e2e/ocr-upload.spec.ts` — CA-F5-02: 3 invoice images uploaded via `FacturaUploader`, OCR extraction, review (including at least one confidence < 0.8 field), confirm
- [ ] 10.4 `e2e/session-expiry.spec.ts` — CA-F5-03: mocked `sesion_expirada` failure on first attempt, `RpaStatus` shows `needs-re-auth`, automatic retry succeeds, `done` reached with no data loss
- [ ] 10.5 `e2e/aeat-error.spec.ts` — CA-F5-04: mocked non-retryable AEAT error, `RpaStatus` shows `failed` with a readable message, process state persists for the user to inspect
- [ ] 10.6 `e2e/cancel-confirmacion.spec.ts` — the mandatory critical-negative case (`config.yaml` frontend notes): user clicks cancel in `ConfirmacionModal` → process reverts to pending, no ARQ job enqueued (asserted via a spy/mock on the enqueue call or by confirming `presentacion.estado` never reaches `presentando`)
- [ ] 10.7 Run all 6 specs: `npx playwright test` — all must pass
- [ ] 10.8 Manual check in Chrome and Safari (current versions) — zero console errors (CA-F5-08)
- [ ] 10.9 Write the report to `specs/integracion-mvp/reports/YYYY-MM-DD-step-10-e2e-playwright.md`

## 11. Update Technical Documentation (MANDATORY, both agents)

- [ ] 11.1 Update `docs/api-spec.yml` to reflect the two documented deviations (OCR path move to `/facturas/ocr`, new `/mensaje/{proceso_id}` endpoint) — the spec must match what's actually built
- [ ] 11.2 Update `docs/development_guide.md`: frontend setup (`cd frontend && npm install && npm run dev`), new env vars, running the ARQ worker (`arq src.workers.rpa_worker.WorkerSettings`), full local-stack startup order (Supabase → Redis → ARQ worker → uvicorn → Next.js)
- [ ] 11.3 Update `CHANGELOG.md` with Phase 5 deliverables
- [ ] 11.4 Note explicitly in documentation that deployment (`SPEC-F5-05` in the functional spec, Dockerfile/docker-compose/rollback) is **not** covered by this change — flagged as an open follow-up, per `design.md`'s closing note
- [ ] 11.5 Note the D11 reinterpretation (per-session runtime trigger vs. the PDR's original fleet-average decision gate) in documentation, so a future reader isn't confused by the mismatch with the PDR's literal wording

## Exit criteria (Orchestrator evaluates before accepting this change)

- All tasks above checked `[x]`, with no work silently skipped
- `pytest tests/ --cov=src/fiscal --cov=src/agent --cov=src/rpa --cov=src/workers --cov=src/api --cov-branch` reports 100% on every module except lines explicitly requiring a live AEAT/Cl@ve Móvil session
- `npx playwright test` passes all 6 specs; manual Chrome/Safari console check is clean
- No fiscal arithmetic exists in any `src/api/` handler — every euro amount traces back to `src/fiscal/` or the graph's own `calcular` node
- The `confirmar` LangGraph interrupt remains the only path to `confirmado=True` — the structured `/calcular` fast-path still lands there, never bypasses it
- ARQ retry only fires for `error_code='sesion_expirada'` — verified by test, not just code review (Task 3.3/3.4)
- Realtime is enabled on `presentacion` via migration, not a client-side polling substitute (except the documented narrow QR-refresh poll)
- No new Supabase table created without RLS + a passing cross-user test (this phase adds none — `presentacion`/`alerta` are pre-existing)
- `ConfirmacionModal`'s deliberate-click requirement, the OCR confidence gate, the 4 RPA states, the glossary-only copy, the period-paired-amounts rule, and the 375px minimum width are all verified by the E2E suite, not left as unverified claims
- The OCR-endpoint path move and the new `/mensaje` endpoint are reflected in an updated `docs/api-spec.yml`, not left as an undocumented divergence
- The deployment gap (functional spec's `SPEC-F5-05`) is explicitly flagged as an open follow-up in documentation, not silently treated as done
- No out-of-scope items implemented: P05-P09, P13, P14, P24-P26, régimen foral, Authentication Model A, any dashboard beyond the minimal conversational flow, D11's summarization alternative (rolling window only)
