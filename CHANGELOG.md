# Changelog

All notable changes to this project are documented here, one entry per archived OpenSpec change.

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
