# Design: calculo-iva-completo

## Schema additions required this phase

Phase 1's `factura_emitida`/`factura_recibida` schema (`docs/data-model.md`) does not carry enough fields for three Phase 2 casuísticas. These need a migration before the functions below can be implemented:

- `factura_emitida.es_rectificativa BOOLEAN DEFAULT FALSE` — flags a credit-note/correction invoice (casuística C04).
- `factura_emitida.factura_original_id UUID REFERENCES factura_emitida(id) NULL` — links a rectificativa to the invoice it corrects, so the engine can compare `periodo_declarado` of both to decide same-quarter vs. different-quarter routing.
- `factura_emitida.cliente_es_empresario_ue BOOLEAN DEFAULT FALSE` — distinguishes a B2B service to a UE business (casilla 62) from a B2C/goods intracom. sale (casilla 59). Without this flag the engine cannot tell the two apart even though both use `es_intracomunitaria=True`.

All three are additive, nullable-safe, backward compatible with Phase 1 data (defaults preserve existing rows' behavior).

## SPEC-F2-01 — Full deductibility table (22 categories)

Replaces the 5-category subset from Phase 1's `tabla_deducibilidad.py` with the complete table from Hoja 4 of `docs/Autonomos.io/1. ANALISIS FUNCIONAL/.md/P04_IVA_trimestral_v1_completo_1.md`. This is the authoritative source — do not alter percentages without updating that source first.

| categoria_gasto (key) | % IVA ded. | % IRPF ded. | requiere_confirmacion | Legal / fuente |
|---|---|---|---|---|
| `software_saas` | 100 | 100 | No | Art. 95 LIVA |
| `material_oficina` | 100 | 100 | No | Art. 95 LIVA |
| `servicios_profesionales` | 100 | 100 | No | Art. 95 LIVA |
| `equipo_informatico_exclusivo` | 100 | 100 | No | Art. 95 LIVA |
| `telefono_mixto` | 50 | 50 | Sí (confirm % uso) | Criterio AEAT |
| `alquiler_local` | 100 | 100 | No | Art. 95 LIVA |
| `suministros_local` | 100 | 100 | Condicional (proporcional si domicilio) | Art. 95 LIVA |
| `suministros_domicilio` | proporcional (m² despacho / m² vivienda) | 30% de la parte proporcional | Sí (informar m²) | Art. 30 LIRPF / DGT V2439-18 |
| `formacion` | 100 | 100 | Sí (confirmar relación) | Art. 95 LIVA |
| `publicidad_marketing` | 100 | 100 | No | Art. 95 LIVA |
| `vehiculo_estandar` | 50 | 0 | Sí (confirmar uso) | Art. 95.3 LIVA / Art. 29 LIRPF |
| `vehiculo_transportista` | 100 | 100 | Sí (confirmar actividad) | Art. 95.3 LIVA excepción |
| `combustible_vehiculo` | proporcional al vehículo vinculado (50 o 100) | proporcional (0 o 100) | No (automático) | Proporcional al vehículo |
| `comida_profesional` | posible 100 | 50 (tope 1% volumen operaciones) | Sí (confirmar uso prof.) | Art. 96.2 LIVA / AEAT |
| `ropa_profesional` | 100 | 100 | Sí | Art. 95 LIVA / Criterio AEAT |
| `ropa_personal` | 0 | 0 | No | Criterio AEAT DGT |
| `gastos_representacion` | posible 100 | tope 1% volumen operaciones | Sí | Art. 96.2 LIVA |
| `seguro_rc_profesional` | 100 | 100 | No | Art. 95 LIVA |
| `alimentacion_personal` | 0 | 0 | No | Criterio AEAT |
| `multas_sanciones` | 0 | 0 | No | Art. 14 LIRPF |
| `cuota_reta` | SIN IVA (0) | 100 | No | Art. 30 LIRPF |
| `intereses_prestamo` | EXENTO (0) | según financiación | Sí | Art. 20 LIVA / Art. 30 LIRPF |

Notes on implementation:

- `combustible_vehiculo` and `comida_profesional`/`gastos_representacion` (percentage "posible 100%") are **not** flat constants — they depend on a companion field (linked vehicle's deductibility, or the confirmation outcome). Model this as the deductibility *default* the agent proposes; `requiere_confirmacion=True` still gates it per Phase 1's existing flag on `FacturaRecibida`.
- `suministros_domicilio` is a **rule, not a constant**. The percentage is computed at invoice ingestion time (m² despacho / m² vivienda, supplied by the user) and stored directly on `factura_recibida.porcentaje_deducible`. The table entry documents the rule; the test for this category must verify that `requiere_confirmacion=True` is set and that the engine reads `porcentaje_deducible` from the invoice record rather than looking up a fixed value from the table.
- IRPF percentages are recorded in the table for completeness and future P09 (M130) reuse, but this phase's functions only consume the IVA percentage — `docs/backend-standards.md` scopes the fiscal engine to IVA (P04) this MVP.

`calcular_iva_deducible()` (existing, Phase 1) is extended to accept this full table — its signature (`facturas_recibidas`, `tabla_deducibilidad`) does not change; only the injected `TABLA_DEDUCIBILIDAD` dict grows from 5 to 22 entries plus the special-case handling above.

## SPEC-F2-02 — ISP (Inversión del Sujeto Pasivo) module

New module `src/fiscal/iva/calcular_isp.py`. Art. 84.Uno.2º LIVA (inversión del sujeto pasivo).

```python
def detectar_isp(factura_recibida: FacturaRecibida) -> bool:
    """True if this received invoice triggers ISP self-assessment.
    Art. 84.Uno.2º LIVA. Handles all 3 required cases:
    - nif_proveedor is None
    - nif_proveedor == '' (empty string)
    - nif_proveedor is not a valid Spanish NIF/CIF format AND not in
      the known-Spanish-registered-supplier list (SPEC-F2-02 table).

    IMPORTANT: Spanish domestic NIFs (e.g. '12345678Z') do NOT carry
    an 'ES' prefix — that prefix only appears on NIF-IVA codes issued
    to foreign entities registered for VAT in Spain. The correct check is:
      (a) Does nif_proveedor match the Spanish NIF/NIE/CIF pattern
          (same regex as Phase 1's NIF_NIE_PATTERN in models.py)?
      OR
      (b) Is nif_proveedor in the known-Spanish-registered-supplier
          NIF-IVA list (ESN0076590D, ESN0133895B, ESB61653893, ESN0004929H)?
    If NEITHER (a) nor (b) → ISP applies.
    """

def calcular_isp(facturas_recibidas: list[FacturaRecibida]) -> ResultadoISP:
    """For each factura_recibida where detectar_isp() is True:
    - base_isp += base_imponible (casilla 12, devengado)
    - cuota_isp_devengada += base_imponible * Decimal("0.21") (casilla 13, devengado)
    - cuota_isp_deducible += cuota_isp_devengada_de_esta_factura * porcentaje_deducible / 100
      (goes into deducible casillas 34-35, per SPEC-F2-01's category for the expense)
    Net effect is 0 when porcentaje_deducible == 100 (the common case per C05).
    Art. 84.Uno.2º LIVA.
    """
```

```python
class ResultadoISP(BaseModel):
    base_isp: Decimal             # casilla 12
    cuota_isp_devengada: Decimal  # casilla 13
    cuota_isp_deducible: Decimal  # feeds into casillas 34-35
```

Known Spanish-registered suppliers (casuística C05 — verify against this list before
assuming ISP, since these have a Spanish NIF and do NOT trigger ISP):

| Proveedor | NIF-IVA español |
|---|---|
| Google Ireland Ltd | ESN0076590D |
| Meta Platforms Ireland | ESN0133895B |
| Adobe Systems | ESB61653893 |
| Microsoft Ireland | ESN0004929H |

This list is data (a Python dict), not logic — same rule as `tabla_deducibilidad.py`.

**Fiscal integrity check (from `openspec/config.yaml`):** `detectar_isp()` must have an
explicit test for each of the 3 mandatory inputs: `nif_proveedor=None`, `nif_proveedor=''`,
and a NIF that is neither Spanish-format nor in the known list. One test each — not one
representative covering all three.

## SPEC-F2-03 — Intracomunitario operations (casillas 59-63)

New module `src/fiscal/iva/calcular_bloque_informativo.py`. These casillas are informative —
they do not change `resultado`, but must be present and correct (AEAT cross-checks against M349).

```python
def calcular_bloque_informativo(
    facturas_emitidas: list[FacturaEmitida],
) -> BloqueInformativo:
    """Art. 25 LIVA (entregas intracomunitarias exentas), Art. 21 LIVA (exportaciones).
    Casillas 59-63:
    - casilla 59: sum(base) where es_intracomunitaria AND NOT cliente_es_empresario_ue
      (goods/B2C intracom. delivery — requires valid NIF-IVA client, VIES-verifiable;
      Phase 2 does not call the real VIES API — see 'Deferred' below)
    - casilla 60: sum(base) where es_exportacion (client outside EU)
    - casilla 61: sum(base) where a mixed-activity exemption applies (out of scope
      this phase — no autónomo profile in the seed data has a mixed exempt activity;
      implement the field but expect it to always be 0 this phase)
    - casilla 62: sum(base) where es_intracomunitaria AND cliente_es_empresario_ue
      (B2B service to a UE business — reverse charge on the client's side)
    """

class BloqueInformativo(BaseModel):
    casilla_59: Decimal
    casilla_60: Decimal
    casilla_61: Decimal
    casilla_62: Decimal
```

**Deferred to a later phase (not this change):** real-time VIES NIF-IVA validation.
Casuística C11 requires verifying the client's NIF-IVA in the VIES registry before
applying the exemption. This phase trusts the `cliente_es_empresario_ue` flag as
already-verified input. Document this explicitly in the task report — not a silent omission.

## SPEC-F2-04 — Facturas rectificativas (casuística C04)

Extends `calcular_iva_devengado()` (Phase 1) — same function, no signature change, but
its aggregation logic must now branch on `es_rectificativa`:

- If `es_rectificativa=True` AND `factura_original.periodo_declarado == factura_rectificativa.periodo_declarado` (same quarter): the rectificativa's (negative) base/cuota are summed directly into the normal `por_tipo`/`cuotas` breakdown — casillas 07-09, no special casilla needed.
- If `es_rectificativa=True` AND periods differ: route to casillas 14 (base mod.) and 15 (cuota mod.) instead — new fields on `ResultadoDevengado`:

```python
class ResultadoDevengado(BaseModel):
    por_tipo: dict[int, Decimal]
    cuotas: dict[int, Decimal]
    base_modificacion: Decimal = Decimal("0.00")   # casilla 14
    cuota_modificacion: Decimal = Decimal("0.00")  # casilla 15
    total: Decimal
    # total (casilla 27) = sum(cuotas.values()) + cuota_modificacion
    # cuota_modificacion (casilla 15) is part of the total but is presented
    # in a separate block on the M303 form — the RPA (Phase 4) must fill
    # casilla 15 explicitly from this field, not derive it from total alone.
```

**Note for Phase 4 (RPA):** casilla 27 on the AEAT form is the algebraic sum of all
devengado blocks including casilla 15. However, the form requires casilla 15 to be
filled separately — the RPA cannot simply put the total in casilla 27 and leave 15 blank.
This design preserves both values so Phase 4 can fill both correctly.

## SPEC-F2-05 — Criterio de caja (casuística C06)

No new module — a **filter** applied before invoices reach `calcular_iva_devengado`/
`calcular_iva_deducible`, gated on `perfil_fiscal.regimen_iva == 'criterio_caja'`:

```python
def filtrar_por_criterio_caja(
    facturas_emitidas: list[FacturaEmitida],
    facturas_recibidas: list[FacturaRecibida],
    regimen_iva: str,
    fecha_inicio_periodo: date,
    fecha_fin_periodo: date,
) -> tuple[list[FacturaEmitida], list[FacturaRecibida]]:
    """If regimen_iva != 'criterio_caja': returns inputs unchanged (filtered by
    fecha, the Phase 1 behavior).
    If regimen_iva == 'criterio_caja': filters facturas_emitidas to only those
    with cobrada=True and fecha_cobro within the period; facturas_recibidas to
    only those with pagada=True and fecha_pago within the period.
    Art. 163 terdecies LIVA (régimen especial del criterio de caja).
    """
```

`calcular_m303()` (SPEC-F2-07) calls `filtrar_por_criterio_caja` *before* passing
invoices to Phase 1's functions — neither `calcular_iva_devengado` nor
`calcular_iva_deducible` needs to change.

## SPEC-F2-06 — `saldo_iva_compensar` real persistence

New module `src/fiscal/iva/actualizar_saldo_iva_compensar.py`. This is the first Phase 2
function that is **not** pure — it is the intentional boundary where the deterministic
engine touches the database. The read/write itself is I/O, not fiscal arithmetic; all
arithmetic still happens in pure functions (per `docs/backend-standards.md`).

```python
def leer_saldo_compensar(client: Client, user_id: str, ejercicio: int) -> Decimal:
    """Reads the current saldo_iva_compensar for this user/ejercicio.
    Returns Decimal('0.00') if no row exists yet.
    Art. 99.Cinco LIVA (compensación de cuotas en períodos siguientes).
    """

def actualizar_saldo_iva_compensar(
    client: Client, user_id: str, ejercicio: int, resultado: ResultadoM303,
) -> Decimal:
    """Writes the new saldo after a quarter is calculated:
    - tipo_resultado == 'a_compensar': nuevo_saldo = saldo_anterior + abs(resultado.resultado)
    - tipo_resultado == 'a_ingresar':  nuevo_saldo = 0
    - tipo_resultado == 'sin_actividad': nuevo_saldo = saldo_anterior (unchanged)
    - tipo_resultado == 'a_devolver':  nuevo_saldo = 0
    Upserts into saldo_iva_compensar on (user_id, ejercicio) unique constraint
    (per docs/data-model.md).
    Returns the new saldo for the caller to log/report.
    Art. 99.Cinco LIVA.
    """
```

**Fiscal integrity check satisfied:** `openspec/config.yaml` requires "saldo_iva_compensar
is read at calculation start and written at calculation end" — `calcular_m303()` (SPEC-F2-07)
calls `leer_saldo_compensar` first (step 1) and `actualizar_saldo_iva_compensar` last
(step 9), closing the gap Phase 1 left open.

## SPEC-F2-07 — `calcular_m303()` end-to-end orchestrator

New module `src/fiscal/iva/calcular_m303.py`. This is the only function in `src/fiscal/`
allowed to take a Supabase `client` — everything else stays pure.

```python
def calcular_m303(
    client: Client,
    user_id: str,
    ejercicio: int,
    periodo: str,
    perfil_fiscal: PerfilFiscal,
    facturas_emitidas: list[FacturaEmitida],
    facturas_recibidas: list[FacturaRecibida],
    fecha_inicio_periodo: date,
    fecha_fin_periodo: date,
) -> tuple[ResultadoM303, list[str]]:
    """Orchestrates the full M303 pipeline for one quarter.
    Art. 99 LIVA (liquidación del impuesto).

    Execution order (must not be reordered):
    1. leer_saldo_compensar(client, user_id, ejercicio)
    2. filtrar_por_criterio_caja(...) per perfil_fiscal.regimen_iva
    3. calcular_isp(facturas_recibidas) — merges into devengado/deducible
    4. calcular_iva_devengado(facturas_emitidas) — includes rectificativa routing
    5. calcular_iva_deducible(facturas_recibidas, TABLA_DEDUCIBILIDAD) — includes ISP deducible
    6. bloque = calcular_bloque_informativo(facturas_emitidas)
       -> resultado.casillas['59'/'60'/'61'/'62'] = bloque.casilla_* (assigned
       after step 7 produces `resultado`, but the value itself comes from this
       step — the orchestrator must not discard `bloque`, since these casillas
       are the only place CA-F2-07's output reaches calcular_m303's caller)
    7. calcular_resultado_m303(ejercicio, periodo, devengado, deducible, saldo_anterior)
    8. validar_coherencia_m303(resultado, devengado, deducible) — collect errors, do not raise
    9. actualizar_saldo_iva_compensar(client, user_id, ejercicio, resultado)

    Returns (resultado, errores_coherencia).
    Caller decides what to do with errores_coherencia — Phase 3's human-in-the-loop
    node surfaces them to the user; this phase just returns them.
    """
```

## Casuística C02 — scope clarification

Casuística C02 ("varios trimestres acumulados sin presentar") is about detecting that the
user has multiple quarters pending and alerting them. This is **not a fiscal engine concern**
— the engine receives a list of invoices for one quarter and computes a result. It does not
know how many quarters are pending in the database.

**This phase's scope for C02:** the fiscal engine returns its result for the requested
quarter. Detecting pending quarters is a database query against the `presentacion` table,
which belongs to the **agent/orchestration layer (Phase 3)**. The test for C02 in
`tasks.md` Step 9.2 must be limited to:

- Verify that `calcular_m303()` processes one quarter correctly even when prior quarters
  are present in the `presentacion` table with `estado='pendiente'`.
- The alert/detection logic itself is out of scope for F2 — add a `# TODO: Phase 3`
  comment in the test file header noting this explicitly.

## Test strategy for this phase

`tests/fiscal/` gains one test module per new function above, following Phase 1's
`test_<function>_<scenario>` convention, plus:

- `test_tabla_deducibilidad_22_categorias.py` — one assertion per category verifying
  percentage matches SPEC-F2-01 exactly. For `suministros_domicilio`: verify
  `requiere_confirmacion=True` and that the engine reads `porcentaje_deducible` from the
  invoice, not from a fixed table value (CA-F2-01).
- `test_calcular_isp.py` — the 3 mandatory cases (`nif_proveedor=None`, `''`, non-Spanish-
  format NIF) each as a separate test (CA-F2-02), plus Google Ireland vs. Google Spain SL
  and Adobe with/without Spanish NIF (CA-F2-02, CA-F2-05).
- `test_calcular_devengado_rectificativa.py` — same-quarter vs. different-quarter, plus
  explicit assertion that `cuota_modificacion` is in `ResultadoDevengado` and that
  `total = sum(cuotas.values()) + cuota_modificacion` (CA-F2-04).
- `test_criterio_caja.py` — invoice issued but not yet collected is excluded;
  invoice collected in-period is included; `regimen_iva='general'` passes through
  unchanged (casuística C06).
- `test_calcular_bloque_informativo.py` — casilla 59 (UE goods sale), 60 (export),
  62 (UE B2B service) (CA-F2-07).
- `test_actualizar_saldo_iva_compensar.py` — integration test against real local Supabase:
  1T with -300€ persists saldo=300; 2T read returns casilla 110 = 300€ (CA-F2-08).
- `test_calcular_m303_end_to_end.py` — full pipeline against the 3 seed profiles,
  tolerance `abs(diff) <= Decimal("0.02")` (CA-F2-10).
- One test per applicable casuística: C01, C02 (engine-only scope per note above),
  C03, C04, C05, C06, C07-as-alert, C08, C10, C11 — CA-F2-09.
  C09 is explicitly out of scope (see `feature.md`).

## Fiscal integrity checks applicable this phase (from `openspec/config.yaml`)

- ISP detection handles all 3 required inputs — see SPEC-F2-02.
- `saldo_iva_compensar` read at start / written at end of `calcular_m303()` — SPEC-F2-06/07.
- No fiscal arithmetic in FastAPI route handlers — this phase does not touch `src/api/`.
- LangGraph interrupt node — not applicable, no LangGraph yet (Phase 3).
- RLS — no new tables this phase (only 3 additive columns); existing policies cover them.
