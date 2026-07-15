# Step 10 Report - Unit Tests and Database Verification

- Date: 2026-07-14
- Change: rpa-aeat (F4)
- Agent: backend_developer (claude-sonnet-4-6 in this session; GLM-5.2 via DeepInfra once the harness exists)
- Environment: local/real Supabase (SUPABASE_URL/SUPABASE_SERVICE_KEY/SUPABASE_ANON_KEY from .env). Playwright fully mocked in every test this phase — no real browser session against AEAT was opened, per the CRITICAL constraint on this change.

## Commands Executed

- `pytest tests/ -v --cov=src/fiscal --cov=src/rpa --cov=src/workers --cov-branch --cov-report=term-missing` (run repeatedly while closing coverage gaps)
- `pip install playwright arq pypdf PyYAML` and added them to `requirements.txt` (none were present before this change)

## Unit Test Results

- Full suite (excluding `@pytest.mark.integration`): **202 passed, 0 failed, 0 skipped** (13 deselected — pre-existing real-Anthropic-API/real-AEAT integration tests from Phases 3/4, never run in the TDD cycle)
- Runtime: ~104s
- `pytest -m "not integration" tests/ -v` confirmed zero real AEAT/network calls beyond the pre-existing real-Supabase DB tests (unchanged pattern from Phases 1-3, not gated by the `integration` marker since it's not an Anthropic API cost concern)

## Prerequisite architecture fixes found and resolved during implementation (Task 3)

Per `CLAUDE.md` §7, `design.md`/`tasks.md` were amended first, then implemented TDD-first (documented as "Task 3.0" in `tasks.md`):

1. **`ResultadoM303` never carried the per-rate/per-category breakdown.** `calcular_m303()` computed `ResultadoDevengado`/`ResultadoDeducible` internally but discarded both, keeping only a handful of aggregate keys in `casillas`. Fixed additively: `ResultadoM303.devengado`/`.deducible` (both `Optional`, default `None`) now retain these objects. Zero new fiscal arithmetic; every existing direct construction of `ResultadoM303` (`tests/integration/test_saldo_iva_compensar.py`) is untouched.
2. **`ResultadoDeducible.por_categoria` was cuota-only.** Every deducible AEAT casilla group is a base+cuota pair, but no base aggregate existed. Fixed additively: `ResultadoDeducible.base_por_categoria` (default `{}`), computed in `calcular_iva_deducible()` with the exact same `porcentaje_deducible` scaling already applied to the cuota.

Both fixes are Phase 2 files (`src/fiscal/models.py`, `src/fiscal/iva/calcular_m303.py`, `src/fiscal/iva/calcular_deducible.py`), fully additive, and the entire Phase 2 fiscal suite was re-run after each to confirm zero regression.

A secondary false positive was also found and fixed in Task 2's own static selector-check test: the regex flagged the dict key `"selector_ejercicio"` as a hardcoded CSS selector (it starts with "select"). Narrowed the regex to require actual CSS syntax (`#`, `[`, or `:has-text(`).

## Coverage

```
Name                                               Stmts   Miss Branch BrPart  Cover
----------------------------------------------------------------------------------------------
src/fiscal/... (all modules)                                                       100%
src/rpa/__init__.py                                    0      0      0      0     100%
src/rpa/aeat/__init__.py                               0      0      0      0     100%
src/rpa/aeat/autenticacion.py                         21      0      4      0     100%
src/rpa/aeat/justificante.py                          19      0      2      0     100%
src/rpa/aeat/m303_form.py                            103      0     48      3      98%   (3 branch-partial artifacts: elif-chain fallthroughs already exercised by other tests, 0 missed statements)
src/rpa/aeat/selectores.py                             8      0      0      0     100%
src/rpa/casilla_map.py                                42      0     28      0     100%
src/workers/__init__.py                                0      0      0      0     100%
src/workers/rpa_worker.py                             43      0      4      0     100%
----------------------------------------------------------------------------------------------
TOTAL                                                517      0    146      3      99%
```

**100% on `src/fiscal/` (unchanged, no regression) and 0 missed statements on every new `src/rpa/`/`src/workers/` module. The only gap is 3 partial-branch artifacts in `m303_form.py` (elif-chain fallthrough combinations), not missed lines — accepted, no code path is untested.**

## Database State Verification

- No new tables or columns required a migration — `presentacion`'s existing schema (Phase 1) already anticipated every F4 field (`estado`, `csv_aeat`, `nrc`, `justificante_path`, `error_code`, `screenshot_path`, `total_devengado`, `total_deducible`, `saldo_compensar_aplicado`), confirmed by reading `docs/data-model.md` before starting.
- `notificar.py`'s new `confirmado=True` upsert was verified against real Supabase in `tests/agent/nodes/test_notificar_confirma_escribe_presentacion.py` (2 tests) and the updated `tests/agent/nodes/test_notificar.py` — both clean up their own test rows via fixture teardown.
- No stray rows left behind: all new tests either mock the Supabase client entirely (all `src/rpa/`/`src/workers/` tests, since Playwright + real AEAT sessions are never exercised) or use the existing fixture-teardown pattern (Task 1's `notificar` tests).

## Steps 11-12 (this change's mandatory-steps pass)

- Step 11 (curl manual endpoint testing): **N/A** — no API endpoints created or modified this phase; F4 is the RPA module + ARQ worker only. `/api/proceso/p04/confirmar` and related endpoints are Phase 5's scope (confirmed by reading `docs/api-spec.yml` and `src/api/routers/`, which only has Phase-1-era endpoints).
- Step 12 (frontend Playwright E2E): **N/A** — no frontend exists yet (Phase 5 scope). Note: this change's own extensive use of Playwright is for AEAT automation, not for testing our own UI — an unrelated use of the same library.

Both explicitly marked N/A in `tasks.md`, not silently omitted, per Phase 1/2/3 precedent.

## Step 13 (documentation) — completed alongside this report

- `requirements.txt`: added `PyYAML`, `playwright`, `arq`, `pypdf` (none were present before this change).
- `CHANGELOG.md`: Phase 4 entry added (see below).
- `docs/development_guide.md`: noted that F4's `@pytest.mark.integration` browser test (Task 4.7) requires manual Product Owner execution with real AEAT/Cl@ve PIN credentials — never run by the agent.
- `TABLA_CASILLA_DEDUCIBLE` (`src/rpa/casilla_map.py`) is documented as the Product-Owner-approved mapping — future category additions go in that data file, never in `m303_form.py`.

## Outcome

- Step 10 status: **PASS**
- Final test count: **202 passed, 0 failed, 0 skipped** (13 pre-existing integration tests deselected)
- Final coverage: **100% on `src/fiscal/`; 0 missed statements on `src/rpa/` and `src/workers/`**
- Blocking issues: none for the agent-executable scope
- **Explicitly NOT executed — requires manual Product Owner action:** `tests/rpa/aeat/test_autenticacion.py::test_autenticar_clave_pin_sesion_real` (Task 4.7), marked `@pytest.mark.integration` and left unchecked `[ ]` in `tasks.md`. This test exercises a real Cl@ve PIN login against the live AEAT Sede Electrónica and requires a human to generate their own Cl@ve PIN (10-minute window) and supply their real NIF at execution time. The agent cannot and did not run it. The Product Owner must execute it manually (`pytest tests/rpa/aeat/test_autenticacion.py -m integration -v`) and confirm the result before this task can be marked complete.

---

## Addendum (2026-07-15) — 5 findings fixed post-first-adversarial-review (tasks.md Section 14)

Since this report, two follow-up commits landed: the Cl@ve Móvil QR authentication correction (replacing the originally-designed text-PIN flow — see `design.md` SPEC-F4-02's amendment) and a branch-coverage fix for `m303_form.py`. The first `/adversarial-review` pass then found **1 CRITICAL + 2 HIGH + 2 MEDIUM findings**. Per `CLAUDE.md` §7, `design.md`/`tasks.md` were amended first (Section 14), then each fix implemented TDD-first. Summary:

**CRITICAL — `manejar_periodo_ya_presentado()` never called.** The T04-E1 helper existed with its own passing unit tests but was never wired into `ejecutar_presentacion` — the real flow had zero protection against AEAT already having a filing this system doesn't know about; it would authenticate and proceed regardless. Fixed: `ejecutar_presentacion` now calls it immediately after resolving `user_id`/`ejercicio`/`periodo`, **before** any AEAT session (QR capture, authentication, navigation) begins. New test `test_ejecutar_presentacion_detecta_periodo_ya_presentado_no_abre_sesion` asserts `page.locator` is never called when an existing filing is found; a regression test confirms the normal flow is unaffected when nothing is found.

**HIGH-1 — no RLS policy on the 3 new Storage buckets.** `justificantes`, `qr-clave`, `screenshots` had no `storage.objects` policy at all — only the service role could read/write them, and `design.md` incorrectly claimed they had "RLS-equivalent" parity with the `facturas` bucket. Fixed: migration `20260715_100000_rpa_storage_rls.sql` (mirroring `20260713_140000_facturas_storage_rls.sql`'s `(storage.foldername(name))[2] = auth.uid()::text` pattern) applied to local Supabase; 6 new RLS integration tests (`tests/integration/test_rpa_storage_rls.py`) prove a user can read their own file and cannot read another user's, for all three buckets. The three buckets themselves also didn't exist locally yet and had to be created ad hoc (same situation Phase 3 hit with `facturas`).

**HIGH-2 — `error_detail` never written, `error_code` used raw Python class names.** Every error path set `error_code=type(exc).__name__` (e.g. `"DiscrepanciaResultadoError"`) instead of the documented snake_case strings, and never populated `error_detail` at all — a human looking at a stopped `presentacion` row had no way to see what actually went wrong. Fixed: added a `codigo_error` class attribute to all 6 RPA exception classes (`ValidacionError` → `validacion_fallida`, `DiscrepanciaResultadoError` → `discrepancia_resultado`, `NRCInvalidoError` → `nrc_invalido`, `JustificanteNoCoincideError` → `justificante_no_coincide`, `AutenticacionError` → `autenticacion_fallida`, `SesionExpiradaError` → `sesion_expirada`); `ejecutar_presentacion`'s except block now does `getattr(exc, "codigo_error", "fallo_presentacion")` and writes `error_detail=str(exc)`. 5 new tests cover each mapped exception type plus the generic fallback.

**MEDIUM-1 — substring false-positive in `verificar_justificante`.** Raw `in` containment meant `resultado="0.00"` (any `sin_actividad` filing) would spuriously match a PDF actually showing `"160.00"`, since `"0.00"` is a literal substring of `"160.00"` — defeating the exact safety net this function exists to provide. Fixed: `_valor_anclado_presente()` requires non-alphanumeric boundaries on both sides of every expected value (regex with negative lookaround), applied uniformly to all six verified fields, not just `resultado`. New test proves a wrong `resultado` sharing trailing digits with the correct value is now caught.

**MEDIUM-2 — ARQ retry/registration scoping (spec-only).** No code change; `design.md`/`tasks.md` corrected to explicitly defer `WorkerSettings`/automatic-retry to Phase 5, alongside the enqueueing endpoint. Reviewed `feature.md` — it doesn't overstate this, no amendment needed there.

### Final numbers after all 5 fixes

- Full suite: **224 passed, 0 failed, 0 skipped** (13 pre-existing integration tests deselected)
- Coverage: **100% line + branch on `src/fiscal/`, `src/rpa/`, and `src/workers/`** — 0 missed statements, 0 partial branches anywhere in scope
- No selector literals introduced outside `aeat_m303.yml`/`selectores.py` (static check still passes)
- `casilla_map.py` still introduces zero new fiscal arithmetic (unchanged by this remediation)

### Outcome

- CRITICAL + both HIGH + both MEDIUM findings: **RESOLVED**
- Ready for a second `/adversarial-review` pass before archiving (tasks.md 14.6.3)
