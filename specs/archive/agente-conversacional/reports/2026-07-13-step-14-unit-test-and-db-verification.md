# Step 14 Report - Unit Tests and Database Verification

- Date: 2026-07-13
- Change: agente-conversacional
- Agent: backend_developer (claude-sonnet-4-6 in this session; GLM-5.2 via DeepInfra once the harness exists)
- Environment: local Supabase (Docker) + real Claude Sonnet 5 API (ANTHROPIC_API_KEY) + real LangSmith tracing (LANGSMITH_API_KEY)

## Commands Executed

- `pytest tests/ -v --cov=src/fiscal --cov=src/agent --cov-branch --cov-report=term-missing` (run multiple times while closing coverage gaps and after the mandatory OCR contract fix)
- `docker exec supabase_db_autonomos-ia-mvp psql ... SELECT COUNT(*) ...` (pre/post baseline, all 6 tables)
- Supabase Storage: created the `facturas` bucket (previously did not exist) to close a real coverage gap in `_descargar_bytes`

## Unit Test Results

- Full suite: **130 passed, 0 failed, 0 skipped**
- Runtime: ~67s (includes real LLM calls in Steps 5/6/8/12 and real Postgres checkpointing in Step 9)
- Notes: no flaky tests observed across repeated runs; one LLM-behavior ambiguity was found and fixed during Step 5 (system prompt didn't unambiguously require registering a dudoso expense in the same turn as asking for confirmation — fixed by making the instruction explicit; verified consistent across 3 repeated runs after the fix)

## Mandatory contract fix applied during this step (architecture review)

**Problem:** OCR numeric fields feeding `calcular_m303()` (`base_imponible`, `tipo_iva`, `cuota_iva`) only went to `facturas_baja_confianza` when confidence < 0.8, meaning a confident-but-wrong OCR reading of a fiscal amount could reach the fiscal engine without user review — a violation of Principle 1 (legal correctness before speed).

**Fix (3 changes, tracked as tasks 6.7–6.10 in `tasks.md`, design amendment in `design.md` SPEC-F3-05):**
1. `src/agent/nodes/ocr_factura.py` — `base_imponible`, `tipo_iva`, `cuota_iva` now always route to `facturas_baja_confianza` regardless of confidence (`CAMPOS_FISCALES_SIEMPRE_REVISAR`). Non-fiscal fields keep the confianza < 0.8 rule.
2. `src/agent/prompts/p04_system_prompt.py` — added the hard constraint that the user must explicitly confirm these three fields before they reach the fiscal engine, even at high OCR confidence.
3. `docs/Autonomos.io/0. REQUERIMIENTOS/PDR.md` — replaced "revisión recomendada"/"revisión opcional" wording with "confirmación obligatoria de campos numéricos fiscales" in both places it described OCR review.

**Consequence discovered and resolved:** because `base_imponible`/`tipo_iva` are required fields on every OCR extraction, the fix makes the old "auto-accept" branch in `ocr_factura()` permanently unreachable — no OCR-extracted invoice can ever bypass confirmation. Rather than leave that branch as dead/uncovered code, it was removed; `ocr_factura()` now always appends flagged fields to `facturas_baja_confianza` and never auto-populates `facturas_emitidas`/`facturas_recibidas`. `tests/agent/nodes/test_ocr_factura.py` was rewritten accordingly (the old `test_ocr_factura_node_acepta_extraccion_alta_confianza` was replaced with `test_ocr_factura_node_campos_fiscales_siempre_requieren_confirmacion`, asserting mandatory review even at confianza 0.99).

## Coverage

```
Name                                               Stmts   Miss Branch BrPart  Cover
----------------------------------------------------------------------------------------------
src/fiscal/... (all modules, unchanged from Phase 2)                              100%
src/agent/__init__.py                                  0      0      0      0   100%
src/agent/checkpointer.py                              6      0      0      0   100%
src/agent/graph.py                                    43      0      8      0   100%
src/agent/llm_client.py                                8      0      2      0   100%
src/agent/nodes/calcular.py                           15      0      2      0   100%
src/agent/nodes/confirmar.py                           5      0      0      0   100%
src/agent/nodes/detectar_periodo.py                   17      0      2      0   100%
src/agent/nodes/notificar.py                          14      0      4      0   100%
src/agent/nodes/ocr_factura.py                        23      0      4      0   100%
src/agent/nodes/recopilar_datos.py                    27      0     12      0   100%
src/agent/nodes/resumir.py                            14      0      0      0   100%
src/agent/nodes/verificar_duplicado.py                 8      0      2      0   100%
src/agent/ocr.py                                      15      0      4      0   100%
src/agent/prompts/p04_system_prompt.py                16      0      2      0   100%
src/agent/state.py                                     3      0      0      0   100%
----------------------------------------------------------------------------------------------
TOTAL                                                487      0    102      0   100%
```

**100% on both `src/fiscal/` (unchanged, no regression) and `src/agent/` (new this phase). No documented exceptions.**

Two gaps found and closed earlier in this step (not left as documented exceptions):
1. `ocr_factura.py:18-19` (`_descargar_bytes` body) — created the real `facturas` Supabase Storage bucket (did not exist locally) and added `tests/agent/nodes/test_ocr_factura_storage.py`, a genuine integration test against real Storage (upload + download, not mocked).
2. `recopilar_datos.py` branch (elif chain, unrecognized tool name) — extracted the block-parsing loop into a pure `_procesar_bloques_respuesta()` function and added 2 unit tests exercising both the "declarar_sin_actividad followed by another block" case and the "unrecognized tool_use name falls through silently" case.

A third gap opened and closed by the mandatory contract fix itself: removing the now-unreachable auto-accept branch in `ocr_factura()` (see above) rather than leaving it undercovered.

## Database State Verification

- Pre-test baseline (from Phase 2's last report): `perfil_fiscal`=0, `factura_emitida`=16, `factura_recibida`=8, `presentacion`=1, `saldo_iva_compensar`=0, `alerta`=0.
- Post-test state: identical — `perfil_fiscal`=0, `factura_emitida`=16, `factura_recibida`=8, `presentacion`=1, `saldo_iva_compensar`=0, `alerta`=0.
- State restored: **Yes** — all test fixtures in this phase (perfil_fiscal rows, presentacion rows, saldo_iva_compensar rows, Storage test file) clean up after themselves via fixture teardown; the `facturas` Storage bucket itself is a permanent, intentional addition (infrastructure, not test data).

## Steps 15–16 (this step's mandatory-steps pass)

- Step 15 (curl manual endpoint testing): **N/A** — no API endpoints created/modified this phase; the graph is invoked directly via tests, not through `src/api/`.
- Step 16 (frontend Playwright E2E): **N/A** — no frontend exists yet.

Both explicitly marked N/A in `tasks.md`, not silently omitted, per Phase 1/2 precedent.

## Step 17 (documentation) — completed alongside this report

- `docs/backend-standards.md`: confirmed the `src/agent/` (singular, runtime) vs. `src/agents/` (plural, build-time harness) naming fix is complete and consistent.
- `docs/development_guide.md`: added a note that `ANTHROPIC_API_KEY`/`LANGSMITH_API_KEY` are mandatory from Phase 3 onwards (Phases 1-2 never called an LLM), plus a `pytest tests/agent/` command block.
- `CHANGELOG.md`: added the Phase 3 entry (`agente-conversacional`) summarizing all deliverables, including the mandatory OCR contract fix.
- `docs/development_guide.md`: added an explicit "Key decisions" bullet noting Phase 3 stops at `confirmado=True` and Phase 4 (RPA, not yet built) picks up from that checkpointed state.

## Outcome (original Step 14 pass)

- Step 14 status: **PASS**
- Final test count: **130 passed, 0 failed, 0 skipped**
- Final coverage: **100% line + branch on `src/fiscal/` and `src/agent/`**
- Blocking issues: none

---

## Addendum (2026-07-13) — 3 blockers fixed post-adversarial-review (tasks.md Section 18)

The first `/adversarial-review` pass on this change found **3 blockers**. Per CLAUDE.md §7, `design.md`/`tasks.md` were updated first (Section 18), then each fix was implemented TDD-first. Summary:

**Blocker 1 — `facturas_baja_confianza` resolution flow (fiscal integrity).** OCR-flagged fiscal fields were never resolvable — routing didn't check the list, and nothing existed to move a confirmed field back into `facturas_emitidas`/`facturas_recibidas`, meaning every OCR-scanned invoice was silently and permanently dropped from the calculation. Fixed: `graph.py`'s routing now checks `facturas_baja_confianza`; `ocr_factura.py` now stores every extracted field (not just flagged ones) so accepted fields survive to assembly time; new `confirmar_factura_baja_confianza` tool in `recopilar_datos.py` resolves fields and assembles the completed invoice once all are cleared. A second bug was caught mid-fix via TDD: a hallucinated/stale tool call for a path with zero matching entries would have synthesized an **empty invoice** — guarded against before it shipped. New end-to-end test (`test_flujo_baja_confianza.py`) proves confirmed OCR data reaches the real `calcular_m303()` engine.

**Blocker 2 — RLS / service-role key (security).** All 4 Supabase-touching nodes (`verificar_duplicado`, `calcular`, `ocr_factura`, `notificar`) used `SUPABASE_SERVICE_KEY`, bypassing RLS entirely and relying solely on an application-level `.eq("user_id", ...)` filter with no database-level backstop. Fixed: new `src/agent/supabase_client.py::crear_cliente_usuario(jwt)` builds a client scoped to the authenticated user's own JWT; all 4 nodes switched to it; `EstadoP04` gained a `user_jwt` field. Discovered along the way that the `facturas` Storage bucket had **zero RLS policies** (service role was the only thing that had ever worked against it) — added migration `20260713_140000_facturas_storage_rls.sql` with per-user policies keyed on a new `{emitidas|recibidas}/{user_id}/{filename}` path convention, verified empirically before writing tests. Also hit a `storage3` library gotcha: its `SyncStorageClient` snapshots headers at construction time, so post-hoc header mutation silently no-ops — the client's cached storage instance had to be rebuilt with the JWT baked in from the start. New `tests/agent/test_rls_agent_nodes.py` proves cross-user access is blocked even when `estado["user_id"]` claims otherwise.

**Blocker 3 — `presentacion_duplicada` never surfaced to the user (CA-F3-09).** `verificar_duplicado` computed the flag but nothing downstream ever read it — the LLM was never told, so CA-F3-09 was unmet despite node-level tests passing. Fixed: `construir_system_prompt()` now accepts `presentacion_duplicada`/`csv_presentacion_previa` and instructs the LLM to disclose the duplicate in its first message; new `declarar_intencion_rectificativa` tool captures the user's answer into `quiere_rectificativa`. This also surfaced a supporting gap: `recopilar_datos()` never captured the assistant's plain-text reply into `mensajes` at all — fixed as a prerequisite, since there was otherwise no way to observe "the agent's first message."

**Minor — `notificar` messaging.** Changed "Confirmación registrada. Presentando ante la AEAT..." (implies filing is underway — false, this graph never files anything) to "Confirmación registrada. Tu declaración está lista y pendiente de presentación."

### Final numbers after all 4 fixes

- Full suite: **143 passed, 0 failed, 0 skipped**
- Coverage: **100% line + branch on both `src/fiscal/` and `src/agent/`** (`src/agent/` grew from 487 to 534 statements / 102 to 124 branches, all covered)
- DB state: verified clean — `perfil_fiscal`=0, `factura_emitida`=16, `factura_recibida`=8, `presentacion`=1, `saldo_iva_compensar`=0, `alerta`=0 (one stray `saldo_iva_compensar` row from earlier mid-fix debugging was found and removed before this final check)
- `grep -rn SUPABASE_SERVICE_KEY src/agent/` → zero results

### Outcome (first review's fixes)

- All 3 blockers + 1 minor: **RESOLVED**
- Ready for a second `/adversarial-review` pass before archiving (tasks.md 18.5.3)

---

## Addendum 2 (2026-07-13) — CRITICAL fix from second adversarial-review pass (tasks.md Section 18.6)

The second `/adversarial-review` pass found the 18.1 fix for Blocker 1 introduced a **CRITICAL** regression: the bare `recopilar_datos -> recopilar_datos` self-edge added to fix Blocker 1 is not a LangGraph pause point. A single `graph.invoke()` re-executed `recopilar_datos` (full Claude Sonnet 5 call included) immediately and repeatedly whenever `facturas_baja_confianza` remained unresolved after one pass — empirically reproduced to make **10,007 API calls** before crashing with `GraphRecursionError`. This also retrapped the pre-existing `ocr_factura -> recopilar_datos` edge, making the whole OCR confirmation flow unusable end-to-end through the real compiled graph, not just the newly-added self-edge. Also found: 2 MEDIUM issues (a system-prompt priority contradiction between OCR-field confirmation and duplicate-presentation disclosure; `user_jwt` expiry with no refresh handling across a long `interrupt()` pause).

**Fix (per CLAUDE.md §7, `design.md` updated first):**

- `recopilar_datos()` rewritten around a `while` loop of `interrupt()` calls positioned **strictly before** the Claude Sonnet 5 API call. Confirming an OCR-flagged field is now a structural gate (like `confirmar`'s own gate on `confirmado`), not an LLM tool call the model could simply skip.
- A `habia_pendientes` early return skips the LLM call entirely on a confirmation-only resume — verified explicitly (`cliente_mock.messages.create.assert_not_called()` across every confirmation-resolution test), which is what prevents the CRITICAL regression: resuming a field confirmation never triggers a redundant (or duplicate) LLM call.
- The `confirmar_factura_baja_confianza` LLM tool removed from `_TOOLS` entirely — the LLM never sees pending OCR fields at all now.
- `graph.py`: the self-edge and the `facturas_baja_confianza` routing branch removed from `_ruta_tras_recopilar_datos` and `construir_grafo()` — routing no longer needs to check it, since `recopilar_datos` guarantees it's empty before ever returning control.
- `p04_system_prompt.py`: removed the OCR-field-confirmation prompt item and the now-dead `_pendientes_baja_confianza()` helper — this is also what resolved the MEDIUM prompt-contradiction finding, since there's no longer a competing conversational priority against duplicate disclosure.
- JWT expiry (the other MEDIUM finding) documented as a known limitation in `design.md` SPEC-F3-06 with an explicit Phase 5 TODO — no code fix this phase, as decided in the design update.
- `tests/agent/test_flujo_baja_confianza.py` fully rewritten: the old version called `recopilar_datos()` directly with a mocked Anthropic client and never exercised `interrupt()` at all (the exact blind spot that let the CRITICAL regression ship undetected). It now drives a compiled graph (mirroring `test_confirmar.py`'s minimal-graph pattern) through the real two/three-invocation interrupt/resume cycle: initial interrupt, full-resolution resume, and a partial-resume-then-second-interrupt case.
- Empirically re-verified the exact repro script from the review against the fixed code: genuine `interrupt()` pause, zero LLM calls, no `GraphRecursionError`.

### Final numbers after the CRITICAL fix

- Full suite: **145 passed, 0 failed, 0 skipped**
- Coverage: **100% line + branch on both `src/fiscal/` and `src/agent/`** (`src/agent/` now 542 total statements / 124 branches project-wide, all covered; `recopilar_datos.py` alone grew to 73 statements / 32 branches)
- DB state: verified clean — `perfil_fiscal`=0, `factura_emitida`=16, `factura_recibida`=8, `presentacion`=1, `saldo_iva_compensar`=0, `alerta`=0

### Outcome

- CRITICAL finding + both MEDIUM findings: **RESOLVED**
- Ready for a third `/adversarial-review` pass before archiving (tasks.md 18.6.12)
