# Tasks: agente-conversacional

`openspec/config.yaml` read: yes. `docs/openspec-tasks-mandatory-steps.md` read: yes. Branch naming: `feature/agente-conversacional` per config. Agent: `backend_developer` (model `claude-sonnet-4-6` per `openspec/config.yaml`; GLM-5.2 via DeepInfra once the harness exists). No frontend work in this change — Step 15 (E2E Playwright) is not applicable and is explicitly marked skipped, not omitted, per the Phase 1/2 precedent.

**Blocking prerequisite — read before starting implementation:** unlike Phases 1-2, several tasks below (`recopilar_datos`, `ocr_factura`, `resumir`, and the CA-F3-10 token-budget test) make **real calls to the Claude Sonnet 5 API** and cannot be executed without a populated `ANTHROPIC_API_KEY` in `.env` (currently blank — Phase 1/2 never needed it). The agent implementing this change must either obtain a real key before Steps 5, 6, 7, and 12, or stop and report this blocker explicitly rather than mark those steps `[x]` without having actually run them — per `docs/openspec-tasks-mandatory-steps.md` §3, tasks can only be marked complete after the agent itself executed the test.

## 0. Setup: Create Feature Branch (MANDATORY — FIRST STEP)

- [x] 0.1 Create feature branch `feature/agente-conversacional` from `main`
- [x] 0.2 Verify branch creation: `git branch --show-current`

## 1. Backend: Fix `docs/backend-standards.md` Naming Conflict

Acceptance criteria: prerequisite for CA-F3-01 (no ambiguity about where the graph lives)

- [x] 1.1 Update `docs/backend-standards.md` "Project structure" section: move `graphs/p04_graph.py` and `state.py` out of the `agents/` block into a new `agent/` (singular) block, per `design.md` folder structure
- [x] 1.2 Add a one-line clarification above the `agents/` (plural) block: "external build-time-only harness — see CLAUDE.md §5, not part of the shipped product"

## 2. Backend: State Definition — TDD

Acceptance criteria: CA-F3-01

- [x] 2.1 Write failing test `test_estado_p04_shape.py`: construct a minimal valid `EstadoP04` dict with all required keys, assert no `KeyError` when accessed by each node's expected fields (a structural smoke test, not a Pydantic model — `EstadoP04` is a `TypedDict`, not runtime-validated)
- [x] 2.2 Verify test fails: `pytest tests/agent/test_estado_p04_shape.py -v`
- [x] 2.3 Implement `src/agent/state.py` (`EstadoP04`, `MensajeChat`) per `design.md` SPEC-F3-01
- [x] 2.4 Run test — must pass: `pytest tests/agent/test_estado_p04_shape.py -v`

## 3. Backend: `detectar_periodo` Node — TDD

Acceptance criteria: CA-F3-02

- [x] 3.1 Write failing tests with mocked `date.today()`: `test_detectar_periodo_abril_detecta_1t`, `_julio_detecta_2t`, `_octubre_detecta_3t`, `_enero_detecta_4t_ano_anterior`
- [x] 3.2 Verify tests fail: `pytest tests/agent/nodes/test_detectar_periodo.py -v`
- [x] 3.3 Implement `src/agent/nodes/detectar_periodo.py` — pure function of the current date, no LLM/DB call, includes national-holiday/weekend deadline shift per Hoja 3 T04-01
- [x] 3.4 Run tests — all must pass: `pytest tests/agent/nodes/test_detectar_periodo.py -v`

## 4. Backend: `verificar_duplicado` Node — TDD (Integration)

Acceptance criteria: CA-F3-09

- [x] 4.1 Write failing integration test `test_verificar_duplicado_encuentra_presentacion_existente` against local Supabase: seed a `presentacion` row for a test user/period, verify `presentacion_duplicada=True` and `csv_presentacion_previa` returned
- [x] 4.2 Write failing integration test `test_verificar_duplicado_sin_presentacion_previa`
- [x] 4.3 Verify tests fail: `pytest tests/agent/nodes/test_verificar_duplicado.py -v`
- [x] 4.4 Implement `src/agent/nodes/verificar_duplicado.py` per `design.md` SPEC-F3-07
- [x] 4.5 Run tests — all must pass: `pytest tests/agent/nodes/test_verificar_duplicado.py -v`

## 5. Backend: System Prompt + `recopilar_datos` Node — TDD

Acceptance criteria: CA-F3-04, CA-F3-08. **Requires real `ANTHROPIC_API_KEY` — see blocking prerequisite above.**

- [x] 5.1 Write `src/agent/prompts/p04_system_prompt.py` per `design.md` SPEC-F3-04 (role, hard constraints from `docs/domain-context.md`, glossary boundary, summary template, dudoso-confirmation phrasing verbatim from Hoja 3 T04-07)
- [x] 5.2 Write failing test `test_recopilar_datos_clasifica_restaurante_requiere_confirmacion` — a restaurant expense mentioned in conversation must set `requiere_confirmacion=True` on the resulting factura entry
- [x] 5.3 Write failing test `test_recopilar_datos_clasifica_software_no_requiere_confirmacion`
- [x] 5.4 Write failing test `test_recopilar_datos_detecta_sin_actividad` (casuística C01): user states no operations this quarter → `sin_actividad=True` after explicit confirmation exchange
- [x] 5.5 Verify tests fail: `pytest tests/agent/nodes/test_recopilar_datos.py -v`
- [x] 5.6 Implement `src/agent/nodes/recopilar_datos.py` (Claude Sonnet 5 call using the system prompt; never invents fiscal terms outside `docs/domain-context.md`'s glossary)
- [x] 5.7 Run tests — all must pass: `pytest tests/agent/nodes/test_recopilar_datos.py -v`

## 6. Backend: OCR Module + `ocr_factura` Node — TDD

Acceptance criteria: CA-F3-03. **Requires real `ANTHROPIC_API_KEY` (Claude Vision) — see blocking prerequisite above.**

- [x] 6.1 Write failing test `test_extraer_factura_ocr_factura_limpia_confianza_alta`: a clean test invoice PDF extracts NIF emisor, fecha, base imponible, tipo IVA all with confidence > 0.8
- [x] 6.2 Write failing test `test_extraer_factura_ocr_imagen_baja_calidad_confianza_baja`: a deliberately low-quality/blurry test image yields confidence < 0.8 on at least one field
- [x] 6.3 Write failing test `test_ocr_factura_node_marca_baja_confianza_para_revision`: the node adds low-confidence extractions to `facturas_baja_confianza`, never auto-accepts them into `facturas_emitidas`/`facturas_recibidas`
- [x] 6.4 Verify tests fail: `pytest tests/agent/test_ocr.py tests/agent/nodes/test_ocr_factura.py -v`
- [x] 6.5 Implement `src/agent/ocr.py` (`extraer_factura_ocr`) and `src/agent/nodes/ocr_factura.py` per `design.md` SPEC-F3-05
- [x] 6.6 Run tests — all must pass: `pytest tests/agent/test_ocr.py tests/agent/nodes/test_ocr_factura.py -v`
- [x] 6.7 **Mandatory contract fix (architecture review, Principle 1)**: `ocr_factura.py` must route `base_imponible`, `tipo_iva`, `cuota_iva` to `facturas_baja_confianza` unconditionally — not gated by the 0.8 threshold — since these feed `calcular_m303()` directly. Non-fiscal fields keep the confianza < 0.8 rule. See `design.md` SPEC-F3-05 amendment.
- [x] 6.8 Update `test_ocr_factura_node_acepta_extraccion_alta_confianza` → `test_ocr_factura_node_campos_fiscales_siempre_requieren_confirmacion`: assert base_imponible/tipo_iva are flagged even at confianza 0.99, and the invoice is never auto-accepted
- [x] 6.9 Add the equivalent hard constraint to `src/agent/prompts/p04_system_prompt.py` and update any doc wording ("revisión recomendada/opcional") in `docs/Autonomos.io/0. REQUERIMIENTOS/PDR.md` that describes OCR review as optional
- [x] 6.10 Run full suite with coverage — must remain 100% on `src/agent/`: `pytest tests/ -v --cov=src/fiscal --cov=src/agent --cov-branch --cov-report=term-missing`

## 7. Backend: `calcular` Node — TDD

Acceptance criteria: supports CA-F3-05 (feeds `resumir`), no new fiscal logic (calls Phase 2's `calcular_m303()` only)

- [x] 7.1 Write failing test `test_calcular_node_delega_a_calcular_m303`: verify the node's output `resultado_m303` matches calling `calcular_m303()` directly with the same inputs — proves no duplicate/reimplemented fiscal arithmetic exists in `src/agent/`
- [x] 7.2 Write failing test `test_calcular_node_sin_actividad_facturas_vacias` (casuística C01 path from `design.md`'s design note: empty invoice lists still produce a valid `sin_actividad` result via the same `calcular_m303()` call)
- [x] 7.3 Verify tests fail: `pytest tests/agent/nodes/test_calcular.py -v`
- [x] 7.4 Implement `src/agent/nodes/calcular.py` — thin wrapper: deserializes state dicts to Pydantic models, calls `calcular_m303()`, serializes the result back into `EstadoP04`'s JSON-safe shape
- [x] 7.5 Run tests — all must pass: `pytest tests/agent/nodes/test_calcular.py -v`

## 8. Backend: `resumir` Node — TDD

Acceptance criteria: CA-F3-05. **Requires real `ANTHROPIC_API_KEY` — see blocking prerequisite above.**

- [x] 8.1 Write failing test `test_resumir_incluye_todos_los_campos_requeridos`: given a `resultado_m303`, the produced `mensaje_resumen` contains total IVA repercutido, total deducible, resultado final, invoice count, and `fecha_limite_presentacion` — assert each value's string representation appears in the message
- [x] 8.2 Write failing test `test_resumir_usa_lenguaje_humano_no_casillas`: assert the message does not contain raw casilla references like "casilla 27" as the primary phrasing (per SPEC-F3-04's template)
- [x] 8.3 Verify tests fail: `pytest tests/agent/nodes/test_resumir.py -v`
- [x] 8.4 Implement `src/agent/nodes/resumir.py` using the template from `design.md` SPEC-F3-04
- [x] 8.5 Run tests — all must pass: `pytest tests/agent/nodes/test_resumir.py -v`

## 9. Backend: `confirmar` Node + Checkpointing — TDD

Acceptance criteria: CA-F3-06, CA-F3-07

- [x] 9.1 Write failing test `test_confirmar_interrumpe_el_grafo`: invoking the compiled graph up to `confirmar` raises/returns the LangGraph interrupt signal rather than completing
- [x] 9.2 Write failing integration test `test_confirmar_resume_confirmado_persiste_thread`: resume with `Command(resume={"accion": "confirmar"})` on the same `thread_id`, verify `confirmado=True` and the checkpoint round-trips through the real local Supabase Postgres via `PostgresSaver`
- [x] 9.3 Write failing integration test `test_confirmar_resume_revisar_vuelve_a_recopilar_datos`: resume with `{"accion": "revisar"}`, verify the graph routes back to `recopilar_datos` and `facturas_emitidas`/`facturas_recibidas` already collected are NOT cleared (CA-F3-07)
- [x] 9.4 Write failing integration test `test_confirmar_resume_cancelar_marca_presentacion_cancelado`: resume with `{"accion": "cancelar"}`, verify `presentacion.estado='cancelado'` is written and the graph run ends
- [x] 9.5 Write failing integration test `test_checkpoint_recupera_estado_exacto_tras_interrupcion`: start a run, let it interrupt at `confirmar`, simulate a process restart (new graph instance, same `checkpointer`), resume with the same `thread_id`, assert the recovered state's `facturas_emitidas`/`resultado_m303`/`mensaje_resumen` are byte-for-byte identical to pre-interrupt state (CA-F3-06)
- [x] 9.6 Verify tests fail: `pytest tests/agent/nodes/test_confirmar.py tests/agent/test_checkpointing.py -v`
- [x] 9.7 Implement `src/agent/checkpointer.py` (`PostgresSaver` against `SUPABASE_DB_URL`) and `src/agent/nodes/confirmar.py` per `design.md` SPEC-F3-06
- [x] 9.8 Run tests — all must pass: `pytest tests/agent/nodes/test_confirmar.py tests/agent/test_checkpointing.py -v`

## 10. Backend: `notificar` Node — TDD

- [x] 10.1 Write failing test `test_notificar_confirmado_no_modifica_presentacion` (Phase 4 owns the actual filing/write — this phase only hands off)
- [x] 10.2 Write failing test `test_notificar_cancelado_actualiza_estado_bd`
- [x] 10.3 Verify tests fail: `pytest tests/agent/nodes/test_notificar.py -v`
- [x] 10.4 Implement `src/agent/nodes/notificar.py`
- [x] 10.5 Run tests — all must pass: `pytest tests/agent/nodes/test_notificar.py -v`

## 11. Backend: Graph Wiring — TDD

Acceptance criteria: CA-F3-01

- [x] 11.1 Write failing test `test_grafo_instancia_sin_errores`: `StateGraph` compiles without raising
- [x] 11.2 Write failing test `test_grafo_todos_los_nodos_conectados`: every node from `design.md` SPEC-F3-02 is present in the compiled graph and reachable from `START`
- [x] 11.3 Write failing test `test_grafo_sin_nodos_inalcanzables`: no node declared is unreachable given the conditional edges in SPEC-F3-03
- [x] 11.4 Verify tests fail: `pytest tests/agent/test_graph.py -v`
- [x] 11.5 Implement `src/agent/graph.py` wiring all nodes and conditional edges per `design.md` SPEC-F3-03
- [x] 11.6 Run tests — all must pass: `pytest tests/agent/test_graph.py -v`

## 12. Backend: Full Flow + Token Budget — TDD

Acceptance criteria: CA-F3-10. **Requires real `ANTHROPIC_API_KEY` and `LANGSMITH_API_KEY` — see blocking prerequisite above.**

- [x] 12.1 Write failing end-to-end test `test_flujo_completo_perfil_1_token_budget`: run the graph from `detectar_periodo` through `confirmar` (resumed with `accion=confirmar`) for seed profile 1, read the LangSmith run's total token count, assert `<= 20000`
- [x] 12.2 Verify test fails (or is skipped with a clear reason if no API key is available yet): `pytest tests/agent/test_flujo_completo.py -v`
- [x] 12.3 Run the full flow for real once the graph is wired — no new implementation needed here, this step validates integration, not a new unit
- [x] 12.4 Run test — must pass within budget: `pytest tests/agent/test_flujo_completo.py -v`

## 13. Backend: Review and Update Existing Unit Tests (MANDATORY)

- [x] 13.1 Review Phase 1/2 tests in `tests/fiscal/` for regressions caused by nothing in this phase touching `src/fiscal/` directly — confirm the full Phase 1+2 suite still passes unmodified
- [x] 13.2 Confirm no test in `tests/agent/` duplicates `tests/fixtures/facturas.py` — reuse it for seed-profile-based flow tests (Task 12) exactly as Phase 2 did

## 14. Backend: Run Unit Tests and Verify Database State (MANDATORY — AGENT MUST EXECUTE)

Acceptance criteria: coverage requirement from `openspec/config.yaml` (100% on `src/fiscal/`; `src/agent/` is new — same 100% bar applies per the project's own precedent, excluding lines that only execute with a live Anthropic API key, which must be documented explicitly if skipped)

- [x] 14.1 Capture pre-test Supabase state (row counts for all 6 tables)
- [x] 14.2 Run targeted tests per new module (repeat the pattern from Phase 1/2 reports for each of: `state`, `detectar_periodo`, `verificar_duplicado`, `recopilar_datos`, `ocr`, `calcular`, `resumir`, `confirmar`, `checkpointing`, `notificar`, `graph`)
- [x] 14.3 Run full suite: `pytest tests/ -v --cov=src/fiscal --cov=src/agent --cov-branch --cov-report=term-missing`
- [x] 14.4 Verify coverage on `src/fiscal/` remains 100% (unaffected by this phase) and report `src/agent/` coverage explicitly, noting any lines only reachable with a live LLM call that could not be exercised
- [x] 14.5 Verify post-test database state: `presentacion` test rows are either cleaned up or documented as intentional
- [x] 14.6 Create report `specs/agente-conversacional/reports/YYYY-MM-DD-step-14-unit-test-and-db-verification.md`
- [x] 14.7 Mark this step complete only after coverage is confirmed and the report exists

## 15. Backend: Manual Endpoint Testing with curl (NOT APPLICABLE THIS PHASE)

- [x] 15.1 N/A — no API endpoints are created or modified this phase. The graph is invoked directly (via tests), not through `src/api/`. Explicitly marked N/A, not silently omitted, mirroring Phase 1/2 precedent for out-of-scope mandatory steps.

## 16. Frontend: E2E Testing with Playwright (NOT APPLICABLE THIS PHASE)

- [x] 16.1 N/A — no frontend exists yet. Explicitly marked N/A, not silently omitted, mirroring Phase 1/2 precedent.

## 17. Update Technical Documentation (MANDATORY)

- [x] 17.1 Confirm `docs/backend-standards.md`'s naming-conflict fix from Task 1 is complete and consistent with the rest of the document
- [x] 17.2 Update `docs/development_guide.md` if new environment variables or setup steps are needed (e.g. confirming `ANTHROPIC_API_KEY`/`LANGSMITH_API_KEY` are required starting this phase, unlike Phase 1/2)
- [x] 17.3 Update `CHANGELOG.md` with what Phase 3 delivered
- [x] 17.4 Note explicitly in documentation that Phase 4 (RPA) picks up from a `confirmado=True` state — this phase's graph does not file anything with AEAT

## 18. Post-Adversarial-Review Remediation (MANDATORY — 3 blockers found before archiving)

The adversarial review run before archiving this change found 3 blockers and 1 minor issue. Per CLAUDE.md §7, `design.md` and `tasks.md` were updated first (SPEC-F3-02, SPEC-F3-03, SPEC-F3-04, SPEC-F3-07, and the fiscal integrity checks section) — this section implements those amendments. TDD applies to every subtask below exactly as it did in Tasks 1-14.

### 18.1 — Blocker 1: `facturas_baja_confianza` resolution flow (fiscal integrity)

Acceptance: an OCR-flagged fiscal field, once confirmed by the user, reaches `calcular_m303()`'s input; the graph never routes to `calcular` while `facturas_baja_confianza` is non-empty. Design ref: SPEC-F3-02 amendment, SPEC-F3-03 amendment (routing + design note), SPEC-F3-04 item 6.

- [x] 18.1.1 Write failing test `test_ruta_tras_recopilar_datos_con_baja_confianza_va_a_recopilar_datos`: `_ruta_tras_recopilar_datos({"facturas_pendientes_ocr": [], "facturas_baja_confianza": [{...}]})` must return `"recopilar_datos"`, not `"calcular"`
- [x] 18.1.2 Write failing test `test_ruta_tras_recopilar_datos_ambos_vacios_va_a_calcular`: both empty still routes to `"calcular"` (regression guard)
- [x] 18.1.3 Verify tests fail: `pytest tests/agent/test_graph_routing.py -v`
- [x] 18.1.4 Update `_ruta_tras_recopilar_datos` in `src/agent/graph.py` to check `facturas_baja_confianza` per the amended SPEC-F3-03, and add the `recopilar_datos -> recopilar_datos` self-edge to `construir_grafo()`
- [x] 18.1.5 Run tests — must pass: `pytest tests/agent/test_graph_routing.py tests/agent/test_graph.py -v`
- [x] 18.1.6 Write failing test `test_recopilar_datos_confirmar_factura_baja_confianza_mueve_a_emitidas`: given a state with one `facturas_baja_confianza` entry for an `emitida` invoice with all its flagged fields, and a user message confirming the values, the resulting state has the entry removed from `facturas_baja_confianza` and a matching invoice appended to `facturas_emitidas`
- [x] 18.1.7 Write failing test `test_recopilar_datos_confirmar_factura_baja_confianza_permite_correccion`: the user supplies a corrected `valor_confirmado` different from the OCR-extracted value; the resulting invoice uses the corrected value, not the original
- [x] 18.1.8 Verify tests fail: `pytest tests/agent/nodes/test_recopilar_datos.py -v`
- [x] 18.1.9 Implement the `confirmar_factura_baja_confianza` tool and its handling in `_procesar_bloques_respuesta`/`recopilar_datos` per SPEC-F3-02 amendment; update `p04_system_prompt.py` per SPEC-F3-04 item 6
- [x] 18.1.10 Run tests — must pass: `pytest tests/agent/nodes/test_recopilar_datos.py -v`
- [x] 18.1.11 Write failing end-to-end integration test `test_flujo_ocr_baja_confianza_llega_a_calcular_m303`: OCR flags `base_imponible`/`tipo_iva` on a factura → simulate the user confirming both via a second `recopilar_datos` call → invoke `calcular` → assert the invoice's `base_imponible` is present in `calcular_m303()`'s actual input (not silently dropped)
- [x] 18.1.12 Verify test fails: `pytest tests/agent/test_flujo_baja_confianza.py -v`
- [x] 18.1.13 Run test — must pass once 18.1.4 and 18.1.9 are both in place: `pytest tests/agent/test_flujo_baja_confianza.py -v`

### 18.2 — Blocker 2: replace `SUPABASE_SERVICE_KEY` with user-scoped client (RLS)

Acceptance: no node in `src/agent/` uses the service role key; all four affected nodes query Supabase as the authenticated user, so RLS is the actual enforcement mechanism. Design ref: fiscal integrity checks amendment ("all Supabase queries in `src/agent/` use anon key + user JWT, never service role key").

- [x] 18.2.1 Write/extend failing RLS integration test(s) in `tests/integration/test_rls.py` (or a new `tests/agent/test_rls_agent_nodes.py`) proving user A's `EstadoP04` cannot read/write user B's `presentacion`/`perfil_fiscal`/`facturas_pendientes_ocr` Storage path through `verificar_duplicado`, `calcular`, `ocr_factura`, or `notificar` when each is given a client scoped to user A's JWT
- [x] 18.2.2 Verify tests fail (or cannot even run without a JWT-scoped client helper — document the failure mode): `pytest tests/agent/ -k rls -v`
- [x] 18.2.3 Add a shared helper (e.g. `src/agent/supabase_client.py::crear_cliente_usuario(jwt: str)`) building a Supabase client with the anon key + the user's JWT (`postgrest` auth header), mirroring the pattern already used by Phase 1/2's `tests/integration/test_rls.py`
- [x] 18.2.4 Replace `SUPABASE_SERVICE_KEY` usage in `verificar_duplicado.py`, `calcular.py`, `ocr_factura.py`, and `notificar.py` with the new user-scoped client; thread the user's JWT through `EstadoP04` (new field, e.g. `user_jwt: str`) since nodes only receive `estado`, not a request context
- [x] 18.2.5 Run tests — must pass: `pytest tests/agent/ -v --cov=src/agent --cov-branch --cov-report=term-missing`
- [x] 18.2.6 Grep verification: `grep -rn SUPABASE_SERVICE_KEY src/agent/` must return zero results
- [x] 18.2.7 Run full suite — coverage must remain 100% on `src/agent/`: `pytest tests/ -v --cov=src/fiscal --cov=src/agent --cov-branch --cov-report=term-missing`

### 18.3 — Blocker 3: surface `presentacion_duplicada` to the user (CA-F3-09)

Acceptance: when `presentacion_duplicada=True`, the agent's first message mentions the existing presentation and asks about a rectificativa; `quiere_rectificativa` is actually set from the user's answer. Design ref: SPEC-F3-04 item 7, SPEC-F3-07 amendment.

- [x] 18.3.1 Write failing integration test `test_recopilar_datos_informa_presentacion_duplicada_en_primer_mensaje`: given `presentacion_duplicada=True` and `csv_presentacion_previa` set, and an otherwise-empty `mensajes` history, the first assistant message produced by `recopilar_datos` mentions the existing presentation
- [x] 18.3.2 Write failing test `test_recopilar_datos_declarar_intencion_rectificativa_establece_estado`: a user message answering "sí, quiero rectificativa" results in `quiere_rectificativa=True` in the returned state
- [x] 18.3.3 Verify tests fail: `pytest tests/agent/nodes/test_recopilar_datos.py -v`
- [x] 18.3.4 Update `construir_system_prompt()` to accept `presentacion_duplicada`/`csv_presentacion_previa` and render SPEC-F3-04 item 7's disclosure instruction; update `recopilar_datos()` to pass these from `estado` on every call; add the `declarar_intencion_rectificativa` tool
- [x] 18.3.5 Run tests — must pass: `pytest tests/agent/nodes/test_recopilar_datos.py -v`
- [x] 18.3.6 Run full suite with coverage: `pytest tests/ -v --cov=src/fiscal --cov=src/agent --cov-branch --cov-report=term-missing`

### 18.4 — Minor: `notificar` confirmado message must not imply filing has started

Design ref: SPEC-F3-02 `notificar` row amendment.

- [x] 18.4.1 Update the `confirmado` branch's message in `src/agent/nodes/notificar.py` to neutral phrasing that does not imply AEAT filing is underway (e.g. "Confirmación registrada. Tu declaración está lista y pendiente de presentación.")
- [x] 18.4.2 Update/assert in `tests/agent/nodes/test_notificar.py` that the message does not contain "presentando" or similar filing-in-progress language
- [x] 18.4.3 Run tests — must pass: `pytest tests/agent/nodes/test_notificar.py -v`

### 18.5 — Full regression + second adversarial pass readiness

- [x] 18.5.1 Run full suite: `pytest tests/ -v --cov=src/fiscal --cov=src/agent --cov-branch --cov-report=term-missing` — confirm 100% line+branch on `src/fiscal/` and `src/agent/`
- [x] 18.5.2 Update the Step 14 report (or add an addendum) noting the 3 blockers fixed and the new test count/coverage
- [x] 18.5.3 Re-run `/adversarial-review` before archiving — **done, result: FAIL (1 CRITICAL, 2 MEDIUM, 2 LOW)**. Per this section's own exit criterion, a FAIL does not satisfy "clean second pass" — see Section 18.6 for the remediation this triggered. This subtask is checked because the review itself was executed as required, not because its outcome was clean.

### 18.6 — CRITICAL fix: replace the `recopilar_datos` self-edge with a real `interrupt()` (second adversarial-review finding)

The second adversarial-review pass found the 18.1 fix for Blocker 1 introduced a new CRITICAL regression: the bare `recopilar_datos -> recopilar_datos` self-edge is not a LangGraph pause point, so a single `graph.invoke()` re-executes `recopilar_datos` (full Claude Sonnet 5 call included) immediately and repeatedly whenever `facturas_baja_confianza` remains unresolved — empirically confirmed to make 10,000+ calls before crashing with `GraphRecursionError`. This also retraps the pre-existing `ocr_factura -> recopilar_datos` edge, making the whole OCR flow unusable end-to-end through the real compiled graph. Design updated first (SPEC-F3-02 amendment, SPEC-F3-03 routing + design note, SPEC-F3-06 new "Interrupt in a loop" subsection, fiscal integrity checks) per CLAUDE.md §7 — this section implements those amendments.

Also folds in the second review's 2 MEDIUM findings, both resolved as a natural consequence of this redesign (see design.md): the system prompt's OCR-confirmation/duplicate-disclosure priority contradiction is resolved by removing the OCR-confirmation prompt item entirely (it's structural now, not conversational); JWT expiry across a long `interrupt()` pause is documented as a known limitation with a Phase 5 TODO (no code fix required this phase).

- [x] 18.6.1 Write failing test(s) proving the CRITICAL bug is fixed: drive the **compiled graph** (not `recopilar_datos()` directly) through a scenario where `facturas_baja_confianza` has a pending entry after `ocr_factura` runs; assert the first `graph.invoke()` returns with `"__interrupt__"` in the result (a genuine pause) instead of raising `GraphRecursionError` or looping
- [x] 18.6.2 Write failing test asserting the resume path: `graph.invoke(Command(resume={"confirmaciones": [...]}), config=...)` on the same thread resolves the pending field(s) and the invoice reaches `facturas_emitidas`/`facturas_recibidas`
- [x] 18.6.3 Write failing test for the multi-round case: a resume that only answers *some* pending fields must interrupt again with the remaining ones, not raise or silently drop them
- [x] 18.6.4 Write failing test proving the LLM is called at most once per `recopilar_datos` invocation and never as a side effect of resuming a field confirmation (e.g., assert the mocked Anthropic client's `messages.create` call count doesn't increase across a pure confirmation-resume cycle)
- [x] 18.6.5 Verify tests fail: `pytest tests/agent/ -k baja_confianza -v`
- [x] 18.6.6 Implement: rewrite `recopilar_datos()` per the SPEC-F3-02 amendment (`while` loop of `interrupt()` calls before the LLM call, `habia_pendientes` early return, no LLM call on the confirmation-only path); remove `confirmar_factura_baja_confianza` from `_TOOLS`; remove the `facturas_baja_confianza` branch and the self-edge from `graph.py`'s `_ruta_tras_recopilar_datos` and `construir_grafo()`
- [x] 18.6.7 Update `p04_system_prompt.py`: remove the OCR-field-confirmation prompt item and `_pendientes_baja_confianza()` helper (dead now — the LLM never sees this), keep the duplicate-disclosure priority instruction as the sole priority claim
- [x] 18.6.8 Update/replace `tests/agent/test_flujo_baja_confianza.py`: the existing test calls `recopilar_datos()` directly with a mocked Anthropic client and never exercises `interrupt()` at all — rewrite it to drive the compiled graph through the real two-invocation (or multi-invocation) interrupt/resume cycle, per SPEC-F3-06
- [x] 18.6.9 Run tests — must pass: `pytest tests/agent/ -k "baja_confianza or graph" -v`
- [x] 18.6.10 Run full suite with coverage — must remain 100% on `src/agent/`: `pytest tests/ -v --cov=src/fiscal --cov=src/agent --cov-branch --cov-report=term-missing`
- [x] 18.6.11 Update the Step 14 report addendum with the CRITICAL fix, the 2 MEDIUM resolutions, and final test count/coverage
- [ ] 18.6.12 Re-run `/adversarial-review` (third pass) before archiving — exit criterion is a clean pass (PASS or PASS WITH GAPS, no CRITICAL/HIGH blockers)

## Exit criteria (Orchestrator evaluates before accepting this change)

- All tasks above checked `[x]`, OR explicitly documented as blocked on `ANTHROPIC_API_KEY`/`LANGSMITH_API_KEY` with no other work silently skipped
- `pytest tests/ --cov=src/fiscal --cov=src/agent --cov-branch` reports 100% on `src/fiscal/` (unchanged) and full coverage on `src/agent/` except lines explicitly documented as requiring a live LLM call
- The unit-test-and-db-verification report exists under `specs/agente-conversacional/reports/`
- The graph compiles, all nodes reachable, no orphan nodes (CA-F3-01)
- `confirmar`'s `interrupt()` is the only path to `confirmado=True` — verified by code review, not just tests
- Checkpointing round-trip verified against real local Supabase Postgres, not mocked
- No out-of-scope items implemented: Phase 4 RPA, chat UI, P04-R rectificativa filing, anything from `openspec/config.yaml` → `out_of_scope`
- **No blockers remain from the adversarial review**: `facturas_baja_confianza` entries are resolvable and reach `calcular_m303()`'s input (Task 18.1); no `src/agent/` node uses `SUPABASE_SERVICE_KEY` (Task 18.2); `presentacion_duplicada` is surfaced to the user and `quiere_rectificativa` is actually set (Task 18.3); `notificar`'s messaging does not imply filing has started (Task 18.4)
- **No blockers remain from the second adversarial review**: `recopilar_datos` resolves `facturas_baja_confianza` via a real `interrupt()` loop, never a bare self-edge; driving the compiled graph through a pending-confirmation scenario returns a genuine pause (`"__interrupt__"`), not a `GraphRecursionError`; the LLM is never called as a side effect of resuming a field confirmation (Task 18.6)
