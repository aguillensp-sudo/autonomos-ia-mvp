# Tasks: rpa-aeat

`openspec/config.yaml` read: yes. `docs/openspec-tasks-mandatory-steps.md` read: yes. Branch naming: `feature/rpa-aeat` per config. Agent: `backend_developer` (model `claude-sonnet-4-6` per `openspec/config.yaml`; GLM-5.2 via DeepInfra once the harness exists).

**No frontend or API-endpoint work in this change** — F4 is the RPA module + ARQ worker only (`/api/proceso/p04/confirmar` and friends are Phase 5's job, confirmed by reading `docs/api-spec.yml` and `src/api/routers/`, which only has Phase-1-era endpoints today). Step N+2 (curl testing) and Step N+3 (Playwright E2E of our own frontend) are therefore not applicable and are explicitly marked skipped below, per the Phase 3 precedent — not silently omitted.

**Important distinction:** this change uses Playwright extensively, but as the RPA automation tool driving the *AEAT* site, not as our own E2E test framework. All RPA-facing tests in this change use Playwright against **mocked/stub AEAT responses** (SPEC-F4-06) — never a real browser session against the live AEAT site outside of tests explicitly marked `@pytest.mark.integration`.

**Blocking prerequisite — read before starting implementation:** several tasks below make (or, in tests, simulate) a **real Playwright browser session against the live AEAT Sede Electrónica**, which additionally requires a real Cl@ve PIN and cannot be executed in CI or without a live test NIF. Any such test is marked `@pytest.mark.integration` per the `pytest.ini` marker convention from Correction 2, and is never run in the default TDD cycle (`pytest -m "not integration"`). The agent implementing this change must either arrange a sandboxed/test AEAT credential before running those specific tests, or stop and report the blocker explicitly rather than mark the step `[x]` without having actually run it — per `docs/openspec-tasks-mandatory-steps.md` §3.

## 0. Setup: Create Feature Branch (MANDATORY — FIRST STEP)

- [ ] 0.1 Create feature branch `feature/rpa-aeat` from `main`
- [ ] 0.2 Verify branch creation: `git branch --show-current`

## 1. Backend: Prerequisite Fix — `notificar.py` writes `presentacion` on confirm (SPEC-F4-00)

Acceptance criteria: prerequisite for the ARQ worker to have anything to pick up (no CA-F4 criterion directly, but blocks all of them)

- [ ] 1.1 Write failing test `test_notificar_confirma_escribe_presentacion.py`: given `confirmado=True` and a populated `resultado_m303`, calling `notificar()` results in a `presentacion` row with `estado='confirmado'` and the expected fields (`total_devengado`, `total_deducible`, `saldo_compensar_aplicado`, `log_confirmacion`)
- [ ] 1.2 Write failing regression test confirming the existing `cancelado=True` branch and its assertions (from `specs/archive/agente-conversacional`) are untouched
- [ ] 1.3 Verify tests fail: `pytest tests/agent/nodes/test_notificar_confirma_escribe_presentacion.py -v`
- [ ] 1.4 Implement the additive upsert in `src/agent/nodes/notificar.py`'s `confirmado=True` branch per `design.md` SPEC-F4-00
- [ ] 1.5 Run tests — must pass: `pytest tests/agent/nodes/test_notificar_confirma_escribe_presentacion.py tests/agent/nodes/test_notificar.py -v`

## 2. Backend: Selector Map + Loader (SPEC-F4-01)

Acceptance criteria: CA-F4-10

- [ ] 2.1 Write failing test `test_cargar_selectores_devuelve_dict_completo`: loading `src/rpa/selectors/aeat_m303.yml` returns a dict with every top-level key SPEC-F4-01 defines (`clave_pin`, `navegacion`, `pagina_1_identificacion`, `pagina_2_devengado`, `pagina_3_deducible`, `pagina_4_resultado`, `acciones`, `mensajes_error`)
- [ ] 2.2 Write failing test `test_ningun_modulo_rpa_hardcodea_selectores`: a static grep-style check (e.g. via `ast` or a regex over `src/rpa/aeat/*.py`) asserting no CSS/aria selector string literals appear outside `src/rpa/selectors/aeat_m303.yml` and `src/rpa/aeat/selectores.py`
- [ ] 2.3 Verify tests fail: `pytest tests/rpa/test_selectores.py -v`
- [ ] 2.4 Implement `src/rpa/selectors/aeat_m303.yml` (full casilla-by-casilla map, 01-72 + 110 + auth/nav/action selectors) and `src/rpa/aeat/selectores.py::cargar_selectores()`
- [ ] 2.5 Run tests — must pass: `pytest tests/rpa/test_selectores.py -v`

## 3. Backend: Casilla Mapping Adapter (SPEC-F4-03)

Acceptance criteria: CA-F4-03, CA-F4-04, CA-F4-05, supports CA-F4-06

- [ ] 3.1 Write failing test `test_construir_mapa_casillas_devengado_por_tipo`: a `ResultadoM303` with 21%-only sales populates casillas 07/08/09 and leaves 01-06/150-152 unset (not zero)
- [ ] 3.2 Write failing test `test_construir_mapa_casillas_devengado_multiples_tipos`: sales at both 4% and 21% populate both blocks independently
- [ ] 3.3 Write failing test `test_construir_mapa_casillas_isp`: ISP amount populates casillas 12-13 only, distinct from the general-regime blocks (casuística C05)
- [ ] 3.4 Write failing test `test_construir_mapa_casillas_modificacion_rectificativa`: a non-zero `base_modificacion`/`cuota_modificacion` populates casillas 14-15 as a distinct pair, and casilla 27's total still equals the arithmetic sum documented in `src/fiscal/models.py` (casuística C04)
- [ ] 3.5 Write failing test `test_construir_mapa_casillas_deducible_corriente_default`: an unrecognized `categoria_gasto` key falls back to the corriente-interior default (28-29), per the Product-Owner-approved mapping table
- [ ] 3.6 Write failing test `test_construir_mapa_casillas_deducible_grupos_explicitos`: categories explicitly mapped to inversión (30-31), importación (32-35), intracomunitario (36-37), rectificación (40-41) land in the correct casillas, not all folded into 28-29
- [ ] 3.7 Write failing test `test_construir_mapa_casillas_resultado_a_ingresar`, `_a_compensar`, `_a_devolver`, `_sin_actividad`: each `tipo_resultado` populates the correct 46/66/69/70/71/72/110 subset
- [ ] 3.8 Write failing test `test_construir_mapa_casillas_bloque_informativo`: casillas 59 (C11 intracomunitaria), 60 (C10 exportación), 61-63 populate only when > 0
- [ ] 3.9 Verify tests fail: `pytest tests/rpa/test_casilla_map.py -v`
- [ ] 3.10 Implement `src/rpa/casilla_map.py` (`construir_mapa_casillas`, `TABLA_CASILLA_DEDUCIBLE`) per `design.md` SPEC-F4-03 — pure function, no I/O, delegates all arithmetic to already-computed `ResultadoM303`/`ResultadoDevengado`/`ResultadoDeducible` fields
- [ ] 3.11 Run tests — must pass: `pytest tests/rpa/test_casilla_map.py -v`
- [ ] 3.12 Add a `test_construir_mapa_casillas_no_reimplementa_aritmetica_fiscal` regression test: asserts every value in the returned map is either copied verbatim from a `ResultadoM303`/`ResultadoDevengado`/`ResultadoDeducible` field or a documented pass-through, proving no new `+`/`-`/`*` fiscal arithmetic was introduced in `casilla_map.py`

## 4. Backend: Cl@ve PIN Authentication (SPEC-F4-02)

Acceptance criteria: CA-F4-01

- [ ] 4.1 Write failing unit test `test_autenticar_clave_pin_verifica_nif_coincide` (mocked Playwright `Page`): a successful login where the authenticated NIF matches `perfil.nif` returns `SesionAEAT(activa=True, ...)`
- [ ] 4.2 Write failing unit test `test_autenticar_clave_pin_nif_no_coincide_lanza_error`: a mismatch between the authenticated NIF and `perfil.nif` raises `AutenticacionError`, and `SesionAEAT` is never returned
- [ ] 4.3 Write failing unit test `test_sesion_expira_tras_10_minutos`: a `SesionAEAT` with a `timestamp_autenticacion` more than 10 minutes in the past raises `SesionExpiradaError` when checked by the form-filling step
- [ ] 4.4 Verify tests fail: `pytest tests/rpa/aeat/test_autenticacion.py -v`
- [ ] 4.5 Implement `src/rpa/aeat/autenticacion.py` (`autenticar_clave_pin`, `SesionAEAT`, `AutenticacionError`, `SesionExpiradaError`) per `design.md` SPEC-F4-02, using selectors loaded from Task 2
- [ ] 4.6 Run tests — must pass: `pytest tests/rpa/aeat/test_autenticacion.py -v`
- [ ] 4.7 Write `@pytest.mark.integration` test `test_autenticar_clave_pin_sesion_real` exercising a real Cl@ve PIN login against AEAT. This test is executed MANUALLY by the Product Owner using their own NIF and Cl@ve PIN — it cannot be run by the agent. The agent must: (a) write the test code; (b) mark it `@pytest.mark.integration`; (c) document in the report that execution requires manual Product Owner action with real AEAT credentials; (d) leave it marked `[ ]` until the Product Owner confirms execution.

## 5. Backend: AEAT Stub Fixtures (SPEC-F4-06)

Acceptance criteria: prerequisite for Tasks 6-8's unit tests (no real AEAT calls)

- [ ] 5.1 Implement `tests/rpa/_stubs_aeat.py` with the four fixtures: `respuesta_exito()`, `respuesta_validacion_error()`, `respuesta_periodo_ya_presentado()`, `respuesta_aeat_no_disponible()`
- [ ] 5.2 Write a smoke test `test_stubs_aeat_shape` asserting each fixture returns the fields the form-filling/error-handling code expects to parse
- [ ] 5.3 Run test — must pass: `pytest tests/rpa/test_stubs_aeat.py -v`

## 6. Backend: Form Navigation, Filling, Validation, Submission (SPEC-F4-04)

Acceptance criteria: CA-F4-02, CA-F4-03, CA-F4-04, CA-F4-05, CA-F4-06

- [ ] 6.1 Write failing test `test_navegar_a_modelo_303_verifica_prellenado`: given a mocked page exposing pre-filled NIF/nombre matching `perfil.nif`, navigation succeeds; a mismatch raises an error before any casilla is touched
- [ ] 6.2 Write failing test `test_rellenar_pagina_identificacion_marca_regimen_general_y_criterio_caja`: `perfil.regimen_iva == "caja"` checks the criterio-de-caja box; otherwise it's left unchecked
- [ ] 6.3 Write failing test `test_rellenar_pagina_devengado_deja_en_blanco_tipos_no_aplicables`: a mapa_casillas with only 21% populated results in no writes to the 4%/10%/0% fields (not zero-writes) — regression guard for T04-20's explicit warning
- [ ] 6.4 Write failing test `test_rellenar_pagina_devengado_detecta_discrepancia_casilla_27` (using `respuesta_validacion_error`-style stub returning a different AEAT-computed casilla 27): a difference > 0.02 € raises `DiscrepanciaResultadoError` (T04-E3) before proceeding to the deducible page
- [ ] 6.5 Write failing test `test_rellenar_pagina_devengado_tolera_diferencia_redondeo`: a difference ≤ 0.02 € proceeds without error
- [ ] 6.6 Write failing test `test_rellenar_pagina_deducible_detecta_discrepancia_casilla_45`: same discrepancy check against casilla 45
- [ ] 6.7 Write failing test `test_rellenar_pagina_resultado_a_ingresar_domiciliacion`, `_nrc`, `_tarjeta_detiene_flujo`: domiciliación writes IBAN + fecha; NRC validates format (22 alphanumeric) before writing and raises on malformed input (T04-E2 precondition); `tarjeta` returns a state requiring manual completion and writes nothing to card fields
- [ ] 6.8 Write failing test `test_rellenar_pagina_resultado_a_compensar`, `_a_devolver_4t`, `_sin_actividad`: each path writes the correct casilla subset per SPEC-F4-03's result-block table
- [ ] 6.9 Write failing test `test_rellenar_bloque_informativo_solo_valores_positivos`: casillas 59-63 are written only when > 0
- [ ] 6.10 Write failing test `test_validar_formulario_bloquea_si_aeat_reporta_errores` (using `respuesta_validacion_error` stub): a non-empty AEAT error list is surfaced and the caller is signaled not to proceed to `presentar()`
- [ ] 6.11 Write failing test `test_presentar_verifica_sesion_fresca_antes_de_enviar`: a `SesionAEAT` older than 10 minutes raises `SesionExpiradaError` instead of submitting
- [ ] 6.12 Write failing test `test_presentar_captura_csv_nrc_timestamp` (using `respuesta_exito` stub): a successful submission returns `PresentacionResult(csv, nrc, timestamp)`
- [ ] 6.13 Verify tests fail: `pytest tests/rpa/aeat/test_m303_form.py -v`
- [ ] 6.14 Implement `src/rpa/aeat/m303_form.py` (`navegar_a_modelo_303`, `rellenar_pagina_identificacion`, `rellenar_pagina_devengado`, `rellenar_pagina_deducible`, `rellenar_pagina_resultado`, `rellenar_bloque_informativo`, `validar_formulario`, `presentar`, `DiscrepanciaResultadoError`) per `design.md` SPEC-F4-04
- [ ] 6.15 Run tests — must pass: `pytest tests/rpa/aeat/test_m303_form.py -v`

## 7. Backend: RPA Error Handling — T04-E1 through T04-E4

Acceptance criteria: CA-F4-07, CA-F4-08

- [ ] 7.1 Write failing test `test_error_e1_periodo_ya_presentado_existe_en_bd`: given a `presentacion` row already exists for `(user_id, ejercicio, periodo)`, the worker surfaces its CSV/justificante and never calls `presentar()`
- [ ] 7.2 Write failing test `test_error_e1_periodo_ya_presentado_no_existe_en_bd`: AEAT reports an existing declaration but no local `presentacion` row exists → `error_code='periodo_ya_presentado_externo'`, flagged for manual review
- [ ] 7.3 Write failing test `test_error_e4_fallo_envio_guarda_screenshot_y_reintenta`: a submission failure (using `respuesta_aeat_no_disponible` stub) saves a screenshot to Supabase Storage, sets `error_code`, and the retry path re-authenticates from scratch rather than resubmitting against the stale session
- [ ] 7.4 Write failing test `test_error_e4_reintento_no_duplica_si_ya_presentado`: after a retry, if step 1's existing-declaration guard now finds a row (because a previous attempt actually succeeded server-side despite a client-side timeout), the retry stops instead of submitting again
- [ ] 7.5 Verify tests fail: `pytest tests/rpa/aeat/test_errores_rpa.py -v`
- [ ] 7.6 Implement the T04-E1/T04-E4 handling in `src/workers/rpa_worker.py` (existing-declaration precheck, screenshot-on-failure, idempotent retry) per `design.md` SPEC-F4-04's error table
- [ ] 7.7 Run tests — must pass: `pytest tests/rpa/aeat/test_errores_rpa.py -v`

## 8. Backend: Justificante Download, Verification, Storage (SPEC-F4-05)

Acceptance criteria: CA-F4-09

- [ ] 8.1 Write failing test `test_descargar_justificante_verifica_campos_coinciden`: a justificante PDF whose NIF/modelo/ejercicio/periodo/CSV/resultado all match the just-submitted values passes verification
- [ ] 8.2 Write failing test `test_descargar_justificante_detecta_discrepancia`: a mismatch (e.g. wrong período in the extracted PDF text) raises `error_code='justificante_no_coincide'` instead of silently accepting the file
- [ ] 8.3 Write failing test `test_descargar_justificante_sube_a_storage_path_correcto`: the uploaded path follows `justificantes/{user_id}/{ejercicio}_{periodo}.pdf`, mirroring Phase 3's `{tipo}/{user_id}/{filename}` convention
- [ ] 8.4 Write failing test `test_descargar_justificante_actualiza_presentacion`: on success, `presentacion.estado='presentado'`, `csv_aeat`, `nrc` (if applicable), `justificante_path` are all updated
- [ ] 8.5 Verify tests fail: `pytest tests/rpa/aeat/test_justificante.py -v`
- [ ] 8.6 Implement `src/rpa/aeat/justificante.py` (`descargar_justificante`, PDF text-layer parsing, Supabase Storage upload) per `design.md` SPEC-F4-05
- [ ] 8.7 Run tests — must pass: `pytest tests/rpa/aeat/test_justificante.py -v`

## 9. Backend: ARQ Worker Integration

Acceptance criteria: ties CA-F4-01 through CA-F4-09 together into one end-to-end flow

- [ ] 9.1 Write failing integration test `test_procesar_presentacion_flujo_completo_exito` (mocked Playwright throughout, using the Task 5 stubs): a `presentacion` row in `estado='confirmado'` transitions through `presentando` to `presentado`, with `csv_aeat`/`justificante_path` populated
- [ ] 9.2 Write failing integration test `test_procesar_presentacion_flujo_error_marca_estado_error`: any of the T04-E1..E4 paths results in `estado='error'` with a populated `error_code`, never leaves the row stuck in `presentando`
- [ ] 9.3 Write failing integration test `test_procesar_presentacion_idempotente_si_ya_presentado`: re-enqueuing a job for a row already `estado='presentado'` is a no-op — no second AEAT session is opened
- [ ] 9.4 Verify tests fail: `pytest tests/workers/test_rpa_worker.py -v`
- [ ] 9.5 Implement `src/workers/rpa_worker.py::procesar_presentacion` (ARQ job registration, state-transition idempotency guard) per `design.md`
- [ ] 9.6 Run tests — must pass: `pytest tests/workers/test_rpa_worker.py -v`
- [ ] 9.7 Run full suite with coverage — must remain 100% on `src/fiscal/` (unchanged) and achieve full coverage on `src/rpa/` and `src/workers/` except lines explicitly requiring a live AEAT session: `pytest tests/ -v --cov=src/fiscal --cov=src/rpa --cov=src/workers --cov-branch --cov-report=term-missing`

## 10. Unit Test and DB Verification Report (MANDATORY)

- [ ] 10.1 Agent executes the full suite itself (never delegates): `pytest tests/ -v --cov=src/fiscal --cov=src/rpa --cov=src/workers --cov-branch --cov-report=term-missing`
- [ ] 10.2 Agent verifies no new migration was needed (per `design.md`, `presentacion`'s existing schema already covers F4) by confirming `mcp__.../list_migrations` (or equivalent) shows no new file, or explicitly stating why one was needed if the casilla-storage design changed during implementation
- [ ] 10.3 Write the report to `specs/rpa-aeat/reports/YYYY-MM-DD-step-10-unit-test-and-db-verification.md` per `docs/openspec-tasks-mandatory-steps.md`'s template, including: full pytest summary, coverage table, confirmation that `pytest -m "not integration"` excludes every real-AEAT test, and the DB-state check from 10.2

## 11. Manual Endpoint Testing with curl (NOT APPLICABLE THIS PHASE)

- [ ] 11.1 N/A — no API endpoints are created or modified this phase; F4 is the RPA module + ARQ worker only, `/api/proceso/p04/confirmar` and related endpoints are Phase 5's scope (confirmed by reading `docs/api-spec.yml` and `src/api/routers/`). Explicitly marked N/A, not silently omitted, mirroring Phase 1/2/3 precedent.

## 12. Frontend: E2E Testing with Playwright (NOT APPLICABLE THIS PHASE)

- [ ] 12.1 N/A — no frontend exists yet (Phase 5 scope). Note: this change's own extensive use of Playwright is for *AEAT automation*, not for testing our own UI — see the distinction called out at the top of this file. Explicitly marked N/A, not silently omitted.

## 13. Update Technical Documentation (MANDATORY)

- [ ] 13.1 Update `docs/backend-standards.md` if the final `src/rpa/`/`src/workers/` layout differs in any way from the Project-structure block already there
- [ ] 13.2 Update `docs/development_guide.md` with any new environment variables (e.g. AEAT sandbox/test credentials needed for `@pytest.mark.integration` tests, ARQ/Redis connection settings if not already documented)
- [ ] 13.3 Update `CHANGELOG.md` with what Phase 4 delivered
- [ ] 13.4 Note explicitly in documentation that Phase 5 (API + frontend) is what actually enqueues `procesar_presentacion` jobs — this phase implements the worker function and its registration only, not the enqueueing endpoint
- [ ] 13.5 Confirm the documentation update references `TABLA_CASILLA_DEDUCIBLE` (per `design.md` SPEC-F4-03) as the Product-Owner-approved mapping, and notes that future category additions are made in that data file, never in `m303_form.py`

## Exit criteria (Orchestrator evaluates before accepting this change)

- All tasks above checked `[x]`, OR explicitly documented as blocked on live AEAT test credentials with no other work silently skipped
- `pytest tests/ --cov=src/fiscal --cov=src/rpa --cov=src/workers --cov-branch` reports 100% on `src/fiscal/` (unchanged) and full coverage on `src/rpa/`/`src/workers/` except lines explicitly documented as requiring a live AEAT session
- `pytest -m "not integration" tests/ -v` passes with zero real AEAT/network calls
- No selector string literals exist outside `src/rpa/selectors/aeat_m303.yml` and `src/rpa/aeat/selectores.py` (Task 2.2's static check)
- `casilla_map.py` introduces no new fiscal arithmetic — every value traces back to an already-computed `ResultadoM303`/`ResultadoDevengado`/`ResultadoDeducible` field (Task 3.12)
- T04-E3 (result discrepancy) is a hard stop with no auto-correction path, verified by tests, not just code review
- `notificar.py`'s `confirmado=True` branch now writes a `presentacion` row (Task 1), giving the ARQ worker a real row to pick up
- The unit-test-and-db-verification report exists under `specs/rpa-aeat/reports/`
- No out-of-scope items implemented: Authentication Model A, any F5 API endpoint, frontend/chat UI, P04-R rectificativa filing, real VIES validation, full prorrata calculation, anything else from `openspec/config.yaml` → `out_of_scope`
- `casilla_map.py` implements the Product-Owner-approved `TABLA_CASILLA_DEDUCIBLE` mapping exactly (corriente interior, bienes de inversión, adquisiciones intracomunitarias groups per `design.md` SPEC-F4-03), not a placeholder or all-default mapping
- Task 4.7 (`test_autenticar_clave_pin_sesion_real`) is written and marked `@pytest.mark.integration`, but left unchecked `[ ]` pending manual execution by the Product Owner with real AEAT/Cl@ve PIN credentials — it must not be marked `[x]` by the agent under any circumstance
