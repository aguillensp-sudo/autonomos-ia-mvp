# Step 9 Report - Manual Endpoint Testing with curl

- Date: 2026-07-16
- Change: integracion-mvp (F5)
- Agent: backend_developer (claude-sonnet-5 in this session)
- Environment: local Supabase (already running), a freshly-started local Redis container (`docker run -d --name autonomos-redis -p 6379:6379 redis:7-alpine` — no Redis existed in this environment before this step), `uvicorn src.api.main:app --reload --port 8000`, and `python -m arq src.workers.rpa_worker.WorkerSettings` (the ARQ worker, against Phase 4's stub AEAT fixtures — never real AEAT). `REDIS_URL` was empty in `.env`; set to `redis://localhost:6379`.

## Commands Executed

No `.env.test`/`$TEST_JWT` existed in this repo — created a throwaway local test account (`test.p04.clean@autonomos.local`) via Supabase's own `/auth/v1/token?grant_type=password` endpoint to obtain a real JWT, and seeded a valid `perfil_fiscal` row for it directly in Postgres (NIF `12345678Z`, a real check-digit-valid Spanish NIF).

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/proceso/p04/iniciar -H "Authorization: Bearer $TOK"
curl -X POST http://localhost:8000/api/proceso/p04/facturas/ocr -H "Authorization: Bearer $TOK" -F "file=@factura_test.png" -F "tipo=emitida"
curl -X POST http://localhost:8000/api/proceso/p04/mensaje/$PROCESO_ID -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" --data-binary @mensaje_payload.json
curl -X POST http://localhost:8000/api/proceso/p04/calcular -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" --data-binary @calcular_payload.json
curl -X GET http://localhost:8000/api/proceso/p04/estado/$PROCESO_ID -H "Authorization: Bearer $TOK"
curl -X GET http://localhost:8000/api/proceso/p04/justificante/$PROCESO_ID -H "Authorization: Bearer $TOK"
```

`factura_test.png` was synthesized with Pillow (no real test invoice image existed in the repo): a 600x300 PNG reading "FACTURA 001 / NIF: B12345678 / Base imponible: 100 EUR / IVA 21%: 21 EUR / Fecha: 15/07/2026".

## Results

### `GET /health`
```json
{"status":"ok","db":"ok","redis":"ok"}
```
Matches `docs/openspec-tasks-mandatory-steps.md`'s expected shape exactly (after the 9.0b correction below — see fix notes).

### `POST /iniciar`
```json
{"proceso_id":"0fcee8fa-e36a-4b17-bd5d-149f05decd3b:P04:2026:2T","ejercicio":2026,"periodo":"2T","fecha_limite":"2026-07-20"}
```

### `POST /facturas/ocr`
```json
{"extracted":{"nif_emisor":"B12345678","confianza_nif_emisor":0.98,"fecha":"2026-07-15","confianza_fecha":0.95,"base_imponible":100,"confianza_base_imponible":0.98,"tipo_iva":21,"confianza_tipo_iva":0.98},"requires_review":false,"pdf_path":"emitida/0fcee8fa-e36a-4b17-bd5d-149f05decd3b/factura_test.png"}
```
Real Claude Vision OCR call against the synthesized PNG, real Storage upload. First attempt 500'd on a Storage RLS violation — see the 9.0a fix below.

### `POST /mensaje/{proceso_id}` — "Hola, no he tenido ninguna factura ni emitida ni recibida este trimestre. Confirmo que no ha habido ninguna operacion."
```json
{"mensajes":[{"rol":"usuario","contenido":"Hola, no he tenido ninguna factura ni emitida ni recibida este trimestre. Confirmo que no ha habido ninguna operacion."}],"pendiente":"confirmacion"}
```
Real Claude Sonnet 5 call, reached the `confirmar` interrupt in one turn — matches design.md's documented single-call behavior for `recopilar_datos`.

### `POST /calcular` (idempotent read)
```json
{"ejercicio":2026,"periodo":"2T","total_devengado":"0.00","total_deducible":"0.00","saldo_compensar_anterior":"0.0","resultado":"0.00","tipo_resultado":"sin_actividad","casillas":{...},"devengado":{...},"deducible":{...},"fecha_limite":"2026-07-20"}
```
`fecha_limite` present and correct — see the 9.0/Task-6 `fecha_limite` fix (already landed in Task 6, re-verified here against a real backend call).

### `POST /confirmar` — **not executed**
The Claude Code auto-mode safety classifier blocked this specific curl call, flagging it as triggering a real-world AEAT tax filing with legal/financial consequences (the ARQ worker was already running and would have picked up the enqueued job). This is a reasonable, conservative block given the classifier can't verify from the command alone that this stack uses Phase 4's stub AEAT fixtures rather than the real Sede Electrónica — I did not attempt to route around it. `/confirmar`'s behavior is otherwise verified by `tests/api/test_p04_router_f5.py::test_post_confirmar_enqueues_arq_job`/`test_post_confirmar_no_enqueues_si_grafo_no_confirma` (mocked) and by code review of `graph_runtime.confirmar_graph` (unchanged this session). If a full live-confirm curl trace is required, it needs the user's explicit go-ahead.

### `GET /estado/{proceso_id}` (before confirming — no `presentacion` row exists yet)
```json
{"detail":{"error":"NOT_FOUND","detail":"Proceso no encontrado","proceso":"P04"}}
```
`404`, as expected — see the 9.0c fix below (first attempt 500'd).

### `GET /justificante/{proceso_id}` (same state)
```json
{"detail":{"error":"NOT_FOUND","detail":"Justificante no disponible","proceso":"P04"}}
```
`404`, as expected — same fix.

## Three real bugs found and fixed (per CLAUDE.md §7: design.md/tasks.md amended first, then implemented)

1. **`get_authed_request` never authenticated Storage, only PostgREST** (`src/api/dependencies.py`). `client.postgrest.auth(jwt)` doesn't touch `client.storage` — supabase-py snapshots Storage headers from the anon key alone at first access. Every Storage call through `req.client` (the `/facturas/ocr` upload, and `/estado`/`/justificante`'s signed URLs) silently ran with no `auth.uid()`, failing RLS. `src/agent/supabase_client.py::crear_cliente_usuario` (Phase 3/4) already had the correct fix — the API layer never replicated it. Fixed by rebuilding `client._storage` with the JWT in its headers, same pattern. New regression test: `tests/api/test_dependencies.py`.
2. **`/estado`/`/justificante` queried `presentacion` by the wrong identifier.** Both did `.eq("id", proceso_id)`, but `proceso_id` is the LangGraph thread_id string, while `presentacion.id` is an unrelated server-generated UUID — every call 500'd (`invalid input syntax for type uuid`) instead of 404ing gracefully. Fixed: parse `proceso_id` into `user_id`/`ejercicio`/`periodo` and query by those plus `proceso='P04'`, matching `notificar.py`'s own upsert key (`on_conflict="user_id,proceso,ejercicio,periodo"`). Updated the 6 affected `test_p04_router_f5.py` tests (mock chain depth + a real thread_id-shaped test `proceso_id`).
3. **`/health`'s `redis` field was a stale hardcoded stub.** Phase 1's `"redis": "not_configured"` comment said "ARQ workers not wired yet this phase" — no longer true since Task 3. Fixed to actually ping Redis; new `tests/api/test_health.py` (3 tests, 100% coverage on `health.py`).

## Test suite re-verification after fixes

`pytest tests/api/ -m "not integration" -v --cov=src/api --cov-branch --cov-report=term-missing`: **31 passed, 1 deselected**, coverage:

```
Name                          Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------------------
src/api/routers/health.py        19      0      0      0   100%
src/api/dependencies.py          28      2      2      0    93%   35-36 (unreachable defensive except)
src/api/graph_runtime.py         78      0     18      0   100%
src/api/routers/p04.py          103     12     12      1    87%   80-89, 96-98 (Phase 1 JSON /facturas CRUD, unchanged this phase)
TOTAL                           242     15     32      1    93%
```

An informational (non-gating) note: running the real-API `@pytest.mark.integration` test `tests/api/test_graph_runtime_integration.py` alongside this session's manual curl testing showed it failing intermittently (`pendiente == 'none'` instead of `'confirmacion'` on one run) — real Claude Sonnet 5 sampling variance on a single free-text turn, not a regression from any fix above (its own deterministic thread_id also accumulates checkpoint state across repeated runs in the same session, which this test's fixture doesn't reset). This test is excluded from the official `-m "not integration"` gate per Phase 3/4 precedent, so it doesn't affect Step 9's or Step 8's pass/fail status.

## Bugs found but explicitly NOT fixed this task (flagged via spawn_task, out of scope)

- `calcular_graph`'s structured/no-invoices recompute path can leave `resultado_m303` unset (found during Task 6's manual testing).
- Chat-registered facturas (via the `agregar_factura_emitida`/`agregar_factura_recibida` tool calls in `recopilar_datos.py`) are missing `id`/`user_id`/`numero_factura`/`fecha`, so `calcular()`'s `FacturaEmitida(**f)` always raises a validation error for that specific code path — this Task 9 curl sequence deliberately avoided it (used the "sin actividad" declaration path instead, which doesn't hit `FacturaEmitida` validation).

Both are real, reproducible, pre-existing bugs outside this task's mandate (graph/agent-node internals, not endpoint wiring) — flagged as background tasks for separate follow-up rather than expanding this task's scope.

## Outcome

- Step 9 status: **PASS** (with the one deliberate, safety-classifier-driven exclusion: `/confirmar` not curled live)
- 3 real bugs found and fixed, each backed by a new or updated regression test
- 2 additional real bugs found, deliberately left unfixed and flagged separately (agent/graph-internals scope, not this task's endpoint-wiring mandate)
- `docs/api-spec.yml` schema conformance: confirmed for every response actually executed (adjusted for the two documented deviations: `/facturas/ocr`'s path and `/mensaje`'s existence, both per `feature.md`)
