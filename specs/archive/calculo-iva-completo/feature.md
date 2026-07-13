# Change: calculo-iva-completo

## Phase

F2 — Motor fiscal P04 completo (`docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §4). Maps to `openspec/config.yaml` → `acceptance_criteria.phase_2`.

## Objective

Complete the fiscal engine so that, given any set of input invoices, it produces the correct M303 result for every casuística documented in the P04 source spec (`docs/Autonomos.io/1. ANALISIS FUNCIONAL/.md/P04_IVA_trimestral_v1_completo_1.md`, Hojas 4 and 5) — not just the 5-category happy path shipped in Phase 1 (`fiscal-engine-fundamentos`).

## Agents involved (per `openspec/config.yaml`)

- **orchestrator** (`claude-opus-4-8`) — plans this change, evaluates exit criteria, runs `fiscal_integrity_checks`
- **backend_developer** (`claude-sonnet-4-6`, GLM-5.2 via DeepInfra once the harness exists) — implements all tasks below; this phase has no frontend work

## Scope

In scope:
- Full deductibility table: all **22** expense categories from Hoja 4 (see `design.md` SPEC-F2-01 for the exact table, percentages, and legal references) — supersedes the 5-category subset from Phase 1.
- ISP (Inversión del Sujeto Pasivo) detection: 3 required cases — `nif_proveedor=None`, `nif_proveedor=''`, and a non-Spanish NIF prefix — plus the known-supplier reference list from casuística C05.
- Intracomunitario operations: casillas 59 (entregas intracom. exentas), 60 (exportaciones), 61 (ops. no sujetas), 62 (servicios B2B a UE) — casuísticas C10 and C11.
- Facturas rectificativas (casuística C04): same-quarter vs. different-quarter routing to casillas 14-15.
- Criterio de caja (casuística C06): filter devengado/deducible by `cobrada`/`pagada` date instead of issue date, when `perfil_fiscal.regimen_iva = 'criterio_caja'`.
- `saldo_iva_compensar` real persistence: read at calculation start, write at calculation end, against the real Supabase table (Phase 1 only exercised this via a function parameter in unit tests).
- Tests for the casuísticas in Hoja 5 that apply to this MVP (see note below on scope count).
- `calcular_bloque_informativo()` — new function producing casillas 59-63.
- `calcular_m303()` end-to-end orchestration function tying together devengado, deducible, bloque informativo, and resultado for a full run against real seed profiles.

**Note on casuística count — confirmed correction:** `docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` (CA-F2-09) and prior instructions referred to "10 casuísticas." This was an error in that phases document. The source of truth, `docs/Autonomos.io/1. ANALISIS FUNCIONAL/.md/P04_IVA_trimestral_v1_completo_1.md` Hoja 5, documents **11** casuísticas (C01–C11), and this change covers all 11. Two are explicitly scoped down per the source's own `ESTADO` column (not omitted, and not a discrepancy — a deliberate scope decision):
- **C07 (prorrata, actividades mixtas)** — source marks it `MVP: ALERTAR. V2: IMPLEMENTAR`. In scope only as detect-and-alert, not full proportional-deduction calculation.
- **C09 (autoliquidación rectificativa de un 303 ya presentado)** — source marks it `IMPLEMENTAR (proceso P04-R separado)`. This is a distinct process (P04-R) that corrects an *already filed* declaration; it depends on the RPA/filing capability (Phase 4) and is **out of scope** for this change.

Out of scope (later phases / out of MVP, per `openspec/config.yaml` → `out_of_scope`):
- P04-R (rectificativa de presentación ya realizada — C09) — needs Phase 4 (RPA) first.
- LangGraph agent, Claude Sonnet conversational integration, OCR (Phase 3).
- Playwright RPA against AEAT (Phase 4).
- Full prorrata calculation for C07 (only alerting is in scope).
- P01/P05-P09/P13/P14/P24-P26 and régimen foral.
- GLM-5.2 harness.

## Acceptance criteria

Maps directly to CA-F2-01 through CA-F2-10:

| ID | Criterion |
|---|---|
| CA-F2-01 | Full deductibility table classifies all 22 expense types correctly. Critical cases: vehículo (50% IVA / 0% IRPF), teléfono mixto (50/50), comida (dudosa → `requiere_confirmacion`), cuota RETA (sin IVA, 100% IRPF) |
| CA-F2-02 | ISP module detects foreign suppliers without Spanish NIF and computes auto-liquidation; Google Ireland (no NIF-ES) vs. Google Spain SL (with NIF-ES) — only the first triggers ISP |
| CA-F2-03 | Casuística C03: IRPF retención on an issued invoice does not affect its IVA — identical invoice with/without retención produces identical M303 IVA result |
| CA-F2-04 | Casuística C04: rectificativa in the same quarter as the original reduces devengado directly; in a different quarter, routes to modification casillas 14-15 |
| CA-F2-05 | Casuística C05: Adobe without Spanish NIF triggers ISP; Adobe with Spanish NIF (`ESB61653893`) does not |
| CA-F2-06 | Casuística C08: 4T negative result with `solicita_devolucion=True` → casilla 72; with compensación → casilla 110 of next quarter |
| CA-F2-07 | `calcular_bloque_informativo()` produces correct casillas 59-63: UE sale with valid NIF-IVA (59), export outside UE (60), B2B service to UE business (62) |
| CA-F2-08 | `actualizar_saldo_iva_compensar()` persists the negative balance to the real `saldo_iva_compensar` Supabase table; 1T with -300€ result, verify 2T reads casilla 110 = 300€ |
| CA-F2-09 | All applicable Hoja 5 casuísticas (C01-C11, per scope note above) have at least one test verifying correct behavior; casuísticas marked `MVP: ALERTAR` (C07) have a test verifying the correct alert fires instead of a calculation |
| CA-F2-10 | `calcular_m303()` end-to-end produces results identical to manually pre-calculated values for the 3 seed profiles, tolerance ±0.02€ |

## References

- `openspec/config.yaml` — mandatory backend steps, fiscal integrity checks, agent/model assignment
- `docs/openspec-tasks-mandatory-steps.md` — exact task structure and report templates followed in `tasks.md`
- `docs/data-model.md` — schema (`factura_emitida.es_isp`, `es_intracomunitaria`, `es_exportacion`; `factura_recibida.es_isp`, `es_bien_inversion`; `saldo_iva_compensar`)
- `docs/domain-context.md` — IVA rates, deductibility summary, glossary
- `docs/backend-standards.md` — fiscal engine rules (pure functions, no intermediate rounding, docstring with legal article)
- `docs/Autonomos.io/1. ANALISIS FUNCIONAL/.md/P04_IVA_trimestral_v1_completo_1.md` — **primary source for this change**: Hoja 4 (22-category deductibility table with legal references), Hoja 5 (11 casuísticas C01-C11), Hoja 4 casillas map (casillas 01-72, 59-63)
- `specs/archive/fiscal-engine-fundamentos/design.md` — Phase 1 context: existing function contracts (`calcular_iva_devengado`, `calcular_iva_deducible`, `calcular_resultado_m303`, `validar_coherencia_m303`) that this phase extends, not replaces
- `docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §4 — Phase 2 objective and CA-F2-01..10 source
