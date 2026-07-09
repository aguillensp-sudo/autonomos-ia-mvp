# Step 11 Report - Unit Tests and Database Verification

- Date: 2026-07-03
- Change: fiscal-engine-fundamentos
- Agent: backend_developer (claude-sonnet-4-6 in this session; GLM-5.2 via DeepInfra once the harness exists)
- Environment: local Supabase (Docker), following the Python 3.14 / analytics-disabled deviations documented in `docs/development_guide.md`

## Commands Executed

- `pytest tests/ -v --cov=src/fiscal --cov-report=term-missing`
- `docker exec supabase_db_autonomos-ia-mvp psql -U postgres -d postgres -c "SELECT ... COUNT(*) ..."` (pre/post baseline)
- `docker exec supabase_db_autonomos-ia-mvp psql -U postgres -d postgres -c "EXPLAIN ANALYZE ..."` (index verification, CA-F1-03)

## Unit Test Results

- Targeted tests (fiscal engine, models, seed fixtures): 26 passed
- Integration tests (RLS, real local Supabase): 3 passed
- Full/required suite: **29 passed, 0 failed, 0 skipped**
- Runtime: 3.95s
- Notes: no flaky tests observed across 2 consecutive runs.

## Coverage

```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
src\fiscal\__init__.py                      0      0   100%
src\fiscal\iva\__init__.py                  0      0   100%
src\fiscal\iva\calcular_deducible.py       13      0   100%
src\fiscal\iva\calcular_devengado.py       11      0   100%
src\fiscal\iva\calcular_resultado.py       11      0   100%
src\fiscal\iva\tabla_deducibilidad.py       5      0   100%
src\fiscal\iva\validar_coherencia.py       14      0   100%
src\fiscal\models.py                       79      0   100%
---------------------------------------------------------------------
TOTAL                                     133      0   100%
```

100% coverage on all `src/fiscal/` modules, no uncovered branches (CA-F1-10 met).

## Database State Verification

- Pre-test baseline (before seed script + RLS tests ran): all 6 tables empty (0 rows).
- Post-test state:
  - `perfil_fiscal`: 0
  - `factura_emitida`: 16 (15 from `scripts/seed_data.py` seed + 1 from the RLS integration test fixture)
  - `factura_recibida`: 8 (from `scripts/seed_data.py`)
  - `presentacion`: 1 (from the RLS integration test fixture)
  - `saldo_iva_compensar`: 0
  - `alerta`: 0
- State restored: **No — intentionally left in place.** This data is the CA-F1-05 seed data that Phase 2+ builds on (per `design.md` SPEC-F1-05), and the RLS test fixture is idempotent (deletes and re-inserts its own rows on each run, per `tests/integration/test_rls.py`), so it does not need cleanup between runs.
- Index usage confirmed via `EXPLAIN ANALYZE` with real seeded data: `factura_emitida` query used `idx_factura_emitida_periodo`, `presentacion` query used `idx_presentacion_user_proceso` (CA-F1-03).

## Outcome

- Step 11 status: **PASS**
- Blocking issues: none
