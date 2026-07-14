# Changelog

All notable changes to this project are documented here, one entry per archived OpenSpec change.

## rpa-aeat (Phase 4 — RPA AEAT) — applied, pending `/verify` and `/archive`

Specs: `specs/rpa-aeat/` (not yet archived)

- `src/rpa/selectors/aeat_m303.yml` + `src/rpa/aeat/selectores.py::cargar_selectores()`: the only place Playwright CSS/aria selectors for the AEAT Sede Electrónica live — full casilla-by-casilla map (01-72, 110) plus auth/nav/action selectors.
- `src/rpa/casilla_map.py::construir_mapa_casillas()`: pure adapter deriving the full AEAT-form casilla dict from Phase 2's `ResultadoM303` — no new fiscal arithmetic. Includes the Product-Owner-approved `TABLA_CASILLA_DEDUCIBLE` (categoria_gasto → casilla-group mapping).
- `src/rpa/aeat/autenticacion.py`: Cl@ve Móvil (QR) authentication (Modelo B only — Modelo A/certificate vault out of scope per `openspec/config.yaml`; SMS PIN fallback documented as a known MVP limitation, not implemented). **Corrected mid-implementation** from an originally-designed text-entry "Cl@ve PIN" flow, which didn't match how AEAT's real Modelo B authentication works (it's QR-scan-with-phone, the RPA never sees or types a PIN) — `design.md` SPEC-F4-02 amended first per `CLAUDE.md` §7, then `autenticar_clave_movil()`/`capturar_qr_clave()` implemented with an injected `notificacion_fn` callback (this phase uploads the QR to Supabase Storage via `guardar_qr_clave()`; Phase 5 will display it in the chat UI instead, same callback shape). NIF verification and the 10-minute session-timeout check are unchanged.
- `src/rpa/aeat/m303_form.py`: navigation, all 4 form pages (identificación, devengado, deducible, resultado + bloque informativo), AEAT's own validation step, and submission. T04-E3 (result discrepancy vs. AEAT's own calculation) is a hard stop with ±0.02€ tolerance — never auto-corrected.
- `src/rpa/aeat/justificante.py`: downloads and verifies the justificante PDF's own text (NIF, modelo, ejercicio, período, CSV, resultado) before uploading to Supabase Storage — never accepted on a mismatch.
- `src/workers/rpa_worker.py`: T04-E1 (período ya presentado) and T04-E4 (submission failure, with screenshot-on-error) handling; `ejecutar_presentacion`/`procesar_presentacion` ARQ job ties the full flow together, idempotent on re-enqueue via the `presentacion` table's existing `UNIQUE(user_id, proceso, ejercicio, periodo)` constraint.
- **Prerequisite fix**: `src/agent/nodes/notificar.py`'s `confirmado=True` branch now upserts a `presentacion` row (`estado='confirmado'`) — previously it wrote nothing, leaving F4's worker with no queryable row to pick up.
- **Two additive Phase 2 fixes found during implementation** (zero new fiscal arithmetic, full regression suite re-verified after each): `ResultadoM303` now optionally carries the `ResultadoDevengado`/`ResultadoDeducible` breakdown objects it already computed but previously discarded; `ResultadoDeducible` gained `base_por_categoria` (the base amount per category, scaled identically to the existing cuota aggregate) since every deducible AEAT casilla group needs a base+cuota pair.
- Tests never hit real AEAT: Playwright fully mocked throughout, using 4 AEAT response stubs (`tests/rpa/_stubs_aeat.py`) covering success, validation error, período-ya-presentado, and AEAT-unavailable.
- **207 tests passing this phase** (0 failed, 0 skipped), 100% coverage on `src/fiscal/` (no regression) and 0 missed statements on every new `src/rpa/`/`src/workers/` module.
- **Explicitly not executed by the agent**: `test_autenticar_clave_movil_sesion_real` (real Cl@ve Móvil QR login against live AEAT) is written and marked `@pytest.mark.integration`, but requires manual Product Owner execution with a real NIF and a phone with the Cl@ve Móvil app — left unchecked in `tasks.md` until confirmed.

Targets CA-F4-01 through CA-F4-10. Not yet verified via `/verify` or `/adversarial-review` — see `specs/rpa-aeat/reports/`.

## agente-conversacional (Phase 3 — Agente conversacional P04)

Archived: `specs/archive/agente-conversacional/`

- LangGraph `StateGraph` for P04 (`src/agent/graph.py`): `detectar_periodo` → `verificar_duplicado` → `recopilar_datos` → (`ocr_factura` loop | `calcular`) → `resumir` → `confirmar` → (`recopilar_datos` | `notificar`). 8 nodes, all reachable, no orphans.
- `EstadoP04` TypedDict (`src/agent/state.py`) — fully JSON-serializable state for `PostgresSaver` checkpointing, including `user_jwt` (RLS, see below).
- `recopilar_datos` node: Claude Sonnet 5 tool-calling (`agregar_factura_emitida`, `agregar_factura_recibida`, `declarar_sin_actividad`, `declarar_intencion_rectificativa`) — the LLM classifies and requests confirmation for dudoso expense categories, discloses a detected duplicate presentation, but never computes a euro amount itself.
- OCR module (`src/agent/ocr.py`, `src/agent/nodes/ocr_factura.py`): Claude Vision extraction of invoices with per-field confidence. Fiscal numeric fields that feed `calcular_m303()` (`base_imponible`, `tipo_iva`, `cuota_iva`) always route to `facturas_baja_confianza` for mandatory confirmation, regardless of reported confidence — no invoice is ever auto-accepted via OCR. Confirmation is a **structural `interrupt()` gate inside `recopilar_datos`** (not an LLM tool call the model could skip) — see below.
- `calcular` node: thin wrapper around Phase 2's `calcular_m303()` — deserializes state into Pydantic models, reads `perfil_fiscal` from Supabase, serializes the result back.
- `resumir` node: deterministic template rendering (guarantees CA-F3-05 fields are never dropped by LLM paraphrasing) plus a short LLM-generated intro sentence.
- `confirmar` node: LangGraph `interrupt()` — the only path to `confirmado=True`, verified by code review (not just tests). Two-invocation pattern: trigger, then resume with `Command(resume=...)`.
- `notificar` node: on cancellation, upserts `presentacion.estado='cancelado'`; on confirmation, hands off without writing to `presentacion` — filing itself is out of scope (Phase 4). Confirmation message never implies filing has started.
- Checkpointing (`src/agent/checkpointer.py`): `PostgresSaver` against Supabase Postgres, `thread_id = f"{user_id}:P04:{ejercicio}:{periodo}"`. Round-trip verified against a real local Postgres, not mocked.
- RLS: every Supabase query in `src/agent/` (`verificar_duplicado`, `calcular`, `ocr_factura`, `notificar`) uses a client scoped to the authenticated user's own JWT (`src/agent/supabase_client.py::crear_cliente_usuario`) — never the service role key, so RLS is the actual enforcement mechanism rather than an application-level filter. Includes a new Storage RLS policy (`facturas` bucket) keyed on a `{emitidas|recibidas}/{user_id}/{filename}` path convention.
- `docs/backend-standards.md` project-structure fix: `src/agent/` (singular, this phase's runtime conversational agent) documented separately from `src/agents/` (plural, external build-time-only harness — CLAUDE.md §5).
- **145 tests total, 100% coverage (line and branch)** on both `src/fiscal/` (unchanged, no regression) and `src/agent/` (new this phase).

### Adversarial review history (3 passes before archiving)

- **Pass 1** found 3 blockers: (1) OCR-flagged fiscal fields were computed but never actually resolvable back into the declaration — fixed via a `recopilar_datos`-internal resolution flow; (2) all 4 Supabase-touching nodes used the service role key, bypassing RLS entirely — fixed with the user-scoped JWT client above; (3) a detected duplicate presentation (`presentacion_duplicada`) was computed by `verificar_duplicado` but never surfaced to the user — fixed by threading it into the system prompt and adding `declarar_intencion_rectificativa`. Also fixed 1 minor: `notificar`'s confirmation message implied AEAT filing was underway when it wasn't.
- **Pass 2** found the Pass-1 fix for blocker (1) introduced a **CRITICAL regression**: a bare `recopilar_datos -> recopilar_datos` self-edge is not a LangGraph pause point, so a single `graph.invoke()` re-executed the node (full Claude Sonnet 5 call included) immediately and repeatedly whenever an OCR field remained unconfirmed — empirically reproduced at **10,007 API calls** before crashing with `GraphRecursionError`. Also found 2 medium issues: a system-prompt priority contradiction, and undocumented `user_jwt` expiry risk across a long `interrupt()` pause.
- **Pass 3** (final, PASS WITH GAPS) verified the actual fix: OCR field confirmation moved to a real `interrupt()` loop inside `recopilar_datos`, positioned strictly before the LLM call, with an early return that skips the LLM call entirely on a confirmation-only resume — closing the CRITICAL finding structurally, not just by testing around it. The prompt contradiction was resolved by removing the now-superseded LLM-facing OCR-confirmation instruction; JWT expiry was documented as an accepted Phase 5 limitation. One LOW finding remains open (no single test yet drives the full graph through both `interrupt()` sites — `recopilar_datos`'s and `confirmar`'s — in one continuous run), tracked as a Phase 5 follow-up.

Satisfies CA-F3-01 through CA-F3-10. Verified via `/verify` and 3 rounds of `/adversarial-review` — see `specs/archive/agente-conversacional/reports/`.

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
