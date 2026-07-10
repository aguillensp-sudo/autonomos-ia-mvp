# Changelog

All notable changes to this project are documented here, one entry per archived OpenSpec change.

## calculo-iva-completo (Phase 2 — Motor fiscal P04 completo)

Archived: `specs/archive/calculo-iva-completo/`

- Full deductibility table: all 22 expense categories from Hoja 4 (`src/fiscal/iva/tabla_deducibilidad.py`), replacing Phase 1's 5-category subset. `calcular_iva_deducible` now trusts each invoice's own `porcentaje_deducible` (fixed a Phase 1 gap where it was re-derived from the table instead).
- ISP (Inversión del Sujeto Pasivo) module (`calcular_isp.py`): detects foreign suppliers without a Spanish NIF (3 mandatory cases: `None`, `''`, non-Spanish format) against the known-supplier list (Google Ireland, Meta Platforms Ireland, Adobe Systems, Microsoft Ireland).
- Bloque informativo (`calcular_bloque_informativo.py`): casillas 59 (entregas intracom.), 60 (exportaciones), 62 (servicios B2B UE) — VIES real-time validation explicitly deferred.
- Facturas rectificativas (`calcular_devengado.py` extended): same-quarter vs. different-quarter routing to casillas 14-15. New `factura_emitida` columns: `es_rectificativa`, `factura_original_id`, `cliente_es_empresario_ue`. `base_imponible` CHECK constraint relaxed to allow negative values for rectificativas.
- Criterio de caja (`criterio_caja.py`): filters invoices by collection/payment date instead of issue date.
- `saldo_iva_compensar` real persistence (`actualizar_saldo_iva_compensar.py`): reads/writes the actual Supabase table — Phase 1 only exercised this via a function parameter.
- Devolución vs. compensación in 4T (`calcular_resultado_m303` extended): `solicita_devolucion` param routes to casilla 72 instead of 110.
- Prorrata alert (`prorrata_alerta.py`, casuística C07): detection only, per source spec's `MVP: ALERTAR` — no proportional calculation.
- `calcular_m303()` orchestrator: end-to-end pipeline wiring all of the above, verified against the 3 seed profiles within ±0.02€.
- 78 tests, 100% coverage on `src/fiscal/` (line and branch).
- Casuísticas Hoja 5 (C01-C11) covered per scope: C09 (autoliquidación rectificativa de una presentación ya realizada) explicitly deferred to a future P04-R change (needs Phase 4 RPA); C02 (trimestres acumulados) rescoped as not a fiscal-engine concern (belongs to Phase 3's agent/orchestration layer).

Satisfies CA-F2-01 through CA-F2-10. Verified via `/verify` (7/7 exit criteria PASS) and `/adversarial-review` (1 HIGH finding resolved before archiving — `calcular_bloque_informativo()`'s result was computed but discarded in `calcular_m303()`, silently dropping casillas 59-62 from the orchestrator's output; see `specs/archive/calculo-iva-completo/reports/`).

## fiscal-engine-fundamentos (Phase 1 — Fundamentos y datos)

Archived: `specs/archive/fiscal-engine-fundamentos/`

- 6 Supabase tables with RLS enforced: `perfil_fiscal`, `factura_emitida`, `factura_recibida`, `presentacion`, `saldo_iva_compensar`, `alerta`.
- Pydantic models in `src/fiscal/models.py`, mirroring the SQL schema (including RPA/error tracking fields on `Presentacion` and timestamps on all tables).
- Fiscal engine core: `calcular_iva_devengado`, `calcular_iva_deducible`, `calcular_resultado_m303`, `validar_coherencia_m303` — all pure functions, cited to their LIVA articles (Art. 92, 95, 99, 99.2).
- Minimal deductibility table covering the 5 categories required by CA-F1-07 (vehículo, software, comida, teléfono mixto, cuota RETA).
- 29 tests, 100% coverage on `src/fiscal/` (line and branch).
- Minimal API surface: `GET /health`, `POST /api/proceso/p04/facturas`, `GET /api/proceso/p04/facturas`.
- Local Supabase development workflow documented in `docs/development_guide.md`, including the local-vs-remote split adopted after a Supabase Cloud incident during this phase.

Satisfies CA-F1-01 through CA-F1-10. Verified via `/verify` and `/adversarial-review` (4 MEDIUM findings resolved before archiving — see `specs/archive/fiscal-engine-fundamentos/reports/`).
