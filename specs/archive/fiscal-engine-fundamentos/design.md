# Design: fiscal-engine-fundamentos

## SPEC-F1-01 — Supabase schema

Use the DDL already defined in `docs/data-model.md` verbatim for the 6 tables (`perfil_fiscal`, `factura_emitida`, `factura_recibida`, `presentacion`, `saldo_iva_compensar`, `alerta`). Migration files land in `src/db/migrations/` as `YYYYMMDD_HHMMSS_description.sql` (per `docs/backend-standards.md` § Database conventions), one file per table plus RLS if not inlined in the `CREATE TABLE` migration.

Indexes required by CA-F1-03 (already specified in `data-model.md`):
- `idx_factura_emitida_user_fecha` on `factura_emitida (user_id, fecha)`
- unique constraint `presentacion (user_id, proceso, ejercicio, periodo)`

## SPEC-F1-02 — Pydantic models

`src/fiscal/models.py`, mirroring the SQL schema exactly (per `docs/data-model.md` §"Pydantic models"):

- `PerfilFiscal`, `FacturaEmitida`, `FacturaRecibida`, `Presentacion`, `SaldoIVACompensar`, `ResultadoM303`

Plus two new result types required by the fiscal engine (see SPEC-F1-03):

```python
class ResultadoDevengado(BaseModel):
    """Breakdown of accrued VAT by rate. Art. 88-90 LIVA."""
    por_tipo: dict[int, Decimal]    # {0: base, 4: base, 10: base, 21: base}
    cuotas: dict[int, Decimal]      # {0: cuota, 4: cuota, 10: cuota, 21: cuota}
    total: Decimal                  # sum of cuotas — casilla 27

class ResultadoDeducible(BaseModel):
    """Breakdown of deductible input VAT by expense category. Art. 95 LIVA."""
    por_categoria: dict[str, Decimal]   # {categoria: cuota_deducible}
    total: Decimal                      # sum of cuota_deducible — casilla 45
```

Validation rules (CA-F1-04):
- `tipo_iva: Literal[0, 4, 10, 21]` — Pydantic rejects any other value (e.g. 25) with `ValidationError` automatically.
- `nif` / `nif_cliente` / `nif_proveedor`: field validator against the Spanish NIF/NIE format (8 digits + letter, or letter + 7 digits + letter).
- `fecha`: field validator rejects any date after `date.today()`.

## SPEC-F1-03 — Fiscal engine function contracts

All functions in `src/fiscal/iva/` (per `docs/backend-standards.md` § Project structure). Every function is pure, fully typed, docstring cites the legal article.

```python
def calcular_iva_devengado(
    facturas_emitidas: list[FacturaEmitida],
) -> ResultadoDevengado:
    """Breakdown of accrued VAT (IVA repercutido) by rate across issued invoices.
    Returns per-rate bases, per-rate quotas, and total (casilla 27).
    Art. 88-90 LIVA. Pure function. No rounding until the final return value.
    """

def calcular_iva_deducible(
    facturas_recibidas: list[FacturaRecibida],
    tabla_deducibilidad: dict[str, DeducibilidadRule],
) -> ResultadoDeducible:
    """Breakdown of deductible input VAT (IVA soportado deducible) by expense category.
    Returns per-category deductible amounts and total (casilla 45).
    Art. 95 LIVA. tabla_deducibilidad is injected data — never hardcoded here.
    """

def calcular_resultado_m303(
    ejercicio: int,
    periodo: str,
    devengado: ResultadoDevengado,
    deducible: ResultadoDeducible,
    saldo_compensar_anterior: Decimal,
) -> ResultadoM303:
    """Art. 99 LIVA. Casilla 70/71 result: positive = a ingresar, negative = a compensar,
    zero with no invoices = sin_actividad. Applies casilla 110 carry-forward.
    devengado.total = casilla 27, deducible.total = casilla 45.
    ejercicio/periodo are required because ResultadoM303 carries them.
    """

def validar_coherencia_m303(
    resultado: ResultadoM303,
    devengado: ResultadoDevengado,
    deducible: ResultadoDeducible,
) -> list[str]:
    """Returns a list of coherence errors (empty if none). Checks:
    - casilla 27 == devengado.total
    - casilla 45 == deducible.total
    - resultado == casilla 27 - casilla 45 (+/- saldo_compensar_anterior)
    """
```

Phase 1 implements only the 5-category subset of `tabla_deducibilidad` required by CA-F1-07 (vehículo 50%, software 100%, comida 0% default, teléfono mixto 50%, cuota RETA 0% IVA). The full 22-category table with ISP/intracomunitario logic is Phase 2 scope (SPEC-F2-01, out of scope here per `openspec/config.yaml`).

## SPEC-F1-04 — Test strategy

`tests/fiscal/` mirrors `src/fiscal/iva/` structure. Minimum 3 cases per function (happy path, edge case, error case). Naming: `test_<function>_<scenario>` (per `docs/backend-standards.md`).

Required cases:
- `test_calcular_iva_devengado_multiples_tipos` — verifies `ResultadoDevengado.por_tipo` and `cuotas` for 0/10/21% mix
- `test_calcular_iva_devengado_sin_facturas` — empty list returns zero totals
- `test_calcular_iva_deducible_vehiculo_uso_mixto` — `ResultadoDeducible.por_categoria['vehiculo']` = 50%
- `test_calcular_iva_deducible_software_profesional` — 100%
- `test_calcular_iva_deducible_telefono_mixto` — 50%
- `test_calcular_iva_deducible_cuota_reta` — 0% IVA
- `test_calcular_iva_deducible_comida_default` — 0% default
- `test_calcular_resultado_m303_a_ingresar` / `_a_compensar` / `_sin_actividad`
- `test_validar_coherencia_m303_casilla_27_incoherente` / `_casilla_45_incoherente` / `_resultado_incoherente`
- `test_factura_emitida_tipo_iva_invalido` / `_nif_invalido` / `_fecha_futura` (≥5 invalid-input cases per CA-F1-04)

All test values must be pre-calculated manually and documented in the test file as comments before implementation starts (TDD).

## SPEC-F1-05 — Seed data

`tests/fixtures/facturas.py` + `scripts/seed_data.py`. Three profiles per `docs/domain-context.md`:

1. **Solo servicios**: only 21% issued invoices, no expenses beyond software/office.
2. **Mixto con gastos**: issued invoices + vehicle, phone, restaurant expense categories.
3. **Con ISP**: includes ≥1 received invoice from a foreign supplier without Spanish NIF (e.g. "Google Ireland Ltd") to exercise `es_isp=True` — the ISP calculation itself is Phase 2, but the seed data and the `es_isp` flag must exist now so Phase 2 can build on it without a schema or fixture change.

Minimums per CA-F1-05: ≥10 issued invoices across 0/10/21% rates, 8 received invoices across corriente/inversión/ISP categories, ≥1 invoice with `retencion_irpf > 0`.

## Minimal API surface (for curl testing, mandatory step N+2)

Per `docs/backend-standards.md` § API endpoints, only the subset needed to exercise this phase's engine:

```
GET  /health                         → {"status": "ok", "db": "ok", "redis": "ok"}
POST /api/proceso/p04/facturas       → create factura_emitida or factura_recibida (manual entry, no OCR yet)
GET  /api/proceso/p04/facturas       → list current user's invoices
```

Error format per `docs/backend-standards.md`: `{"error": "CODE", "detail": "...", "proceso": "P04"}`.
Missing JWT → 401. Invalid payload → 422 with the structured error.

## Fiscal integrity checks applicable this phase (from `openspec/config.yaml`)

- No fiscal arithmetic outside `src/fiscal/` — not in Pydantic validators, not in migration scripts, not in route handlers.
- RLS enabled on every table created this phase, with `user_id = auth.uid()` policy.
- `saldo_iva_compensar` table exists this phase; the read/write wiring is exercised by `calcular_resultado_m303` tests even though the full multi-quarter carry-forward flow ships in Phase 2.
- ISP detection is a Phase 2 concern — not implemented here, but the `es_isp` column and seed profile 3 exist so Phase 2 needs no schema change.
