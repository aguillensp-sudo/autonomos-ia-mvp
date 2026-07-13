# Step 11 Report - Unit Tests and Database Verification

- Date: 2026-07-06
- Change: calculo-iva-completo
- Agent: backend_developer (claude-sonnet-4-6 in this session; GLM-5.2 via DeepInfra once the harness exists)
- Environment: local Supabase (Docker), same setup documented in `docs/development_guide.md`

## Commands Executed

- `pytest tests/fiscal/test_tabla_deducibilidad_22_categorias.py tests/fiscal/test_calcular_deducible.py -v`
- `pytest tests/fiscal/test_calcular_isp.py -v`
- `pytest tests/fiscal/test_calcular_bloque_informativo.py -v`
- `pytest tests/fiscal/test_calcular_devengado.py -v`
- `pytest tests/fiscal/test_criterio_caja.py -v`
- `pytest tests/integration/test_saldo_iva_compensar.py -v`
- `pytest tests/fiscal/test_calcular_m303_end_to_end.py -v`
- `pytest tests/fiscal/test_casuisticas_hoja5.py -v`
- `pytest tests/ -v --cov=src/fiscal --cov-branch --cov-report=term-missing` (full suite, final run)

## Unit Test Results

- Full suite: **77 passed, 0 failed, 0 skipped**
- Runtime: 20.56s
- Notes: no flaky tests observed. Two Phase 1 regressions were found and fixed during
  this change (not left as failures): (1) `calcular_iva_deducible` was ignoring the
  invoice's own `porcentaje_deducible` and re-deriving it from the table by category —
  fixed to trust the invoice's stored value, which is also what CA-F2-01's
  `suministros_domicilio` case requires. (2) Phase 1's deductibility category keys
  (`vehiculo`, `software`, `comida`) were renamed to match the 22-category table
  (`vehiculo_estandar`, `software_saas`, `comida_profesional`) — `tests/fixtures/facturas.py`
  updated accordingly, all Phase 1 tests re-verified green after the rename.

## Coverage

```
Name                                               Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------------------------
src\fiscal\__init__.py                                 0      0      0      0   100%
src\fiscal\iva\__init__.py                             0      0      0      0   100%
src\fiscal\iva\actualizar_saldo_iva_compensar.py      17      0      6      0   100%
src\fiscal\iva\calcular_bloque_informativo.py         16      0      8      0   100%
src\fiscal\iva\calcular_deducible.py                  11      0      2      0   100%
src\fiscal\iva\calcular_devengado.py                  19      0      4      0   100%
src\fiscal\iva\calcular_isp.py                        28      0     10      0   100%
src\fiscal\iva\calcular_m303.py                       31      0      2      0   100%
src\fiscal\iva\calcular_resultado.py                  16      0      8      0   100%
src\fiscal\iva\criterio_caja.py                        8      0      2      0   100%
src\fiscal\iva\prorrata_alerta.py                       5      0      2      0   100%
src\fiscal\iva\tabla_deducibilidad.py                  5      0      0      0   100%
src\fiscal\iva\validar_coherencia.py                  14      0      6      0   100%
src\fiscal\models.py                                  99      0     10      0   100%
----------------------------------------------------------------------------------------------
TOTAL                                                269      0     60      0   100%
```

100% line **and branch** coverage on all `src/fiscal/` modules (CA-F2 coverage requirement met).
One branch (the `alerta_prorrata is not None` True-path inside `calcular_m303`) was
initially uncovered (99% overall) — fixed by adding
`test_c07_calcular_m303_propaga_alerta_prorrata`, which exercises the full
orchestrator with a mixed-activity profile, not just `detectar_alerta_prorrata` in isolation.

## Database State Verification

- Pre-test baseline (same as end of Phase 1, this change added no seed data):
  `factura_emitida`: 16, `factura_recibida`: 8, `presentacion`: 1, `saldo_iva_compensar`: 0,
  `perfil_fiscal`: 0, `alerta`: 0.
- Post-test state: `factura_emitida`: 16, `factura_recibida`: 8, `presentacion`: 1,
  `saldo_iva_compensar`: **1**, `perfil_fiscal`: 0, `alerta`: 0.
- State restored: **Mostly — one intentional leftover row, documented.** The single
  `saldo_iva_compensar` row (ejercicio 2032, saldo=0.00) comes from
  `test_calcular_m303_perfil_1_persiste_saldo_para_siguiente_trimestre`, which
  verifies `calcular_m303()` actually calls the real persistence function — the
  row is left at `saldo=0.00` (the correct post-`a_ingresar` state), not deleted,
  following Phase 1's precedent of leaving verification data in place with
  justification. All other integration tests (`test_saldo_iva_compensar.py`,
  `test_casuisticas_hoja5.py`'s C02/C07 cases) clean up their own rows via
  fixture teardown or explicit deletes — verified no unbounded growth across
  repeated full-suite runs in this session.
- 3 new `factura_emitida` columns (`es_rectificativa`, `factura_original_id`,
  `cliente_es_empresario_ue`) confirmed present with correct defaults; Phase 1's
  RLS and seed-data row counts unaffected by the migration.

## Outcome

- Step 11 status: **PASS**
- Blocking issues: none
