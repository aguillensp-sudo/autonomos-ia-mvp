# Tasks: fiscal-engine-fundamentos

`openspec/config.yaml` read: yes. `docs/openspec-tasks-mandatory-steps.md` read: yes. Branch naming: `feature/{change-name}` per config. Agent: `backend_developer` (model `claude-sonnet-4-6` per `openspec/config.yaml`; GLM-5.2 via DeepInfra once the harness exists). No frontend work in this change — Step N+3 (E2E Playwright) is not applicable and is explicitly marked skipped, not omitted.

## 0. Setup: Create Feature Branch (MANDATORY — FIRST STEP)

- [x] 0.1 Create feature branch `feature/fiscal-engine-fundamentos` from `main`
- [x] 0.2 Verify branch creation: `git branch --show-current`

## 1. Backend: Supabase Schema Migrations
Acceptance criteria: CA-F1-01, CA-F1-03

- [x] 1.1 Create migration for `perfil_fiscal` per `docs/data-model.md`
- [x] 1.2 Create migration for `factura_emitida` with indexes `idx_factura_emitida_user_fecha`, `idx_factura_emitida_periodo`
- [x] 1.3 Create migration for `factura_recibida` with index `idx_factura_recibida_categoria`
- [x] 1.4 Create migration for `presentacion` with unique index `(user_id, proceso, ejercicio, periodo)`
- [x] 1.5 Create migration for `saldo_iva_compensar` with unique index `(user_id, ejercicio)`
- [x] 1.6 Create migration for `alerta` with index `idx_alerta_fecha`
- [x] 1.7 Run `supabase db push` and verify all 6 tables exist in Supabase Studio
- [x] 1.8 `EXPLAIN ANALYZE` a representative query against `factura_emitida` and `presentacion` to confirm index usage

## 2. Backend: RLS Policies
Acceptance criteria: CA-F1-02

- [x] 2.1 Enable RLS and add `user_id = auth.uid()` policy on all 6 tables (included in the migrations above — verify explicitly)
- [x] 2.2 Create 2 test users (A, B) in the test Supabase project
- [x] 2.3 Write and run integration test: user B cannot `SELECT` user A's `factura_emitida` rows
- [x] 2.4 Write and run integration test: user B cannot `SELECT` user A's `presentacion` rows

## 3. Backend: Pydantic Models — TDD
Acceptance criteria: CA-F1-04

- [x] 3.1 Write failing tests: `test_factura_emitida_tipo_iva_invalido`, `test_factura_emitida_nif_invalido`, `test_factura_emitida_fecha_futura`, plus 2 more invalid-input cases (5 total, per CA-F1-04)
- [x] 3.2 Verify tests fail: `pytest tests/fiscal/test_models.py -v`
- [x] 3.3 Implement `PerfilFiscal`, `FacturaEmitida`, `FacturaRecibida`, `Presentacion`, `SaldoIVACompensar`, `ResultadoM303` in `src/fiscal/models.py`
- [x] 3.4 Implement NIF/NIE format validator and future-date validator
- [x] 3.5 Run tests — all 5 must now pass with the expected `ValidationError`: `pytest tests/fiscal/test_models.py -v`

## 4. Backend: Seed Data
Acceptance criteria: CA-F1-05

- [x] 4.1 Write `tests/fixtures/facturas.py` with the 3 autónomo profiles (solo servicios, mixto con gastos, con ISP)
- [x] 4.2 Write `scripts/seed_data.py` to load fixtures into the test Supabase project
- [x] 4.3 Run the seed script and verify via `SELECT COUNT(*)`: ≥10 `factura_emitida` (rates 0/10/21%), 8 `factura_recibida` (corriente/inversión/ISP), ≥1 with `retencion_irpf > 0`

## 5. Backend: `calcular_iva_devengado` — TDD
Acceptance criteria: CA-F1-06

- [x] 5.1 Write failing tests against manually pre-calculated values for the 3 seed profiles: `test_calcular_iva_devengado_multiples_tipos`
- [x] 5.2 Verify tests fail: `pytest tests/fiscal/test_calcular_devengado.py -v`
- [x] 5.3 Implement `calcular_iva_devengado` in `src/fiscal/iva/calcular_devengado.py` (Art. 92 LIVA in docstring)
- [x] 5.4 Run tests — output must match manual calculation exactly: `pytest tests/fiscal/test_calcular_devengado.py -v`

## 6. Backend: `calcular_iva_deducible` + Minimal Deductibility Table — TDD
Acceptance criteria: CA-F1-07

- [x] 6.1 Write `src/fiscal/iva/tabla_deducibilidad.py` as a data dict: vehículo (50%), software (100%), comida (0% default), teléfono mixto (50%), cuota RETA (0% IVA) — 5 categories minimum
- [x] 6.2 Write failing tests: `test_calcular_iva_deducible_vehiculo_uso_mixto`, `test_calcular_iva_deducible_software_profesional`, `test_calcular_iva_deducible_telefono_mixto`, `test_calcular_iva_deducible_cuota_reta`, plus comida default case
- [x] 6.3 Verify tests fail: `pytest tests/fiscal/test_calcular_deducible.py -v`
- [x] 6.4 Implement `calcular_iva_deducible` in `src/fiscal/iva/calcular_deducible.py` (Art. 95 LIVA in docstring)
- [x] 6.5 Run tests — all 5 categories match the Excel-documented percentages: `pytest tests/fiscal/test_calcular_deducible.py -v`

## 7. Backend: `calcular_resultado_m303` — TDD
Acceptance criteria: CA-F1-08

- [x] 7.1 Write failing tests with pre-calculated values: `test_calcular_resultado_m303_a_ingresar`, `_a_compensar`, `_sin_actividad`
- [x] 7.2 Verify tests fail: `pytest tests/fiscal/test_calcular_resultado.py -v`
- [x] 7.3 Implement `calcular_resultado_m303` in `src/fiscal/iva/calcular_resultado.py`
- [x] 7.4 Run tests — all 3 green: `pytest tests/fiscal/test_calcular_resultado.py -v`

## 8. Backend: `validar_coherencia_m303` — TDD
Acceptance criteria: CA-F1-09

- [x] 8.1 Write failing tests with incoherent data: `test_validar_coherencia_m303_casilla_27_incoherente`, `_casilla_45_incoherente`, `_resultado_incoherente`
- [x] 8.2 Verify tests fail: `pytest tests/fiscal/test_validar_coherencia.py -v`
- [x] 8.3 Implement `validar_coherencia_m303` in `src/fiscal/iva/validar_coherencia.py`
- [x] 8.4 Run tests — each incoherent case returns a non-empty error list: `pytest tests/fiscal/test_validar_coherencia.py -v`

## 9. Backend: Minimal CRUD Endpoints for Facturas
Acceptance criteria: supports curl testing in Step 12 (CA-F1-06, CA-F1-07)

- [x] 9.1 Implement `GET /health` returning `{"status": "ok", "db": "ok", "redis": "ok"}`
- [x] 9.2 Implement `POST /api/proceso/p04/facturas` (manual entry only — no OCR this phase)
- [x] 9.3 Implement `GET /api/proceso/p04/facturas` (list current user's invoices)
- [x] 9.4 Wire Supabase JWT auth dependency per `docs/backend-standards.md`
- [x] 9.5 Structured error responses `{"error": "CODE", "detail": "...", "proceso": "P04"}` on 401/422

## 10. Backend: Review and Update Existing Unit Tests (MANDATORY)

- [x] 10.1 Review all tests written in Steps 3–9 for consistency with `docs/backend-standards.md` naming convention (`test_<function>_<scenario>`)
- [x] 10.2 Update any test that duplicates fixtures instead of reusing `tests/fixtures/facturas.py`

## 11. Backend: Run Unit Tests and Verify Database State (MANDATORY — AGENT MUST EXECUTE)
Acceptance criteria: CA-F1-10

- [x] 11.1 Capture pre-test Supabase state (row counts for all 6 tables in the test project)
- [x] 11.2 Run targeted tests per module, e.g. `pytest tests/fiscal/test_calcular_devengado.py -v --cov=src/fiscal/iva/calcular_devengado.py --cov-report=term-missing` (repeat for each module touched)
- [x] 11.3 Run full suite: `pytest tests/ -v --cov=src/fiscal --cov-report=term-missing`
- [x] 11.4 Verify coverage on `src/fiscal/` is exactly 100%, no uncovered branches
- [x] 11.5 Verify post-test database state matches the pre-test baseline (or document intentional seed changes); restore if not
- [x] 11.6 Create report `specs/fiscal-engine-fundamentos/reports/YYYY-MM-DD-step-11-unit-test-and-db-verification.md` using the template from `docs/openspec-tasks-mandatory-steps.md`
- [x] 11.7 Mark this step complete only after 100% coverage is confirmed and the report exists

## 12. Backend: Manual Endpoint Testing with curl (MANDATORY — AGENT MUST EXECUTE)
Acceptance criteria: CA-F1-06, CA-F1-07

- [x] 12.1 Start backend server: `uvicorn src.api.main:app --reload --port 8000`
- [x] 12.2 Verify health: `curl http://localhost:8000/health` — expect `{"status": "ok", "db": "ok", "redis": "ok"}`
- [x] 12.3 Export test JWT: `export TEST_JWT="<supabase_jwt_for_test_user>"`
- [x] 12.4 `curl -X POST http://localhost:8000/api/proceso/p04/facturas -H "Authorization: Bearer $TEST_JWT" -H "Content-Type: application/json" -d '<factura json>'` — verify 201 and response body matches `docs/api-spec.yml`
- [x] 12.5 `curl -X GET http://localhost:8000/api/proceso/p04/facturas -H "Authorization: Bearer $TEST_JWT"` — verify 200 and list contains the created invoice
- [x] 12.6 Test error case: missing `Authorization` header → verify 401
- [x] 12.7 Test error case: `tipo_iva=25` in payload → verify 422 with `{"error": "...", "detail": "...", "proceso": "P04"}`
- [x] 12.8 Restore database state: delete the invoice created in 12.4
- [x] 12.9 Create report `specs/fiscal-engine-fundamentos/reports/YYYY-MM-DD-step-12-curl-testing.md` using the template from `docs/openspec-tasks-mandatory-steps.md`

## 13. Frontend: E2E Testing with Playwright — NOT APPLICABLE THIS PHASE

- [x] 13.1 No frontend exists yet (Phase 5 scope). Explicitly skipped per `openspec/config.yaml` → `frontend.mandatory_steps` applying only when frontend work is in scope. Revisit when `frontend/` is scaffolded.

## 14. Update Technical Documentation (MANDATORY)

- [x] 14.1 Update `CHANGELOG.md` with the new fiscal engine functions and endpoints
- [x] 14.2 Verify `docs/data-model.md` still matches the actual migrations (no drift)
- [x] 14.3 Update `docs/api-spec.yml` if the `/api/proceso/p04/facturas` contract differs from what's already documented there

## Exit criteria (orchestrator evaluates before accepting this change)

- All tasks above checked `[x]`
- `pytest tests/ --cov=src/fiscal --cov-report=term-missing` reports 100% on `src/fiscal/`
- Both report files exist under `specs/fiscal-engine-fundamentos/reports/`, following the required sections in `openspec/config.yaml` → `reports.required_sections`
- Fiscal integrity checks from `openspec/config.yaml` that apply this phase: no fiscal arithmetic outside `src/fiscal/`, RLS enabled with `user_id = auth.uid()` on every new table
- RLS cross-user tests (2.3, 2.4) pass
- No out-of-scope item from `openspec/config.yaml` → `out_of_scope` was implemented
