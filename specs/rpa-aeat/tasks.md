# Tasks: rpa-aeat

`openspec/config.yaml` read: yes. `docs/openspec-tasks-mandatory-steps.md` read: yes. Branch naming: `feature/rpa-aeat` per config. Agent: `backend_developer` (model `claude-sonnet-4-6` per `openspec/config.yaml`; GLM-5.2 via DeepInfra once the harness exists).

**No frontend or API-endpoint work in this change** — F4 is the RPA module + ARQ worker only (`/api/proceso/p04/confirmar` and friends are Phase 5's job, confirmed by reading `docs/api-spec.yml` and `src/api/routers/`, which only has Phase-1-era endpoints today). Step N+2 (curl testing) and Step N+3 (Playwright E2E of our own frontend) are therefore not applicable and are explicitly marked skipped below, per the Phase 3 precedent — not silently omitted.

**Important distinction:** this change uses Playwright extensively, but as the RPA automation tool driving the *AEAT* site, not as our own E2E test framework. All RPA-facing tests in this change use Playwright against **mocked/stub AEAT responses** (SPEC-F4-06) — never a real browser session against the live AEAT site outside of tests explicitly marked `@pytest.mark.integration`.

**Blocking prerequisite — read before starting implementation:** several tasks below make (or, in tests, simulate) a **real Playwright browser session against the live AEAT Sede Electrónica**, which additionally requires a real Cl@ve PIN and cannot be executed in CI or without a live test NIF. Any such test is marked `@pytest.mark.integration` per the `pytest.ini` marker convention from Correction 2, and is never run in the default TDD cycle (`pytest -m "not integration"`). The agent implementing this change must either arrange a sandboxed/test AEAT credential before running those specific tests, or stop and report the blocker explicitly rather than mark the step `[x]` without having actually run it — per `docs/openspec-tasks-mandatory-steps.md` §3.

## 0. Setup: Create Feature Branch (MANDATORY — FIRST STEP)

- [x] 0.1 Create feature branch `feature/rpa-aeat` from `main`
- [x] 0.2 Verify branch creation: `git branch --show-current`

## 1. Backend: Prerequisite Fix — `notificar.py` writes `presentacion` on confirm (SPEC-F4-00)

Acceptance criteria: prerequisite for the ARQ worker to have anything to pick up (no CA-F4 criterion directly, but blocks all of them)

- [x] 1.1 Write failing test `test_notificar_confirma_escribe_presentacion.py`: given `confirmado=True` and a populated `resultado_m303`, calling `notificar()` results in a `presentacion` row with `estado='confirmado'` and the expected fields (`total_devengado`, `total_deducible`, `saldo_compensar_aplicado`, `log_confirmacion`)
- [x] 1.2 Write failing regression test confirming the existing `cancelado=True` branch and its assertions (from `specs/archive/agente-conversacional`) are untouched
- [x] 1.3 Verify tests fail: `pytest tests/agent/nodes/test_notificar_confirma_escribe_presentacion.py -v`
- [x] 1.4 Implement the additive upsert in `src/agent/nodes/notificar.py`'s `confirmado=True` branch per `design.md` SPEC-F4-00
- [x] 1.5 Run tests — must pass: `pytest tests/agent/nodes/test_notificar_confirma_escribe_presentacion.py tests/agent/nodes/test_notificar.py -v`

## 2. Backend: Selector Map + Loader (SPEC-F4-01)

Acceptance criteria: CA-F4-10

- [x] 2.1 Write failing test `test_cargar_selectores_devuelve_dict_completo`: loading `src/rpa/selectors/aeat_m303.yml` returns a dict with every top-level key SPEC-F4-01 defines (`clave_pin`, `navegacion`, `pagina_1_identificacion`, `pagina_2_devengado`, `pagina_3_deducible`, `pagina_4_resultado`, `acciones`, `mensajes_error`)
- [x] 2.2 Write failing test `test_ningun_modulo_rpa_hardcodea_selectores`: a static grep-style check (e.g. via `ast` or a regex over `src/rpa/aeat/*.py`) asserting no CSS/aria selector string literals appear outside `src/rpa/selectors/aeat_m303.yml` and `src/rpa/aeat/selectores.py`
- [x] 2.3 Verify tests fail: `pytest tests/rpa/test_selectores.py -v`
- [x] 2.4 Implement `src/rpa/selectors/aeat_m303.yml` (full casilla-by-casilla map, 01-72 + 110 + auth/nav/action selectors) and `src/rpa/aeat/selectores.py::cargar_selectores()`
- [x] 2.5 Run tests — must pass: `pytest tests/rpa/test_selectores.py -v`

## 3. Backend: Casilla Mapping Adapter (SPEC-F4-03)

Acceptance criteria: CA-F4-03, CA-F4-04, CA-F4-05, supports CA-F4-06

### 3.0 — Prerequisite (found during implementation): `ResultadoM303` must carry the breakdown objects

Per `design.md` SPEC-F4-03's amendment: `calcular_m303()` computes `ResultadoDevengado`/`ResultadoDeducible` but discards them, keeping only a partial `casillas` dict on `ResultadoM303`. Additive fix, Phase 2 files, both new fields default to `None`.

- [x] 3.0.1 Write failing test `test_resultado_m303_acepta_devengado_deducible_opcionales` (in `tests/fiscal/test_models.py`): constructing `ResultadoM303` without `devengado`/`deducible` still works (regression guard, matches `tests/integration/test_saldo_iva_compensar.py`'s existing direct construction); constructing it with both set makes them readable back
- [x] 3.0.2 Write failing test `test_calcular_m303_adjunta_devengado_deducible_al_resultado` (in `tests/fiscal/iva/test_calcular_m303.py` or the closest existing test module for this function): calling `calcular_m303()` with seed invoices at 21% and 4% results in `resultado.devengado.por_tipo` containing both rates, and `resultado.deducible.por_categoria` containing the seed expense categories
- [x] 3.0.3 Verify tests fail: `pytest tests/fiscal/test_models.py tests/fiscal/iva/test_calcular_m303.py -k "devengado_deducible" -v`
- [x] 3.0.4 Implement: add `devengado: ResultadoDevengado | None = None` and `deducible: ResultadoDeducible | None = None` to `ResultadoM303` in `src/fiscal/models.py`; add `resultado.devengado = devengado` and `resultado.deducible = deducible` in `src/fiscal/iva/calcular_m303.py` right after `calcular_resultado_m303()` returns
- [x] 3.0.5 Run tests — must pass: `pytest tests/fiscal/test_models.py tests/fiscal/iva/test_calcular_m303.py -v`
- [x] 3.0.6 Run the full Phase 2 fiscal suite with coverage to confirm no regression: `pytest tests/fiscal/ -v --cov=src/fiscal --cov-branch --cov-report=term-missing` — must remain 100%
- [x] 3.0.7 Second sub-fix (found while writing 3.0's tests): `ResultadoDeducible.por_categoria` is cuota-only — no base aggregate exists, but every deducible casilla group is a base+cuota pair. Write failing test `test_calcular_iva_deducible_base_por_categoria` (`tests/fiscal/test_calcular_deducible.py`) and `test_resultado_deducible_base_por_categoria_por_defecto_vacio` (`tests/fiscal/test_models.py`) per `design.md`'s second SPEC-F4-03 amendment
- [x] 3.0.8 Verify tests fail, then implement: add `base_por_categoria: dict[str, Decimal] = {}` to `ResultadoDeducible` (`src/fiscal/models.py`); compute it in `calcular_iva_deducible()` (`src/fiscal/iva/calcular_deducible.py`) with the same `porcentaje_deducible` scaling already applied to the cuota
- [x] 3.0.9 Re-run the full Phase 2 fiscal suite with coverage — must remain 100%: `pytest tests/fiscal/ -v --cov=src/fiscal --cov-branch --cov-report=term-missing`

- [x] 3.1 Write failing test `test_construir_mapa_casillas_devengado_por_tipo`: a `ResultadoM303` with 21%-only sales populates casillas 07/08/09 and leaves 01-06/150-152 unset (not zero)
- [x] 3.2 Write failing test `test_construir_mapa_casillas_devengado_multiples_tipos`: sales at both 4% and 21% populate both blocks independently
- [x] 3.3 Write failing test `test_construir_mapa_casillas_isp`: ISP amount populates casillas 12-13 only, distinct from the general-regime blocks (casuística C05)
- [x] 3.4 Write failing test `test_construir_mapa_casillas_modificacion_rectificativa`: a non-zero `base_modificacion`/`cuota_modificacion` populates casillas 14-15 as a distinct pair, and casilla 27's total still equals the arithmetic sum documented in `src/fiscal/models.py` (casuística C04)
- [x] 3.5 Write failing test `test_construir_mapa_casillas_deducible_corriente_default`: an unrecognized `categoria_gasto` key falls back to the corriente-interior default (28-29), per the Product-Owner-approved mapping table
- [x] 3.6 Write failing test `test_construir_mapa_casillas_deducible_grupos_explicitos`: categories explicitly mapped to inversión (30-31), importación (32-35), intracomunitario (36-37), rectificación (40-41) land in the correct casillas, not all folded into 28-29
- [x] 3.7 Write failing test `test_construir_mapa_casillas_resultado_a_ingresar`, `_a_compensar`, `_a_devolver`, `_sin_actividad`: each `tipo_resultado` populates the correct 46/66/69/70/71/72/110 subset
- [x] 3.8 Write failing test `test_construir_mapa_casillas_bloque_informativo`: casillas 59 (C11 intracomunitaria), 60 (C10 exportación), 61-63 populate only when > 0
- [x] 3.9 Verify tests fail: `pytest tests/rpa/test_casilla_map.py -v`
- [x] 3.10 Implement `src/rpa/casilla_map.py` (`construir_mapa_casillas`, `TABLA_CASILLA_DEDUCIBLE`) per `design.md` SPEC-F4-03 — pure function, no I/O, delegates all arithmetic to already-computed `ResultadoM303`/`ResultadoDevengado`/`ResultadoDeducible` fields
- [x] 3.11 Run tests — must pass: `pytest tests/rpa/test_casilla_map.py -v`
- [x] 3.12 Add a `test_construir_mapa_casillas_no_reimplementa_aritmetica_fiscal` regression test: asserts every value in the returned map is either copied verbatim from a `ResultadoM303`/`ResultadoDevengado`/`ResultadoDeducible` field or a documented pass-through, proving no new `+`/`-`/`*` fiscal arithmetic was introduced in `casilla_map.py`

## 4. Backend: Cl@ve Móvil (QR) Authentication (SPEC-F4-02)

Acceptance criteria: CA-F4-01

### 4.0 — Design correction (found via Product Owner review, before further coding)

The original Task 4 (4.1-4.7 below) implemented a text-entry "Cl@ve PIN" flow (NIF + a typed PIN submitted by the RPA), which does not match how AEAT's real Modelo B authentication works — it's a QR scanned with the Cl@ve Móvil phone app, the RPA never sees or types a PIN. Per `CLAUDE.md` §7, `design.md` SPEC-F4-02 was amended first (Cl@ve Móvil QR primary flow, SMS PIN fallback documented as an MVP limitation, Modelo A/certificate unchanged as out-of-scope V2). This section replaces the original 4.1-4.7 with the corrected flow — the original subtasks are struck through in intent, not left as stale duplicates.

- [x] 4.0.1 Write failing unit test `test_capturar_qr_clave_retorna_screenshot_del_elemento`: `capturar_qr_clave(page, selectores)` returns exactly what `page.locator(qr_elemento).screenshot()` returns
- [x] 4.0.2 Write failing unit test `test_autenticar_clave_movil_captura_qr_y_llama_notificacion_fn`: the QR bytes are passed to the injected `notificacion_fn` callback, unmodified
- [x] 4.0.3 Write failing unit test `test_autenticar_clave_movil_espera_redireccion_con_timeout_120s`: `page.wait_for_url()` is called with `selectores["clave_movil"]["url_autenticada_patron"]` and `timeout=120_000`
- [x] 4.0.4 Write failing unit test `test_autenticar_clave_movil_verifica_nif_coincide`: a successful flow where the authenticated NIF matches `perfil.nif` returns `SesionAEAT(activa=True, ...)`
- [x] 4.0.5 Write failing unit test `test_autenticar_clave_movil_nif_no_coincide_lanza_error`: a mismatch raises `AutenticacionError`, and `SesionAEAT` is never returned
- [x] 4.0.6 Write failing unit test `test_sesion_expira_tras_10_minutos` / `test_sesion_dentro_de_10_minutos_no_lanza_error`: unchanged from the original design — `SesionAEAT`'s 10-minute timeout logic is untouched by the QR-vs-PIN correction
- [x] 4.0.7 Verify tests fail: `pytest tests/rpa/aeat/test_autenticacion.py -v -m "not integration"`
- [x] 4.0.8 Implement `src/rpa/aeat/autenticacion.py`: remove `autenticar_clave_pin`; add `capturar_qr_clave(page, selectores) -> bytes` and `autenticar_clave_movil(nif, page, selectores, notificacion_fn) -> SesionAEAT` per `design.md` SPEC-F4-02's amendment. `SesionAEAT`/`AutenticacionError`/`SesionExpiradaError`/`verificar_sesion_activa` unchanged.
- [x] 4.0.9 Update `src/rpa/selectors/aeat_m303.yml`: replace `clave_pin` with `clave_movil` (`boton_acceso`, `qr_elemento`, `url_autenticada_patron`, `nif_autenticado_label`)
- [x] 4.0.10 Run tests — must pass: `pytest tests/rpa/aeat/test_autenticacion.py -v -m "not integration"`
- [x] 4.0.11a **QR element selector verified: `img#imgQRAcceso` on the live AEAT site.** Product Owner inspected the real AEAT DOM and confirmed `qr_elemento`'s selector in `aeat_m303.yml`. This verifies one selector, not the full flow — see 4.0.11 below, which remains unchecked.
- [ ] 4.0.11 Update `test_autenticar_clave_pin_sesion_real` → `test_autenticar_clave_movil_sesion_real`: prompts for real NIF only (no PIN — the user scans the QR with their own phone), launches a real headed browser, drives the real QR flow, waits up to 120s for the redirect. **Manual Product Owner execution only** — the agent writes the test, marks it `@pytest.mark.integration`, and leaves it unchecked `[ ]` until the Product Owner confirms execution of the *complete* session (browser open → QR scan → authenticated-NIF confirmation). The QR selector itself is already verified (4.0.11a); what remains is the end-to-end session run whenever the Product Owner has time to sit through a full Cl@ve Móvil confirmation.

~~4.1-4.7 (original Cl@ve PIN text-entry flow, superseded by 4.0 above)~~

## 5. Backend: AEAT Stub Fixtures (SPEC-F4-06)

Acceptance criteria: prerequisite for Tasks 6-8's unit tests (no real AEAT calls)

- [x] 5.1 Implement `tests/rpa/_stubs_aeat.py` with the four fixtures: `respuesta_exito()`, `respuesta_validacion_error()`, `respuesta_periodo_ya_presentado()`, `respuesta_aeat_no_disponible()`
- [x] 5.2 Write a smoke test `test_stubs_aeat_shape` asserting each fixture returns the fields the form-filling/error-handling code expects to parse
- [x] 5.3 Run test — must pass: `pytest tests/rpa/test_stubs_aeat.py -v`

## 6. Backend: Form Navigation, Filling, Validation, Submission (SPEC-F4-04)

Acceptance criteria: CA-F4-02, CA-F4-03, CA-F4-04, CA-F4-05, CA-F4-06

- [x] 6.1 Write failing test `test_navegar_a_modelo_303_verifica_prellenado`: given a mocked page exposing pre-filled NIF/nombre matching `perfil.nif`, navigation succeeds; a mismatch raises an error before any casilla is touched
- [x] 6.2 Write failing test `test_rellenar_pagina_identificacion_marca_regimen_general_y_criterio_caja`: `perfil.regimen_iva == "caja"` checks the criterio-de-caja box; otherwise it's left unchecked
- [x] 6.3 Write failing test `test_rellenar_pagina_devengado_deja_en_blanco_tipos_no_aplicables`: a mapa_casillas with only 21% populated results in no writes to the 4%/10%/0% fields (not zero-writes) — regression guard for T04-20's explicit warning
- [x] 6.4 Write failing test `test_rellenar_pagina_devengado_detecta_discrepancia_casilla_27` (using `respuesta_validacion_error`-style stub returning a different AEAT-computed casilla 27): a difference > 0.02 € raises `DiscrepanciaResultadoError` (T04-E3) before proceeding to the deducible page
- [x] 6.5 Write failing test `test_rellenar_pagina_devengado_tolera_diferencia_redondeo`: a difference ≤ 0.02 € proceeds without error
- [x] 6.6 Write failing test `test_rellenar_pagina_deducible_detecta_discrepancia_casilla_45`: same discrepancy check against casilla 45
- [x] 6.7 Write failing test `test_rellenar_pagina_resultado_a_ingresar_domiciliacion`, `_nrc`, `_tarjeta_detiene_flujo`: domiciliación writes IBAN + fecha; NRC validates format (22 alphanumeric) before writing and raises on malformed input (T04-E2 precondition); `tarjeta` returns a state requiring manual completion and writes nothing to card fields
- [x] 6.8 Write failing test `test_rellenar_pagina_resultado_a_compensar`, `_a_devolver_4t`, `_sin_actividad`: each path writes the correct casilla subset per SPEC-F4-03's result-block table
- [x] 6.9 Write failing test `test_rellenar_bloque_informativo_solo_valores_positivos`: casillas 59-63 are written only when > 0
- [x] 6.10 Write failing test `test_validar_formulario_bloquea_si_aeat_reporta_errores` (using `respuesta_validacion_error` stub): a non-empty AEAT error list is surfaced and the caller is signaled not to proceed to `presentar()`
- [x] 6.11 Write failing test `test_presentar_verifica_sesion_fresca_antes_de_enviar`: a `SesionAEAT` older than 10 minutes raises `SesionExpiradaError` instead of submitting
- [x] 6.12 Write failing test `test_presentar_captura_csv_nrc_timestamp` (using `respuesta_exito` stub): a successful submission returns `PresentacionResult(csv, nrc, timestamp)`
- [x] 6.13 Verify tests fail: `pytest tests/rpa/aeat/test_m303_form.py -v`
- [x] 6.14 Implement `src/rpa/aeat/m303_form.py` (`navegar_a_modelo_303`, `rellenar_pagina_identificacion`, `rellenar_pagina_devengado`, `rellenar_pagina_deducible`, `rellenar_pagina_resultado`, `rellenar_bloque_informativo`, `validar_formulario`, `presentar`, `DiscrepanciaResultadoError`) per `design.md` SPEC-F4-04
- [x] 6.15 Run tests — must pass: `pytest tests/rpa/aeat/test_m303_form.py -v`

## 7. Backend: RPA Error Handling — T04-E1 through T04-E4

Acceptance criteria: CA-F4-07, CA-F4-08

- [x] 7.1 Write failing test `test_error_e1_periodo_ya_presentado_existe_en_bd`: given a `presentacion` row already exists for `(user_id, ejercicio, periodo)`, the worker surfaces its CSV/justificante and never calls `presentar()`
- [x] 7.2 Write failing test `test_error_e1_periodo_ya_presentado_no_existe_en_bd`: AEAT reports an existing declaration but no local `presentacion` row exists → `error_code='periodo_ya_presentado_externo'`, flagged for manual review
- [x] 7.3 Write failing test `test_error_e4_fallo_envio_guarda_screenshot_y_reintenta`: a submission failure (using `respuesta_aeat_no_disponible` stub) saves a screenshot to Supabase Storage, sets `error_code`, and the retry path re-authenticates from scratch rather than resubmitting against the stale session
- [x] 7.4 Covered by Task 9.3's integration test `test_procesar_presentacion_idempotente_si_ya_presentado` — the idempotent-retry guard is only meaningfully testable at the full worker-orchestration level (Task 9), so this scenario is verified there rather than duplicated here.
- [x] 7.5 Verify tests fail: `pytest tests/rpa/aeat/test_errores_rpa.py -v`
- [x] 7.6 Implement the T04-E1/T04-E4 handling in `src/workers/rpa_worker.py` (existing-declaration precheck, screenshot-on-failure, idempotent retry) per `design.md` SPEC-F4-04's error table
- [x] 7.7 Run tests — must pass: `pytest tests/rpa/aeat/test_errores_rpa.py -v`

## 8. Backend: Justificante Download, Verification, Storage (SPEC-F4-05)

Acceptance criteria: CA-F4-09

- [x] 8.1 Write failing test `test_descargar_justificante_verifica_campos_coinciden`: a justificante PDF whose NIF/modelo/ejercicio/periodo/CSV/resultado all match the just-submitted values passes verification
- [x] 8.2 Write failing test `test_descargar_justificante_detecta_discrepancia`: a mismatch (e.g. wrong período in the extracted PDF text) raises `error_code='justificante_no_coincide'` instead of silently accepting the file
- [x] 8.3 Write failing test `test_descargar_justificante_sube_a_storage_path_correcto`: the uploaded path follows `justificantes/{user_id}/{ejercicio}_{periodo}.pdf`, mirroring Phase 3's `{tipo}/{user_id}/{filename}` convention
- [x] 8.4 Write failing test `test_descargar_justificante_actualiza_presentacion`: on success, `presentacion.estado='presentado'`, `csv_aeat`, `nrc` (if applicable), `justificante_path` are all updated
- [x] 8.5 Verify tests fail: `pytest tests/rpa/aeat/test_justificante.py -v`
- [x] 8.6 Implement `src/rpa/aeat/justificante.py` (`descargar_justificante`, PDF text-layer parsing, Supabase Storage upload) per `design.md` SPEC-F4-05
- [x] 8.7 Run tests — must pass: `pytest tests/rpa/aeat/test_justificante.py -v`

## 9. Backend: ARQ Worker Integration

Acceptance criteria: ties CA-F4-01 through CA-F4-09 together into one end-to-end flow

### 9.0 — Amendment (Task 4.0's QR correction propagated here)

`ejecutar_presentacion`/`procesar_presentacion` originally took a `pin: str` parameter and called `autenticar_clave_pin`. Per Task 4.0's design correction, replaced with: no `pin` parameter (the RPA never receives one); a new `guardar_qr_clave(client, user_id, ejercicio, periodo, qr_bytes) -> str` helper uploads the QR to Supabase Storage (`qr-clave/{user_id}/{ejercicio}_{periodo}.png`); `ejecutar_presentacion` builds an internal `notificacion_fn` closure over it and calls `autenticar_clave_movil`.

- [x] 9.0.1 Write failing test `test_guardar_qr_clave_sube_a_storage_path_correcto`
- [x] 9.0.2 Write failing test `test_ejecutar_presentacion_flujo_exito_guarda_qr_en_storage`
- [x] 9.0.3 Implement `guardar_qr_clave` and wire the `notificacion_fn` closure into `ejecutar_presentacion`; remove `pin` from `ejecutar_presentacion`/`procesar_presentacion`
- [x] 9.0.4 Run full worker suite — must pass: `pytest tests/workers/ -v -m "not integration" --cov=src.workers --cov-branch --cov-report=term-missing` (100%)

- [x] 9.1 Write failing integration test `test_procesar_presentacion_flujo_completo_exito` (mocked Playwright throughout, using the Task 5 stubs): a `presentacion` row in `estado='confirmado'` transitions through `presentando` to `presentado`, with `csv_aeat`/`justificante_path` populated
- [x] 9.2 Write failing integration test `test_procesar_presentacion_flujo_error_marca_estado_error`: any of the T04-E1..E4 paths results in `estado='error'` with a populated `error_code`, never leaves the row stuck in `presentando`
- [x] 9.3 Write failing integration test `test_procesar_presentacion_idempotente_si_ya_presentado`: re-enqueuing a job for a row already `estado='presentado'` is a no-op — no second AEAT session is opened
- [x] 9.4 Verify tests fail: `pytest tests/workers/test_rpa_worker.py -v`
- [x] 9.5 Implement `src/workers/rpa_worker.py::procesar_presentacion` (ARQ job registration, state-transition idempotency guard) per `design.md`
- [x] 9.6 Run tests — must pass: `pytest tests/workers/test_rpa_worker.py -v`
- [x] 9.7 Run full suite with coverage — must remain 100% on `src/fiscal/` (unchanged) and achieve full coverage on `src/rpa/` and `src/workers/` except lines explicitly requiring a live AEAT session: `pytest tests/ -v --cov=src/fiscal --cov=src/rpa --cov=src/workers --cov-branch --cov-report=term-missing`

## 10. Unit Test and DB Verification Report (MANDATORY)

- [x] 10.1 Agent executes the full suite itself (never delegates): `pytest tests/ -v --cov=src/fiscal --cov=src/rpa --cov=src/workers --cov-branch --cov-report=term-missing`
- [x] 10.2 Agent verifies no new migration was needed (per `design.md`, `presentacion`'s existing schema already covers F4) by confirming `mcp__.../list_migrations` (or equivalent) shows no new file, or explicitly stating why one was needed if the casilla-storage design changed during implementation
- [x] 10.3 Write the report to `specs/rpa-aeat/reports/YYYY-MM-DD-step-10-unit-test-and-db-verification.md` per `docs/openspec-tasks-mandatory-steps.md`'s template, including: full pytest summary, coverage table, confirmation that `pytest -m "not integration"` excludes every real-AEAT test, and the DB-state check from 10.2

## 11. Manual Endpoint Testing with curl (NOT APPLICABLE THIS PHASE)

- [x] 11.1 N/A — no API endpoints are created or modified this phase; F4 is the RPA module + ARQ worker only, `/api/proceso/p04/confirmar` and related endpoints are Phase 5's scope (confirmed by reading `docs/api-spec.yml` and `src/api/routers/`). Explicitly marked N/A, not silently omitted, mirroring Phase 1/2/3 precedent.

## 12. Frontend: E2E Testing with Playwright (NOT APPLICABLE THIS PHASE)

- [x] 12.1 N/A — no frontend exists yet (Phase 5 scope). Note: this change's own extensive use of Playwright is for *AEAT automation*, not for testing our own UI — see the distinction called out at the top of this file. Explicitly marked N/A, not silently omitted.

## 13. Update Technical Documentation (MANDATORY)

- [x] 13.1 Update `docs/backend-standards.md` if the final `src/rpa/`/`src/workers/` layout differs in any way from the Project-structure block already there
- [x] 13.2 Update `docs/development_guide.md` with any new environment variables (e.g. AEAT sandbox/test credentials needed for `@pytest.mark.integration` tests, ARQ/Redis connection settings if not already documented)
- [x] 13.3 Update `CHANGELOG.md` with what Phase 4 delivered
- [x] 13.4 Note explicitly in documentation that Phase 5 (API + frontend) is what actually enqueues `procesar_presentacion` jobs — this phase implements the worker function and its registration only, not the enqueueing endpoint
- [x] 13.5 Confirm the documentation update references `TABLA_CASILLA_DEDUCIBLE` (per `design.md` SPEC-F4-03) as the Product-Owner-approved mapping, and notes that future category additions are made in that data file, never in `m303_form.py`

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
- Task 4.0.11 (`test_autenticar_clave_movil_sesion_real`) is written and marked `@pytest.mark.integration`, but left unchecked `[ ]` pending manual execution by the Product Owner with a real NIF and their own phone's Cl@ve Móvil app — it must not be marked `[x]` by the agent under any circumstance. The QR selector itself (`img#imgQRAcceso`) is separately verified (4.0.11a) — that is not the same as a completed end-to-end session.
