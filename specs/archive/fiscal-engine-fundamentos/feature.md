# Change: fiscal-engine-fundamentos

## Phase

F1 — Fundamentos y datos (`docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §3). Maps to `openspec/config.yaml` → `acceptance_criteria.phase_1`.

## Objective

Build the data infrastructure that underpins the whole MVP: the Supabase schema, the Pydantic models, and a unit-tested fiscal engine core — with zero dependency on the LLM or the RPA layer. At the end of this change, `src/fiscal/` takes a set of invoices and produces a correct M303 calculation for the 3 seed autónomo profiles, fully covered by tests.

## Agents involved (per `openspec/config.yaml`)

- **orchestrator** (`claude-opus-4-8`) — plans this change, evaluates exit criteria, runs `fiscal_integrity_checks`
- **backend_developer** (`claude-sonnet-4-6`, GLM-5.2 via DeepInfra once the harness exists) — implements all tasks below; this phase has no frontend work

## Scope

In scope:
- Supabase schema for `perfil_fiscal`, `factura_emitida`, `factura_recibida`, `presentacion`, `saldo_iva_compensar`, `alerta` — per `docs/data-model.md`.
- RLS policies on every table (`user_id = auth.uid()`).
- Pydantic models in `src/fiscal/models.py`.
- Fiscal engine core functions: `calcular_iva_devengado`, `calcular_iva_deducible`, `calcular_resultado_m303`, `validar_coherencia_m303`.
- A minimal deductibility table covering the 5 categories required by CA-F1-07 (not the full 22-category table).
- Seed data for 3 autónomo profiles (solo servicios, mixto con gastos, con ISP de proveedor extranjero).
- Minimal CRUD endpoints for facturas, enough to exercise the engine via curl (per mandatory step N+2).

Out of scope (later phases, per `openspec/config.yaml` → `out_of_scope` and Phase 2+ of the roadmap):
- The full 22-category deductibility table, ISP/intracomunitario/criterio de caja logic (Phase 2, SPEC-F2-01..05).
- LangGraph agent, Claude Sonnet conversational integration, OCR (Phase 3).
- Playwright RPA against AEAT (Phase 4).
- P01/P05-P08/P09/P13/P14/P24-P26 and régimen foral — explicitly out of scope for the whole MVP.

## Acceptance criteria

Maps directly to CA-F1-01 through CA-F1-10:

| ID | Criterion |
|---|---|
| CA-F1-01 | Supabase schema created with all 6 tables, correct columns/types/constraints |
| CA-F1-02 | RLS active — user A cannot read user B's invoices/declarations |
| CA-F1-03 | Performance indexes exist: `(user_id, fecha)` on `factura_emitida`, unique index on `presentacion (user_id, proceso, ejercicio, periodo)` |
| CA-F1-04 | Pydantic models reject invalid `tipo_iva`, invalid NIF, future dates |
| CA-F1-05 | Seed data loads: ≥10 issued invoices (rates 0/10/21%), 8 received invoices (corriente/inversión/ISP), ≥1 invoice with IRPF retención |
| CA-F1-06 | `calcular_iva_devengado()` matches manually pre-calculated values for all 3 seed profiles |
| CA-F1-07 | `calcular_iva_deducible()` applies correct percentages for ≥5 categories (vehículo 50%, software 100%, comida 0% default, teléfono mixto, cuota RETA) |
| CA-F1-08 | `calcular_resultado_m303()` correct for a_ingresar, a_compensar, and sin_actividad cases |
| CA-F1-09 | `validar_coherencia_m303()` detects casilla 27/45 mismatches and result inconsistencies |
| CA-F1-10 | 100% test coverage on the fiscal engine, no uncovered branches |

## References

- `openspec/config.yaml` — mandatory backend steps, fiscal integrity checks, agent/model assignment for this change
- `docs/openspec-tasks-mandatory-steps.md` — exact task structure and report templates followed in `tasks.md`
- `docs/data-model.md` — authoritative schema and Pydantic model shapes
- `docs/domain-context.md` — IVA rates, deductibility rules, glossary
- `docs/backend-standards.md` — fiscal engine rules (pure functions, no intermediate rounding, docstring with legal article), project structure, API endpoints, error format
- `docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §3 — Phase 1 objective and CA-F1-01..10 source
