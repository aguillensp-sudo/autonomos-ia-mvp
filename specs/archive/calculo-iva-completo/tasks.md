# Tasks: calculo-iva-completo

`openspec/config.yaml` read: yes. `docs/openspec-tasks-mandatory-steps.md` read: yes. Branch naming: `feature/calculo-iva-completo` per config. Agent: `backend_developer` (model `claude-sonnet-4-6` per `openspec/config.yaml`; GLM-5.2 via DeepInfra once the harness exists). No frontend work in this change — Step 13 (E2E Playwright) is not applicable and is explicitly marked skipped, not omitted, per the Phase 1 precedent.

## 0. Setup: Create Feature Branch (MANDATORY — FIRST STEP)

- [x] 0.1 Create feature branch `feature/calculo-iva-completo` from `main`
- [x] 0.2 Verify branch creation: `git branch --show-current`

## 1. Backend: Schema Migration — Additive Columns

Acceptance criteria: enables CA-F2-04, CA-F2-07 (see `design.md` "Schema additions required this phase")

- [x] 1.1 Create migration adding `factura_emitida.es_rectificativa BOOLEAN DEFAULT FALSE`
- [x] 1.2 Create migration adding `factura_emitida.factura_original_id UUID REFERENCES factura_emitida(id)`
- [x] 1.3 Create migration adding `factura_emitida.cliente_es_empresario_ue BOOLEAN DEFAULT FALSE`
- [x] 1.4 Apply migrations to local Supabase: `supabase migration up`
- [x] 1.5 Verify columns exist and Phase 1 seed data / RLS tests still pass unaffected

## 2. Backend: Full Deductibility Table — 22 Categories — TDD

Acceptance criteria: CA-F2-01

- [x] 2.1 Write failing test `test_tabla_deducibilidad_22_categorias.py` — one assertion per category from `design.md` SPEC-F2-01, verifying `porcentaje` and `descripcion` match exactly
- [x] 2.2 Write failing tests for the 4 critical cases called out in CA-F2-01: `test_calcular_iva_deducible_vehiculo_estandar` (50%/0%), `test_calcular_iva_deducible_telefono_mixto` (50/50, already exists from Phase 1 — extend if needed), `test_calcular_iva_deducible_comida_requiere_confirmacion`, `test_calcular_iva_deducible_cuota_reta` (already exists — verify still passes). **Also add `test_calcular_iva_deducible_suministros_domicilio_proporcional`**: per `design.md` SPEC-F2-01, this category is a rule, not a fixed percentage — the test must assert (a) `requiere_confirmacion=True` on the resulting classification, and (b) the engine uses the invoice's own `porcentaje_deducible` field (set at ingestion from m² despacho/m² vivienda) rather than any fixed value looked up from `TABLA_DEDUCIBILIDAD` for this category.
- [x] 2.3 Verify tests fail: `pytest tests/fiscal/test_tabla_deducibilidad_22_categorias.py tests/fiscal/test_calcular_deducible.py -v`
- [x] 2.4 Replace the 5-category `TABLA_DEDUCIBILIDAD` in `src/fiscal/iva/tabla_deducibilidad.py` with all 22 categories per SPEC-F2-01, each `DeducibilidadRule` citing its legal source from the table
- [x] 2.5 Run tests — all must pass: `pytest tests/fiscal/test_tabla_deducibilidad_22_categorias.py tests/fiscal/test_calcular_deducible.py -v`

## 3. Backend: ISP Module — TDD

Acceptance criteria: CA-F2-02, CA-F2-05

- [x] 3.1 Write failing tests for `detectar_isp()`: `test_detectar_isp_nif_none`, `test_detectar_isp_nif_vacio`, `test_detectar_isp_nif_no_espanol` (the 3 mandatory cases per `openspec/config.yaml` fiscal_integrity_checks), plus `test_detectar_isp_google_ireland_sin_nif_es`, `test_detectar_isp_google_spain_con_nif_es` (must NOT trigger ISP), `test_detectar_isp_adobe_sin_nif_es`, `test_detectar_isp_adobe_con_nif_es` (`ESB61653893`, must NOT trigger)
- [x] 3.2 Write failing test `test_calcular_isp_efecto_neto_cero` (100% deductible service → net 0) and `test_calcular_isp_efecto_neto_no_cero` (partially deductible service)
- [x] 3.3 Verify tests fail: `pytest tests/fiscal/test_calcular_isp.py -v`
- [x] 3.4 Implement `src/fiscal/iva/calcular_isp.py`: `detectar_isp()`, `calcular_isp()`, `ResultadoISP`, and the known-supplier data table (Google Ireland, Meta Platforms Ireland, Adobe Systems, Microsoft Ireland) per `design.md` SPEC-F2-02
- [x] 3.5 Run tests — all must pass: `pytest tests/fiscal/test_calcular_isp.py -v`

## 4. Backend: Bloque Informativo (Casillas 59-63) — TDD

Acceptance criteria: CA-F2-07

- [x] 4.1 Write failing tests: `test_calcular_bloque_informativo_casilla_59_venta_ue_bien`, `_casilla_60_exportacion`, `_casilla_62_servicio_b2b_ue`, `_casilla_61_default_cero`
- [x] 4.2 Verify tests fail: `pytest tests/fiscal/test_calcular_bloque_informativo.py -v`
- [x] 4.3 Implement `src/fiscal/iva/calcular_bloque_informativo.py` per `design.md` SPEC-F2-03, using the new `cliente_es_empresario_ue` column to distinguish casilla 59 from 62
- [x] 4.4 Run tests — all must pass: `pytest tests/fiscal/test_calcular_bloque_informativo.py -v`
- [x] 4.5 Document in the task report that real-time VIES validation is explicitly deferred (per `design.md` SPEC-F2-03 "Deferred" note) — this is not a silent omission

## 5. Backend: Facturas Rectificativas Routing — TDD

Acceptance criteria: CA-F2-04

- [x] 5.1 Write failing test `test_calcular_devengado_rectificativa_mismo_trimestre` (reduces devengado directly, no casilla 14-15)
- [x] 5.2 Write failing test `test_calcular_devengado_rectificativa_trimestre_diferente` (routes to `base_modificacion`/`cuota_modificacion`, casillas 14-15)
- [x] 5.3 Verify tests fail: `pytest tests/fiscal/test_calcular_devengado.py -v`
- [x] 5.4 Extend `ResultadoDevengado` with `base_modificacion`/`cuota_modificacion` fields; extend `calcular_iva_devengado()` to branch on `es_rectificativa` + `factura_original_id.periodo_declarado` comparison, per `design.md` SPEC-F2-04
- [x] 5.5 Run tests — all must pass, including Phase 1's existing `calcular_devengado` tests (no regression): `pytest tests/fiscal/test_calcular_devengado.py -v`

## 6. Backend: Criterio de Caja Filter — TDD

Acceptance criteria: casuística C06 (CA-F2-09)

- [x] 6.1 Write failing test `test_filtrar_criterio_caja_excluye_no_cobrada` (issued but not collected → excluded from devengado)
- [x] 6.2 Write failing test `test_filtrar_criterio_caja_incluye_cobrada_en_periodo`
- [x] 6.3 Write failing test `test_filtrar_criterio_caja_regimen_general_no_filtra` (regimen_iva='general' → passthrough, Phase 1 behavior unchanged)
- [x] 6.4 Verify tests fail: `pytest tests/fiscal/test_criterio_caja.py -v`
- [x] 6.5 Implement `filtrar_por_criterio_caja()` in `src/fiscal/iva/criterio_caja.py` per `design.md` SPEC-F2-05
- [x] 6.6 Run tests — all must pass: `pytest tests/fiscal/test_criterio_caja.py -v`

## 7. Backend: `saldo_iva_compensar` Real Persistence — TDD (Integration)

Acceptance criteria: CA-F2-08

- [x] 7.1 Write failing integration test `test_actualizar_saldo_iva_compensar_persiste_a_compensar` against local Supabase: 1T with -300€ result persists saldo=300
- [x] 7.2 Write failing integration test `test_leer_saldo_compensar_recupera_valor_persistido`: 2T reads casilla 110 = 300€ from the same row
- [x] 7.3 Write failing integration test `test_actualizar_saldo_iva_compensar_a_ingresar_resetea_a_cero`
- [x] 7.4 Verify tests fail: `pytest tests/integration/test_saldo_iva_compensar.py -v`
- [x] 7.5 Implement `leer_saldo_compensar()` and `actualizar_saldo_iva_compensar()` in `src/fiscal/iva/actualizar_saldo_iva_compensar.py` per `design.md` SPEC-F2-06 (upsert on `(user_id, ejercicio)` unique constraint)
- [x] 7.6 Run tests — all must pass: `pytest tests/integration/test_saldo_iva_compensar.py -v`

## 8. Backend: `calcular_m303()` End-to-End Orchestrator — TDD

Acceptance criteria: CA-F2-10

- [x] 8.1 Write failing test `test_calcular_m303_perfil_1_solo_servicios` — full pipeline against seed profile 1, tolerance ±0.02€ vs. manually pre-calculated value
- [x] 8.2 Write failing test `test_calcular_m303_perfil_2_mixto_con_gastos`
- [x] 8.3 Write failing test `test_calcular_m303_perfil_3_con_isp`
- [x] 8.4 Verify tests fail: `pytest tests/fiscal/test_calcular_m303_end_to_end.py -v`
- [x] 8.5 Implement `calcular_m303()` in `src/fiscal/iva/calcular_m303.py` per `design.md` SPEC-F2-07, wiring together all functions from tasks 2-7 in the documented order
- [x] 8.6 Run tests — all 3 profiles must match manual calculation within tolerance: `pytest tests/fiscal/test_calcular_m303_end_to_end.py -v`

## 9. Backend: Remaining Casuísticas Coverage (Hoja 5)

Acceptance criteria: CA-F2-03, CA-F2-06, CA-F2-09

- [x] 9.1 Write and pass `test_c01_sin_actividad` (already covered by Phase 1's `calcular_resultado_m303` sin_actividad test — verify it still applies with `calcular_m303()`)
- [x] 9.2 **C02 rescoped — see `design.md` "Casuística C02 — scope clarification".** Not a fiscal engine concern: detecting multiple pending quarters requires querying the `presentacion` table's filing history, which belongs to the agent/orchestration layer (Phase 3), not `src/fiscal/`. This phase's test verifies only that `calcular_m303()` processes one quarter correctly even when prior quarters exist in `presentacion` with `estado='pendiente'`. Add a `# TODO: Phase 3` comment in the test file header noting that the alert/detection logic itself is deferred.
- [x] 9.3 Write and pass `test_c03_retencion_irpf_no_afecta_iva` (CA-F2-03): identical invoice with/without `retencion_irpf` produces identical `total_devengado`
- [x] 9.4 Write and pass `test_c07_prorrata_alerta_no_calculo` — mixed-activity profile triggers an alert/flag; explicitly does NOT attempt the proportional calculation (per `design.md` scope note — `MVP: ALERTAR`)
- [x] 9.5 Write and pass `test_c08_devolucion_4t_vs_compensacion` (CA-F2-06): 4T negative result with `solicita_devolucion=True` → casilla 72; with compensación → casilla 110 propagates to next quarter's `saldo_iva_compensar`
- [x] 9.6 Confirm C09 (autoliquidación rectificativa de presentación ya realizada) is explicitly out of scope — add a one-line note in the test file header, do not write a test for it (it belongs to a future P04-R change per `feature.md`)
- [x] 9.7 Confirm C10 (exportación fuera UE) and C11 (venta B2B UE) are covered by Task 4's bloque informativo tests — cross-reference, do not duplicate

## 10. Backend: Review and Update Existing Unit Tests (MANDATORY)

- [x] 10.1 Review all Phase 1 tests in `tests/fiscal/` for regressions caused by the `ResultadoDevengado` field additions (task 5.4) — run the full Phase 1 suite and confirm no unexpected failures
- [x] 10.2 Update any Phase 1 test that constructed a `ResultadoDevengado` positionally (rather than by keyword) if the new optional fields break it

## 11. Backend: Run Unit Tests and Verify Database State (MANDATORY — AGENT MUST EXECUTE)

Acceptance criteria: coverage requirement from `openspec/config.yaml` (100% on `src/fiscal/`)

- [x] 11.1 Capture pre-test Supabase state (row counts for all 6 tables, plus the 3 new columns' default values on existing rows)
- [x] 11.2 Run targeted tests per new module (repeat the pattern from Phase 1's report for each of: `calcular_isp`, `calcular_bloque_informativo`, `criterio_caja`, `actualizar_saldo_iva_compensar`, `calcular_m303`)
- [x] 11.3 Run full suite: `pytest tests/ -v --cov=src/fiscal --cov-report=term-missing`
- [x] 11.4 Verify coverage on `src/fiscal/` is exactly 100%, no uncovered branches (including the new rectificativa/ISP/criterio-caja branches — these are exactly the kind of conditional logic branch coverage must catch)
- [x] 11.5 Verify post-test database state: `saldo_iva_compensar` test rows from task 7 are either cleaned up or documented as intentional (per Phase 1's precedent of leaving seed/test data in place with justification)
- [x] 11.6 Create report `specs/calculo-iva-completo/reports/YYYY-MM-DD-step-11-unit-test-and-db-verification.md`
- [x] 11.7 Mark this step complete only after 100% coverage is confirmed and the report exists

## 12. Backend: Manual Endpoint Testing with curl (MANDATORY per config — scoped to regression this phase)

Acceptance criteria: no new endpoints this phase; verifies no regression on Phase 1's endpoints

- [x] 12.1 Start backend server: `uvicorn src.api.main:app --reload --port 8000`
- [x] 12.2 Verify health: `curl http://localhost:8000/health` — expect `{"status": "ok", "db": "ok", "redis": "not_configured"}`
- [x] 12.3 Re-run Phase 1's `POST`/`GET /api/proceso/p04/facturas` curl checks (from `specs/archive/fiscal-engine-fundamentos/reports/2026-07-03-step-12-curl-testing.md`) to confirm the 3 new nullable/default columns on `factura_emitida` do not break existing request/response handling
- [x] 12.4 Note explicitly in the report: this change adds no new API endpoint (the new fiscal functions are consumed by `calcular_m303()` only, not yet wired to a route — that wiring is Phase 5 scope per the original roadmap)
- [x] 12.5 Create report `specs/calculo-iva-completo/reports/YYYY-MM-DD-step-12-curl-testing.md`

## 13. Frontend: E2E Testing with Playwright (NOT APPLICABLE THIS PHASE)

- [x] 13.1 No frontend exists yet and no endpoint changed — explicitly skipped, not silently omitted, mirroring Phase 1's precedent.

## 14. Update Technical Documentation (MANDATORY)

- [x] 14.1 Update `docs/data-model.md` with the 3 new `factura_emitida` columns (`es_rectificativa`, `factura_original_id`, `cliente_es_empresario_ue`)
- [x] 14.2 Update `docs/backend-standards.md` project structure section if new file paths under `src/fiscal/iva/` aren't already implied by the existing pattern
- [x] 14.3 Update `CHANGELOG.md` with what Phase 2 delivered
- [x] 14.4 Note in documentation that VIES real-time validation (casuística C11) and full prorrata calculation (C07) and P04-R (C09) remain explicitly deferred, per `design.md`

## Exit criteria (Orchestrator evaluates before accepting this change)

- All tasks above checked `[x]`
- `pytest tests/ --cov=src/fiscal --cov-branch` reports 100% line and branch coverage
- Both report files exist under `specs/calculo-iva-completo/reports/`
- ISP detection verified for all 3 mandatory input cases (`None`, `''`, non-ES)
- `saldo_iva_compensar` read/write verified against real local Supabase, not just a function parameter
- `calcular_m303()` end-to-end matches manual calculation for all 3 seed profiles within ±0.02€
- No out-of-scope items (C09/P04-R, full VIES integration, full prorrata, anything from `openspec/config.yaml` → `out_of_scope`) implemented
