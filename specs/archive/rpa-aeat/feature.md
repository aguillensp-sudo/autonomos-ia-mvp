# Change: rpa-aeat

## Phase

F4 — RPA AEAT (`docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §6). Maps to `openspec/config.yaml` → `acceptance_criteria.phase_4`.

## Objective

Build the Playwright RPA module that takes a confirmed P04 declaration (output of Phase 3's `agente-conversacional` graph) and actually files the Modelo 303 with the AEAT Sede Electrónica: authenticate with Cl@ve PIN, fill the form from the computed casillas, validate before submitting, submit, and store the resulting justificante PDF. At the end of this change, a confirmed declaration in the `presentacion` table can be picked up by an ARQ worker and turned into a real AEAT filing with a CSV and a downloadable justificante — with no fiscal arithmetic re-implemented and no selector hardcoded in Python.

## Agents involved (per `openspec/config.yaml`)

- **orchestrator** (`claude-opus-4-8`) — plans this change, evaluates exit criteria, runs `fiscal_integrity_checks` (in particular: *"LangGraph interrupt node present in every graph that leads to AEAT submission"* and *"RLS enabled on every new Supabase table with user_id = auth.uid() policy"*)
- **backend_developer** (`claude-sonnet-4-6`, GLM-5.2 via DeepInfra once the harness exists) — implements all tasks below; this phase has no frontend work (no UI exists yet — Phase 5 scope)

## Prerequisite gap found during research — must be resolved as part of this change

Phase 3's `notificar` node (`src/agent/nodes/notificar.py`) only upserts a `presentacion` row when `cancelado=True`. When `confirmado=True`, it hands off without writing anything to `presentacion` (per `specs/archive/agente-conversacional/design.md`, SPEC-F3-02's table: *"does NOT write to presentacion itself (that's Phase 4's job once it actually files with AEAT)"*). As written, there is no queryable row with `estado='confirmado'` for an ARQ worker to pick up — F4 has nothing to poll.

**Resolution, in scope for this change:** amend `notificar.py` (small, additive change to already-shipped Phase 3 code, not a new file) so that on `confirmado=True` it also upserts a `presentacion` row with `estado='confirmado'`, the serialized `resultado_m303` (including `casillas`), and `rpa_job_id=null` — giving F4's worker a stable row to transition through `presentando → presentado|error`. This keeps the state machine consistent with the `ProcesoEstado` enum already defined in `docs/api-spec.yml` and the CHECK constraint already present on `presentacion.estado` in `docs/data-model.md`. Per `CLAUDE.md` §7 this is documented here as part of this change's design, not applied as an informal "quick fix" to Phase 3 — see `tasks.md` group 1.

## Second gap found during research — casilla mapping is incomplete

Phase 2's `calcular_m303()` only populates `casillas` for `{"12","13","27","45","59","60","61","62","70","72","110"}`. It does not break out the per-rate devengado casillas (01-03 / 04-06 / 07-09), the modificación block as a distinct pair (14-15, currently folded only into 27), or the deducible sub-groups CA-F4-04 requires (28-29 corriente, 30-31 inversión, 34-35 intracomunitario, 32-33 importación corriente, 36-37 adquisiciones intracom. corrientes, 40-41 rectificación, 42-44 otras deducciones). `ResultadoDevengado.por_tipo`/`cuotas` and `ResultadoDeducible.por_categoria` already hold the underlying Decimal values internally — this is a pure mapping gap, not a missing calculation, and a code comment in `src/fiscal/models.py` (lines 181-185) already anticipates exactly this being Phase 4's job.

**Resolution, in scope for this change:** F4 builds its own thin, pure casilla-mapping adapter (`src/rpa/aeat/casilla_map.py`) that derives the full AEAT-form casilla set from the already-computed `ResultadoM303` object — no new fiscal arithmetic, no reopening of Phase 2's engine. This includes a static `categoria_gasto → tipo_casilla_deducible` table (a data file, mirroring the philosophy of Phase 2's `tabla_deducibilidad.py`), with the exact category→casilla-group assignment already approved by the Product Owner — see `design.md` SPEC-F4-03.

## Scope

In scope:
- `src/rpa/aeat/autenticacion.py` — Cl@ve PIN authentication flow only (Modelo B). Modelo A (certificate vault) is explicitly out of scope for MVP per `openspec/config.yaml` → `out_of_scope`.
- `src/rpa/aeat/m303_form.py` — navigates to the Modelo 303 form, selects ejercicio/período, fills all four pages (identificación, devengado, deducible, resultado + bloque informativo) from the casilla map.
- `src/rpa/aeat/justificante.py` — downloads the PDF justificante after successful submission and uploads it to Supabase Storage.
- `src/rpa/casilla_map.py` (or `src/rpa/aeat/casilla_map.py` — exact path finalized in `design.md`) — pure adapter from `ResultadoM303` to the full AEAT casilla dict.
- `src/rpa/selectors/aeat_m303.yml` — the only place Playwright CSS/aria selectors for the AEAT site are allowed to live.
- `src/workers/rpa_worker.py` — ARQ worker that picks up `presentacion` rows in `estado='confirmado'`, runs the RPA flow, and transitions state through `presentando` to `presentado` or `error`.
- Form validation before submission (AEAT's own "Validar" step) and a hard stop on any discrepancy between the agent's computed result and AEAT's computed result (casilla 27 / casilla 45 / final result), tolerance ±0.02 €.
- Error handling for T04-E1 through T04-E4 (see `design.md` SPEC-F4-04 for full detection/recovery logic per error type).
- Amendment to `src/agent/nodes/notificar.py` per the prerequisite gap above.
- AEAT stub/mock HTTP fixtures for unit tests (success, validation error, período ya presentado, AEAT no disponible) — real AEAT is never hit in tests.

Out of scope (later phases / explicitly excluded per `openspec/config.yaml`):
- Authentication Model A (certificate vault) — V2 only.
- `/api/proceso/p04/confirmar`, `/estado`, `/justificante` and any other F5 API endpoints — F4 is the RPA module + worker only, it does not touch `src/api/`.
- Frontend / chat UI (Phase 5).
- P04-R (autoliquidación rectificativa) — T04-E1 explicitly derives to this process when the user wants to correct an already-filed declaration; P04-R itself is not implemented here.
- Full VIES real-time validation, full prorrata calculation (casuística C07 stays "MVP: ALERTAR" per the functional spec).
- Any process other than P04 (P01, P05-P09, P13, P14, P24-P26, régimen foral).
- Payment-card flows: if `metodo_pago='tarjeta'`, the RPA must stop and redirect the user to complete card entry manually in the AEAT session — the agent must never store or process card data.

## Acceptance criteria

Maps directly to CA-F4-01 through CA-F4-10:

| ID | Criterion |
|---|---|
| CA-F4-01 | Authentication opens the Sede Electrónica and selects Cl@ve PIN (Modelo B); verifies the authenticated NIF matches `perfil.nif` |
| CA-F4-02 | Navigates to the Modelo 303 form and selects the correct ejercicio/período; verifies Pre303 pre-fill (if available) and pre-filled NIF/name match the profile |
| CA-F4-03 | Fills casillas 01-27 (devengado: per-rate breakdown, ISP 12-13, modificación 14-15) correctly from the casilla map, leaving inapplicable rate blocks blank (not zero) |
| CA-F4-04 | Fills casillas 28-45 (deducible: corriente 28-29, inversión 30-31, importación 32-35, intracomunitario 36-37, rectificación 40-41, otras 42-44) correctly from the casilla map |
| CA-F4-05 | Fills the result block (46, 66, 69, 70, 71/72/110 as applicable) marking positive "a ingresar" vs negative "a compensar"/"a devolver" correctly, including 4T devolución vs compensación choice |
| CA-F4-06 | AEAT's own "Validar" step returns no errors for profile-1 seed data before submission is attempted |
| CA-F4-07 | Detects T04-E1 (período ya presentado) without re-submitting, and without losing any already-entered form data |
| CA-F4-08 | Detects T04-E4 (presentación fuera de plazo / general submission failure) with state persistence and a retry path that does not duplicate a partial submission |
| CA-F4-09 | On successful submission, downloads and verifies the justificante PDF (NIF, modelo, período, CSV, resultado all match the submitted values) and stores it in Supabase Storage |
| CA-F4-10 | The selector map (`src/rpa/selectors/aeat_m303.yml`) is a separate file from all Python code and is hot-swappable — no code change is required when AEAT updates its UI, only the YAML |

## References

- `docs/Autonomos.io/3. SDD/specs/fases_desarrollo_criterios_aceptacion_MVP_2.md` §6 (SPEC-F4-01..05, CA-F4-01..10)
- `docs/Autonomos.io/1. ANALISIS FUNCIONAL/.md/P04_IVA_trimestral_v1_completo_1.md` — Bloque 5/6 (T04-15..T04-26), T04-E1..E4, casuísticas C01-C11 (Hoja 5)
- `docs/backend-standards.md` — RPA project structure, external selector map rule, mock-in-tests rule
- `docs/domain-context.md` — casilla glossary, Cl@ve PIN, CSV, NRC
- `docs/api-spec.yml` — `ProcesoEstado` schema, `ResultadoM303.casillas` contract
- `docs/data-model.md` — `presentacion` table (already has every column F4 needs, no migration expected)
- `specs/archive/agente-conversacional/design.md` — F3's `EstadoP04`, `notificar` node, the confirmed-but-unfiled handoff gap
- `openspec/config.yaml` — `fiscal_integrity_checks`, `out_of_scope` (Modelo A exclusion)
