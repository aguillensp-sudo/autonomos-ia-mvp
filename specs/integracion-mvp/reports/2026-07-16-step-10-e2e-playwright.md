# Step 10 Report - Frontend E2E Testing with Playwright

- Date: 2026-07-16
- Change: integracion-mvp (F5)
- Agent: frontend_developer (claude-sonnet-5 in this session)
- Environment: local Supabase, local Redis, `uvicorn` backend, `npm run dev` frontend, ARQ worker — all already running from Task 9. Chromium installed via `npx playwright install chromium` (no browsers were installed in this environment before this step).

## Commands Executed

```bash
npx playwright install chromium
npx playwright test e2e/happy-path.spec.ts --reporter=list
npx playwright test e2e/ocr-upload.spec.ts --reporter=list
npx playwright test e2e/session-expiry.spec.ts --reporter=list
npx playwright test e2e/aeat-error.spec.ts --reporter=list
npx playwright test e2e/cancel-confirmacion.spec.ts --reporter=list
npx playwright test --reporter=list   # all 5 together
```

## Architectural correction found before writing any spec (10.0)

Task 9's own wording assumed a runtime "stub AEAT" mode existed for the RPA worker. It doesn't: Phase 4's stub fixtures (`tests/rpa/_stubs_aeat.py`) only mock Playwright's `Page` object inside pytest — the real, running `rpa_worker.py` has no stub switch and would launch a real Playwright browser against the real AEAT Sede Electrónica, requiring a real Cl@ve Móvil session (this is exactly what Claude Code's safety classifier correctly blocked in Task 9 when a live `/confirmar` curl call was attempted).

**Resolution:** every spec that reaches an RPA-outcome state (`presentando`/`presentado`/`sesion_expirada`/`failed`) intercepts the browser's own `POST /confirmar` call via Playwright's `page.route()` and fulfills a mocked `202`, then simulates the `presentacion` row transitions a real `rpa_worker.py` run would have written, directly via the Supabase admin client (`e2e/helpers/db.ts`, service-role key, test-only). This never lets a real job reach real AEAT, while still exercising `RpaStatus`'s real Realtime subscription and 4-state rendering — which is what CA-F5-01/03/04 actually require.

Test isolation: each spec creates its own throwaway Supabase user (`crearUsuarioDePrueba`), seeds a valid `perfil_fiscal`, cleans up `presentacion`/`alerta`/`factura_*`/LangGraph checkpoint rows before each test, and deletes the user afterward.

## Four more bugs found while writing the specs (10.0a-10.0d)

Per CLAUDE.md §7, design.md/tasks.md amended first (see the Task 10 amendment), then fixed:

1. **`RpaStatus.tsx`'s Realtime filter compared the wrong identifier** — same class of bug as Task 9's `/estado`/`/justificante` fix: `filter: id=eq.${procesoId}` can never match, since `procesoId` is the thread_id and `presentacion.id` is an unrelated UUID. The subscription silently never fired. Fixed: subscribe unfiltered (RLS scopes rows to the user) and re-fetch on any UPDATE.
2. **The "Ver justificante" link pointed at a frontend route that was never built.** Fixed: fetch the signed URL from the real backend endpoint on click, render a real anchor.
3. **The P04 page always restarted at the chat phase on mount**, even mid-RPA or after a failure — a reload lost the `RpaStatus` view entirely. Found writing `aeat-error.spec.ts`'s reload-persistence assertion. Fixed: check `/estado` after `/iniciar` and resume at `confirmado` if the process is already past `calculado`.
4. **A Base UI console error fired on every dashboard render** (`Button render={<Link/>}` without `nativeButton={false}`) — violates CA-F5-08. Fixed.

## Results

```
Running 5 tests using 5 workers
  ok ocr-upload.spec.ts (12.9s)
  ok cancel-confirmacion.spec.ts (25.7s)
  ok session-expiry.spec.ts (28.7s)
  ok happy-path.spec.ts (30.4s)
  ok aeat-error.spec.ts (34.0s)

5 passed (35.6s)
```

Also run individually (each passed standalone): happy-path 34.9s, ocr-upload 10.8s, session-expiry 37.6s, aeat-error 45.6s, cancel-confirmacion 25.7s-27.7s.

`happy-path.spec.ts`'s own timing log: `happy-path system steps completed in ~30-35s`. This is **not** comparable to CA-F5-01's real "5 minutes" framing, which is about a real Cl@ve Móvil session's wall-clock time — this measures only the system's own steps (chat round-trip through a real Claude Sonnet 5 call, calculate, confirm, and the simulated RPA-transition UI updates), correctly excluding any real AEAT interaction per the 10.0 amendment.

## Manual browser check (10.8)

Chrome (via the Claude Code Browser pane, Chromium-based): logged in, visited `/dashboard` and `/proceso/p04` — **zero console errors** after the 10.0d fix (confirmed both before the fix, reproducing the Base UI warning, and after).

**Safari: not available.** This is a Windows environment with no Safari installation — explicitly flagging this as an environment limitation rather than silently skipping or fabricating a check. If Safari verification is required, it needs to happen on macOS.

## Outcome

- Step 10 status: **PASS** (Safari check explicitly not executed — environment limitation, flagged above)
- 5/5 specs passing, both individually and together
- 1 architectural correction (no runtime stub-AEAT mode) + 4 real frontend bugs found and fixed, all spec-amended first per CLAUDE.md §7
- No real AEAT/Playwright-against-AEAT automation was triggered at any point in this task
