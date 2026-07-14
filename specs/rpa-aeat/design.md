# Design: rpa-aeat

## Folder structure

Per `docs/backend-standards.md`'s Project structure block (planned since Phase 1):

```
src/
  rpa/
    aeat/
      autenticacion.py     # Cl@ve PIN auth (Modelo B only)
      m303_form.py          # navigate + fill all 4 pages + validate + submit
      justificante.py        # download PDF, verify, upload to Supabase Storage
    casilla_map.py           # pure adapter: ResultadoM303 -> full AEAT casilla dict
    selectors/
      aeat_m303.yml          # ONLY place Playwright selectors for AEAT live
  workers/
    rpa_worker.py             # ARQ worker: polls presentacion(estado='confirmado')
src/agent/
  nodes/
    notificar.py              # amended (Phase 3 file) — see SPEC-F4-00 below
```

`src/rpa/` and `src/workers/` do not exist yet — this change creates them.

## SPEC-F4-00 — Prerequisite fix: `notificar.py` writes a `presentacion` row on confirm

**Problem.** `specs/archive/agente-conversacional/design.md` SPEC-F3-02 states the `notificar` node, on `confirmado=True`, only hands off — it does not write to `presentacion`. Only the `cancelado=True` branch upserts a row today. There is therefore no queryable `estado='confirmado'` row for an ARQ worker to pick up.

**Fix.** Extend the existing `confirmado=True` branch of `notificar.py` (additive, does not touch the `cancelado` branch) to upsert:

```python
admin.table("presentacion").upsert({
    "user_id": estado["user_id"],
    "proceso": "P04",
    "modelo": "303",
    "ejercicio": estado["ejercicio"],
    "periodo": estado["periodo"],
    "estado": "confirmado",
    "total_devengado": estado["resultado_m303"]["total_devengado"],
    "total_deducible": estado["resultado_m303"]["total_deducible"],
    "saldo_compensar_aplicado": estado["resultado_m303"]["saldo_compensar_anterior"],
    "log_confirmacion": estado["resultado_m303"],  # JSONB snapshot incl. casillas
}, on_conflict="user_id,proceso,ejercicio,periodo").execute()
```

This matches the `UNIQUE (user_id, proceso, ejercicio, periodo)` constraint and the `estado` CHECK constraint already present on the table (`docs/data-model.md`), and the `ProcesoEstado.estado` enum already defined in `docs/api-spec.yml`. No migration is needed — the column set already anticipates this write.

**Test impact.** `specs/archive/agente-conversacional`'s existing `notificar` tests must keep passing unchanged (the `cancelado` branch is untouched); a new test is added in this change's own test tree (`tests/agent/nodes/test_notificar_confirma_escribe_presentacion.py`) asserting the new upsert, since the assertion belongs to F4's acceptance criteria (the worker's ability to find the row), not to F3's.

## SPEC-F4-01 — Selector map (`src/rpa/selectors/aeat_m303.yml`)

All Playwright CSS/aria selectors for the AEAT Sede Electrónica live here, never inline in Python. Format:

```yaml
# src/rpa/selectors/aeat_m303.yml
clave_pin:
  login_button: "a#accesoClavePin"
  nif_input: "input#nifPin"
  pin_input: "input#pinAcceso"
  submit_button: "button#entrarClave"

navegacion:
  menu_iva: "a[href*='IVA']"
  modelo_303: "a[data-modelo='303']"
  selector_ejercicio: "select#ejercicio"
  selector_periodo: "select#periodo"
  pre303_cargar: "button#cargarPre303"

pagina_1_identificacion:
  nif_prellenado: "input#nifTitular"
  regimen_general_checkbox: "input#regimenGeneral"
  criterio_caja_checkbox: "input#criterioCaja"

pagina_2_devengado:
  casilla_01: "input[name='casilla01']"
  casilla_02: "input[name='casilla02']"
  casilla_03: "input[name='casilla03']"
  # ... casillas 04-27, see full file for the complete field-by-field map

pagina_3_deducible:
  casilla_28: "input[name='casilla28']"
  # ... casillas 29-45

pagina_4_resultado:
  casilla_46: "input[name='casilla46']"
  # ... casillas 66, 69, 70, 71, 72, 110
  nrc_input: "input#nrc"
  iban_domiciliacion_input: "input#ibanDomiciliacion"

acciones:
  validar_button: "button#validarDeclaracion"
  presentar_button: "button#presentarDeclaracion"
  confirmar_firma_button: "button#confirmarFirma"
  descargar_justificante_button: "a#descargarJustificante"

mensajes_error:
  periodo_ya_presentado: ".alerta-error:has-text('ya existe una declaración')"
  discrepancia_resultado: ".alerta-error:has-text('el resultado no coincide')"
```

Loaded once at worker startup via a thin `cargar_selectores() -> dict` helper in `src/rpa/aeat/selectores.py`; every RPA module receives selectors as a parameter, never imports the YAML path itself, so unit tests can substitute a fixture selector map without touching the real file.

## SPEC-F4-02 — Authentication (`src/rpa/aeat/autenticacion.py`)

Modelo B (Cl@ve PIN) only — Modelo A (certificate vault) is out of scope per `openspec/config.yaml`.

Flow (mirrors T04-17 in the functional spec, identical to P01's T01-18):

1. Worker requests a Cl@ve PIN from the user (via the existing notification channel — the user must generate it just before the RPA runs, since it expires in 10 minutes).
2. `autenticar_clave_pin(nif: str, pin: str, page: Page, selectores: dict) -> SesionAEAT` — navigates to the Cl@ve PIN login, enters NIF + PIN, submits.
3. Verifies the authenticated NIF shown on the resulting page equals `perfil.nif` — mismatch raises `AutenticacionError`, no further steps run.
4. Returns `SesionAEAT(activa=True, timestamp_autenticacion=datetime.now(timezone.utc))`.

**Session timeout.** The Cl@ve PIN window is 10 minutes from PIN generation, not from AEAT login. `m303_form.py` checks `datetime.now(timezone.utc) - sesion.timestamp_autenticacion < timedelta(minutes=10)` before every AEAT-facing step; on expiry it raises `SesionExpiradaError`, which the worker catches and restarts the flow at authentication (asking the user for a fresh PIN) rather than silently retrying with a dead session.

## SPEC-F4-03 — Casilla mapping (`src/rpa/casilla_map.py`)

Pure function, no I/O, no fiscal arithmetic — only reshapes already-computed `Decimal` values from `ResultadoM303`, `ResultadoDevengado`, `ResultadoDeducible` (all Phase 2, `src/fiscal/models.py`) into the full AEAT casilla dict the form needs.

```python
def construir_mapa_casillas(resultado: ResultadoM303) -> dict[str, Decimal]:
    """Derives every AEAT-form casilla (01-72, 110) from an already-computed
    ResultadoM303. Adds no new fiscal logic — see src/fiscal/models.py
    lines 181-185, which anticipates this exact split since Phase 2."""
```

Devengado block (per-rate, from `ResultadoDevengado.por_tipo`/`cuotas`):

| Rate | Base casilla | Tipo casilla | Cuota casilla |
|---|---|---|---|
| 0% | 150 | 151 | 152 |
| 4% | 01 | 02 | 03 |
| 10% | 04 | 05 | 06 |
| 21% | 07 | 08 | 09 |
| ISP | 12 | — | 13 |
| Modificación (rectificativas, casuística C04) | 14 | — | 15 |

Only rates present in `por_tipo` with a non-zero base are populated; absent rates are left **unset** in the output dict (the form-filling step in SPEC-F4-04 must leave those fields blank, never write `0`, per T04-20's explicit warning).

Deducible block (from `ResultadoDeducible.por_categoria`, mapped via a new static table `TABLA_CASILLA_DEDUCIBLE` in `src/rpa/casilla_map.py`):

| `categoria_gasto` group | Base casilla | Cuota casilla |
|---|---|---|
| corriente interior (default — most autónomos only use this) | 28 | 29 |
| bienes de inversión interiores | 30 | 31 |
| importaciones corrientes | 32 | 33 |
| importaciones bienes de inversión | 34 | 35 |
| adquisiciones intracomunitarias corrientes | 36 | 37 |
| rectificación deducciones períodos anteriores | 40 | 41 |
| otras deducciones (prorrata, regularización) | 42-44 | — |

**Product Owner approved mapping** (`TABLA_CASILLA_DEDUCIBLE` in `src/rpa/casilla_map.py`):

| Casilla group | `categoria_gasto` values |
|---|---|
| corriente interior (28-29) | `software_saas`, `material_oficina`, `servicios_profesionales`, `telefono_mixto`, `alquiler_local`, `suministros_local`, `suministros_domicilio`, `formacion`, `publicidad_marketing`, `seguro_rc_profesional`, `comida_profesional`, `ropa_profesional`, `gastos_representacion`, `cuota_reta`, `intereses_prestamo`, `alimentacion_personal`, `multas_sanciones`, `ropa_personal` |
| bienes de inversión interiores (30-31) | `equipo_informatico_exclusivo`, `vehiculo_estandar`, `vehiculo_transportista`, `combustible_vehiculo` |
| adquisiciones intracomunitarias corrientes (36-37) | all ISP-flagged invoices (`es_isp=True`) from foreign suppliers |

Every `categoria_gasto` value not listed in one of the three rows above defaults to corriente interior (28-29). Importaciones (32-35), rectificación (40-41), and otras deducciones (42-44) remain reachable by the adapter for the invoice-level cases described earlier in this section (imports with a DUA, rectificaciones of prior periods, prorrata/regularización) but have no `categoria_gasto`-driven default — they are populated only when the underlying invoice/adjustment data explicitly indicates one of those cases.

This table mirrors `tabla_deducibilidad.py`'s philosophy — it is data, not logic. Update this file when new categories are added, never hunt through `m303_form.py`.

Result block: casillas 27 (total devengado, cross-checked against AEAT's own calculation — see SPEC-F4-04 T04-E3), 45 (total deducible), 46/66/69 (resultado), 70/71/72/110 per `tipo_resultado` (a_ingresar / a_compensar / a_devolver / sin_actividad), mirroring T04-22 exactly.

Bloque informativo: casillas 59 (entregas intracomunitarias, casuística C11), 60 (exportaciones, C10), 61, 62, 63 — populated only when > 0, per T04-23.

## SPEC-F4-04 — Form filling, validation, submission (`src/rpa/aeat/m303_form.py`)

Sequence (T04-18 through T04-26):

1. `navegar_a_modelo_303(page, ejercicio, periodo, selectores)` — menu path, select ejercicio/período, verify Pre303 pre-fill if offered, confirm pre-filled NIF/nombre match `perfil.nif`.
2. `rellenar_pagina_identificacion(page, perfil, selectores)` — régimen general = SI, criterio de caja checkbox if `perfil.regimen_iva == "caja"`.
3. `rellenar_pagina_devengado(page, mapa_casillas, selectores)` — writes only populated rate blocks; after writing, reads AEAT's own casilla 27 total and compares to `mapa_casillas["27"]` (tolerance ±0.02 €) — **discrepancy triggers T04-E3, see below, before any further page is touched.**
4. `rellenar_pagina_deducible(page, mapa_casillas, selectores)` — same discrepancy check against casilla 45.
5. `rellenar_pagina_resultado(page, mapa_casillas, resultado.tipo_resultado, metodo_pago, selectores)` — result casillas + payment method fields (NRC / IBAN domiciliación / redirect to manual card flow).
6. `rellenar_bloque_informativo(page, mapa_casillas, selectores)`.
7. `validar_formulario(page, selectores) -> ValidacionResult` — clicks AEAT's own "Validar" button, parses the response for zero-error vs error list. **CA-F4-06 requires this returns clean before any submission is attempted.** A non-clean validation is a hard stop (worker sets `estado='error'`, `error_code` from AEAT's message), never auto-corrected.
8. `presentar(page, sesion, selectores) -> PresentacionResult` — re-checks session freshness (< 10 min, SPEC-F4-02), clicks submit, handles the Cl@ve PIN signature prompt if required, captures CSV + NRC (if a_ingresar) + timestamp.

### Error handling — T04-E1 through T04-E4

| Error | Detected in | Recovery |
|---|---|---|
| **T04-E1** — Período ya presentado | step 1 (`navegar_a_modelo_303`) or the initial worker precheck | Query `presentacion` for an existing row for `(user_id, ejercicio, periodo)`. If found → surface its `csv_aeat`/justificante, do not resubmit. If not found in DB but AEAT reports one exists → set `estado='error'`, `error_code='periodo_ya_presentado_externo'`, flag for manual review (the user may have filed outside the system). Either way, if the user wants to correct it, the worker marks `requiere_rectificativa=True` and stops — P04-R is out of scope for this change. |
| **T04-E2** — NRC inválido | step 5 (`rellenar_pagina_resultado`, when `metodo_pago='nrc'`) | Validate NRC format (22 alphanumeric chars) before writing to the form. If AEAT itself rejects a well-formed NRC (mismatch with NIF/modelo/ejercicio/periodo/importe), stop, set `error_code='nrc_invalido'`, ask the user to obtain a fresh NRC from their bank — never guess or auto-correct a NRC. |
| **T04-E3** — Resultado agente ≠ resultado AEAT | steps 3-4 (casilla 27 / casilla 45 cross-check) | Compare casilla-by-casilla. If the difference is ≤ 0.02 € (rounding), proceed. If > 0.02 €, **hard stop — never submit.** Set `estado='error'`, `error_code='discrepancia_resultado'`, `error_detail` includes both values and the differing casilla, and require explicit user decision before any retry. |
| **T04-E4** — Presentación fuera de plazo / fallo general de envío | step 8 (`presentar`) | Detect via AEAT's response after clicking submit. Save a screenshot to Supabase Storage (`docs/backend-standards.md`'s existing RPA-failure convention), set `estado='error'`, `error_code`, `screenshot_path`. Retry path: worker re-attempts authentication + navigation from scratch (never resubmits against a stale AEAT session) up to a fixed retry count before surfacing to the user; retries never risk a duplicate submission because step 1 always re-checks for an existing `presentacion` row first (same guard as T04-E1). |

**Card payment.** If `metodo_pago == "tarjeta"`, `m303_form.py` stops immediately before any card-entry step and returns a state requiring the user to complete payment manually inside the (already-authenticated) AEAT session — the RPA never touches card fields, per `feature.md`'s scope note.

## SPEC-F4-05 — Justificante download (`src/rpa/aeat/justificante.py`)

After a successful `presentar()`:

1. Click the "descargar justificante" control, capture the PDF stream.
2. Parse the PDF (text extraction, not OCR — AEAT justificantes are text-layer PDFs) and verify NIF, modelo (303), ejercicio, período, CSV, and resultado all match the values just submitted. Mismatch → `error_code='justificante_no_coincide'`, hard stop (the filing may have succeeded but the artifact can't be trusted — flag for manual verification, do not silently accept).
3. Upload to Supabase Storage under `justificantes/{user_id}/{ejercicio}_{periodo}.pdf`, mirroring the `{emitidas|recibidas}/{user_id}/{filename}` RLS-path convention established in Phase 3.
4. Update the `presentacion` row: `estado='presentado'`, `csv_aeat`, `nrc` (if applicable), `justificante_path`, timestamp.

## SPEC-F4-06 — AEAT test stubs (`tests/rpa/_stubs_aeat.py`)

Per `docs/backend-standards.md`'s testing rule ("RPA tests use mock responses — never hit real AEAT in tests") and `openspec/config.yaml`'s testing policy, unit tests never launch a real browser against AEAT. Four fixture HTTP/DOM responses are provided, matching SPEC-F4-04's error table:

- `respuesta_exito()` — validation clean, submission succeeds, CSV + justificante returned.
- `respuesta_validacion_error()` — "Validar" returns a non-empty error list.
- `respuesta_periodo_ya_presentado()` — AEAT reports an existing declaration (T04-E1).
- `respuesta_aeat_no_disponible()` — a 5xx / timeout simulating AEAT unavailability (feeds T04-E4's general-failure path).

Any test that instead drives a real (even sandboxed) browser session against the actual AEAT site is marked `@pytest.mark.integration` per the marker convention established in Correction 2 (`pytest.ini`), and is never run in the TDD cycle (`pytest -m "not integration"`).

## ARQ worker (`src/workers/rpa_worker.py`)

Per `docs/backend-standards.md`'s ARQ + Redis pattern:

```python
async def procesar_presentacion(ctx, presentacion_id: str) -> None:
    """ARQ job: picks up a presentacion row in estado='confirmado' and
    drives it through autenticacion -> m303_form -> justificante."""
```

The worker is enqueued by Phase 5's `/api/proceso/p04/confirmar` endpoint (out of scope here — this change only implements the worker function itself and its ARQ registration, not the enqueueing endpoint). State transitions written to `presentacion.estado`: `confirmado → presentando → presentado | error`. Every transition and every error path re-checks `estado` at the start (idempotency guard) so a re-enqueued job on a row already `presentado` is a no-op, not a duplicate filing.

## Fiscal integrity checks applicable this phase (from `openspec/config.yaml`)

- *"LangGraph interrupt node present in every graph that leads to AEAT submission"* — satisfied upstream by Phase 3's `confirmar` interrupt; F4 only ever acts on rows already marked `confirmado` by a human via that interrupt, never on its own initiative.
- *"RLS enabled on every new Supabase table with user_id = auth.uid() policy"* — no new table is created in this change (`presentacion` already has RLS from Phase 1); the Supabase Storage path for justificantes follows the same `{user_id}`-scoped convention as Phase 3's invoice storage, which already has an RLS-equivalent Storage policy.
- Never presents with an unresolved fiscal discrepancy (T04-E3) — hard stop, no auto-correction, matches the "STOP and alert" language in the functional spec verbatim.
