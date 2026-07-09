---
description: Enforce mandatory steps from openspec/config.yaml when creating tasks.md artifacts and ensure agent executes all manual tests
alwaysApply: true
---

# OpenSpec Tasks: Mandatory Steps Enforcement

When creating or updating `tasks.md` artifacts in OpenSpec changes, you MUST:

## 1. Read openspec/config.yaml First

**BEFORE** creating or updating any `tasks.md` file, you MUST read `openspec/config.yaml` to understand:
- Backend and frontend-specific mandatory steps
- Branch naming conventions (`feature/{change-name}`)
- Task structure requirements
- Testing commands and coverage thresholds
- What is out of scope for the MVP

## 2. Mandatory Steps

All implementation tasks MUST include these steps in the correct order:

### Step 0: Create Feature Branch (MUST BE FIRST)
- **Location**: Must be the very first step (Step 0)
- **Branch naming**: `feature/{change-name}` (from `openspec/config.yaml`)
- **Action**: Create and switch to feature branch before any code changes

### Mandatory Steps (Must Be Included):
- **Step N**: Review and Update Existing Unit Tests (MANDATORY)
- **Step N+1**: Run Unit Tests and Verify Database State (MANDATORY)
- **Step N+2**: Manual Endpoint Testing with curl (MANDATORY for backend) — **AGENT MUST EXECUTE**
- **Step N+3**: E2E Testing with Playwright (MANDATORY if frontend involved) — **AGENT MUST EXECUTE**
- **Step N+4**: Update Technical Documentation (MANDATORY)

## 3. Manual Testing Requirements — CRITICAL: Agent Must Execute

**IMPORTANT**: The coding agent MUST perform all manual testing steps itself. **NEVER delegate testing to the user**. These tests must be executed by the agent to mark tasks as completed in `tasks.md`.

### Step N+1: Run Unit Tests and Verify Database State (MANDATORY)

**Agent Responsibility**: The coding agent MUST execute unit tests, validate database integrity, and produce a test report in `specs/<change-name>/reports/`.

**Implementation Steps** (Agent must perform):
1. **Prepare Test Environment**:
   - Ensure required services are running (Supabase local, Redis)
   - Capture pre-test database state for impacted tables
   - Document the exact test command to be executed

2. **Run Targeted Unit Tests First**:
   - For backend tasks touching `src/fiscal/`:
     ```bash
     pytest tests/fiscal/test_<module>.py -v --cov=src/fiscal/<module>.py --cov-report=term-missing
     ```
   - Confirm no failures and no regressions

3. **Run Broader Unit Test Suite**:
   - ```bash
     pytest tests/ -v --cov=src/fiscal --cov-report=term-missing
     ```
   - Coverage on `src/fiscal/` must be **100%** — this is non-negotiable per `openspec/config.yaml`
   - Record total passed/failed/skipped and runtime

4. **Verify Post-Test Database State**:
   - Re-check the same Supabase tables captured before tests
   - Confirm no unintended mutations remain
   - If any mutation occurred, restore state and document the restoration

5. **Create Unit Test Verification Report**:
   - Save under `specs/<change-name>/reports/`
   - Filename: `YYYY-MM-DD-step-N-unit-test-and-db-verification.md`
   - Use the report template below

6. **Mark Task as Completed**: Only after tests pass, coverage is 100% on `src/fiscal/`, database state is verified, and the report file exists.

**Report Template**:
```markdown
# Step N+1 Report — Unit Tests and Database Verification

- Date: YYYY-MM-DD
- Change: <change-name>
- Agent: backend-developer

## Commands Executed
- `pytest tests/fiscal/test_<module>.py -v --cov=src/fiscal/<module>.py`
- `pytest tests/ -v --cov=src/fiscal --cov-report=term-missing`

## Unit Test Results
- Targeted tests: X passed, Y failed, Z skipped
- Full suite: X passed, Y failed, Z skipped
- Coverage src/fiscal/: X% (must be 100%)
- Runtime: <duration>
- Notes: <any flaky tests or exceptions>

## Database State Verification
- Pre-test baseline:
  - <table>: <row count or key values>
- Post-test validation:
  - <table>: <row count or key values>
- State restored: Yes/No
- Restoration actions (if any): <actions>

## Outcome
- Step status: PASS/FAIL
- Blocking issues: <none or list>
```

### Step N+2: Manual Endpoint Testing with curl (MANDATORY for backend)

**Agent Responsibility**: The coding agent MUST execute all curl commands and verify responses. **NEVER delegate to the user.**

**Project-specific setup**:
- Backend server: `uvicorn src.api.main:app --reload --port 8000`
- Health check: `curl http://localhost:8000/health`
- All protected endpoints require a Supabase JWT:
  ```bash
  # Get test JWT from .env.test or generate with Supabase CLI
  export TEST_JWT="<supabase_jwt_for_test_user>"
  ```

**Implementation Steps** (Agent must perform):

1. **Start the backend server** (if not already running):
   ```bash
   uvicorn src.api.main:app --reload --port 8000
   ```

2. **Verify server is healthy**:
   ```bash
   curl http://localhost:8000/health
   # Expected: {"status": "ok", "db": "ok", "redis": "ok"}
   ```

3. **Test GET endpoints**:
   ```bash
   curl -X GET http://localhost:8000/api/proceso/p04/estado/<proceso_id> \
     -H "Authorization: Bearer $TEST_JWT"
   ```
   Verify: correct status code, response body matches `docs/api-spec.yml` schema

4. **Test POST endpoints** (CREATE operations):
   ```bash
   curl -X POST http://localhost:8000/api/proceso/p04/iniciar \
     -H "Authorization: Bearer $TEST_JWT" \
     -H "Content-Type: application/json"
   ```
   Verify: status code, response body, created record in Supabase
   **Restore**: delete the created record after testing

5. **Test error cases**:
   - Missing JWT → 401
   - Invalid payload → 422 with structured error `{"error": "CODE", "detail": "...", "proceso": "P04"}`
   - Duplicate declaration → 409 with `PRESENTACION_DUPLICADA` error code

6. **Restore Database State**: After all tests, verify Supabase tables are back to pre-test state.

7. **Create curl Testing Report**:
   - Save under `specs/<change-name>/reports/`
   - Filename: `YYYY-MM-DD-step-N-curl-testing.md`

**Mark Task as Completed**: Only after all curl tests pass, database is restored, and report exists.

### Step N+3: E2E Testing with Playwright (MANDATORY if frontend involved)

**Agent Responsibility**: The coding agent MUST execute all E2E tests using the **Playwright test runner** (`npx playwright test`). This is NOT the Playwright MCP browser tools — it is the standard Playwright test runner for automated testing.

**When This Applies**:
- Any task that creates or modifies a Next.js component or page
- Any task that integrates frontend with a backend endpoint
- Any task involving Supabase Realtime subscriptions

**Implementation Steps** (Agent must perform):

1. **Ensure servers are running**:
   ```bash
   # Terminal 1 — Backend
   uvicorn src.api.main:app --reload --port 8000
   # Terminal 2 — Frontend
   cd frontend && npm run dev
   ```

2. **Run the relevant Playwright spec**:
   ```bash
   # Run a specific spec file
   npx playwright test e2e/<feature>.spec.ts
   # Run all E2E tests
   npx playwright test
   ```

3. **Verify test output**:
   - All tests in the spec file must pass
   - Paste the actual Playwright output in the report
   - If tests fail — fix the component and re-run before reporting

4. **What the E2E test must cover**:
   - The task's slice of the happy path (from the acceptance criteria)
   - The critical negative case introduced by this task (e.g. user clicks cancel, OCR field rejected, RPA error state)
   - For any RPA-dependent screen: all four states must be tested (waiting / needs-re-auth / failed / done)

5. **Restore test environment**:
   - Delete any test data created in Supabase during the E2E run
   - Verify Supabase Storage has no leftover test files

6. **Create E2E Test Report**:
   - Save under `specs/<change-name>/reports/`
   - Filename: `YYYY-MM-DD-step-N-e2e-playwright.md`

**Mark Task as Completed**: Only after all Playwright tests pass and report exists.

**Report Template**:
```markdown
# Step N+3 Report — E2E Playwright Testing

- Date: YYYY-MM-DD
- Change: <change-name>
- Agent: frontend-developer

## Commands Executed
- `npx playwright test e2e/<spec>.spec.ts`

## Test Results
```
<paste actual Playwright output here>
```

## Scenarios Covered
- Happy path: <description>
- Negative case: <description>
- RPA states tested (if applicable): waiting / needs-re-auth / failed / done

## Environment Restoration
- Test data deleted: Yes/No
- Storage files cleaned: Yes/No

## Outcome
- Step status: PASS/FAIL
- Blocking issues: <none or list>
```

## 4. Verification Checklist

Before finalizing any `tasks.md` file, verify:
- [ ] `openspec/config.yaml` has been read
- [ ] Step 0 (Create Feature Branch) is the FIRST step
- [ ] Branch name follows `feature/{change-name}` convention
- [ ] All mandatory steps are included and marked "(MANDATORY)"
- [ ] Backend tasks: Step N+1 (unit tests) and Step N+2 (curl) are present
- [ ] Frontend tasks: Step N+3 (Playwright) is present
- [ ] Report paths follow `specs/<change-name>/reports/YYYY-MM-DD-step-N-<type>.md`
- [ ] Every step explicitly states "AGENT MUST EXECUTE"
- [ ] Database state restoration steps are included for CREATE/UPDATE/DELETE operations
- [ ] All tasks reference their acceptance criteria (CA-Fx-xx)
- [ ] No out-of-scope items from `openspec/config.yaml` are included

## 5. When This Applies

This rule applies when:
- Creating `tasks.md` via `/ff` (fast-forward)
- Updating existing `tasks.md` files
- Implementing tasks via `/apply` — the agent must execute all tests itself

## 6. Example Structure

```markdown
## 0. Setup: Create Feature Branch (MANDATORY — FIRST STEP)

- [ ] 0.1 Create feature branch `feature/fiscal-engine-iva-devengado` from main
- [ ] 0.2 Verify branch creation: `git branch --show-current`

## 1. Backend: TDD — Write Failing Tests First
- [ ] 1.1 Write test_calcular_iva_devengado_tipo_general() — must fail
- [ ] 1.2 Write test_calcular_iva_devengado_isp_proveedor_extranjero() — must fail
- [ ] 1.3 Verify tests fail: `pytest tests/fiscal/test_calcular_devengado.py -v`
- Acceptance criteria: CA-F1-06

## 2. Backend: Implement calcular_iva_devengado()
- [ ] 2.1 Create src/fiscal/iva/calcular_devengado.py
- [ ] 2.2 Implement function with legal reference in docstring (Art. 88-90 LIVA)
- [ ] 2.3 Run tests — all must pass: `pytest tests/fiscal/test_calcular_devengado.py -v`
- Acceptance criteria: CA-F1-06

## 3. Backend: Review and Update Existing Unit Tests (MANDATORY)
- [ ] 3.1 Check for existing tests that may be affected by the new function
- [ ] 3.2 Update any affected tests

## 4. Backend: Run Unit Tests and Verify Database State (MANDATORY — AGENT MUST EXECUTE)
- [ ] 4.1 Capture pre-test Supabase state
- [ ] 4.2 Run targeted tests: `pytest tests/fiscal/ -v --cov=src/fiscal --cov-report=term-missing`
- [ ] 4.3 Verify coverage is 100% on src/fiscal/
- [ ] 4.4 Verify post-test database state
- [ ] 4.5 Create report `specs/fiscal-engine-iva-devengado/reports/YYYY-MM-DD-step-4-unit-test-and-db-verification.md`
- [ ] 4.6 Mark complete only after report exists and coverage is 100%
- Acceptance criteria: CA-F1-10

## 5. Backend: Manual Endpoint Testing with curl (MANDATORY — AGENT MUST EXECUTE)
- [ ] 5.1 Start backend: `uvicorn src.api.main:app --reload --port 8000`
- [ ] 5.2 Verify health: `curl http://localhost:8000/health`
- [ ] 5.3 Test POST /api/proceso/p04/calcular with seed data profile 1
- [ ] 5.4 Test POST /api/proceso/p04/calcular with seed data profile 2 (ISP case)
- [ ] 5.5 Test error case: missing JWT → verify 401
- [ ] 5.6 Restore any test data created
- [ ] 5.7 Create report `specs/fiscal-engine-iva-devengado/reports/YYYY-MM-DD-step-5-curl-testing.md`
- Acceptance criteria: CA-F1-06, CA-F2-02

## 6. Update Technical Documentation (MANDATORY)
- [ ] 6.1 Update CHANGELOG.md with the new function
- [ ] 6.2 Verify docs/data-model.md is still accurate
- [ ] 6.3 Update docs/api-spec.yml if any endpoint contract changed
```

## 7. Agent Execution Requirements

**CRITICAL**: When implementing tasks via `/apply`, the coding agent MUST:

1. **Execute All Tests Itself**: Never ask the user to run tests. The agent:
   - Starts servers if needed
   - Executes pytest with the exact command from `openspec/config.yaml`
   - Executes `npx playwright test` (not Playwright MCP tools) for E2E
   - Verifies all responses and outcomes
   - Restores database state after tests

2. **Mark Tasks as Completed Only After**:
   - All required tests have been executed by the agent
   - Test output is documented in the report file
   - The report file exists in `specs/<change-name>/reports/`
   - Coverage is 100% on `src/fiscal/` for fiscal engine tasks
   - Database state has been verified and restored

3. **Never Delegate Testing**: The agent must never:
   - Ask the user to run pytest
   - Ask the user to execute curl commands
   - Ask the user to run `npx playwright test`
   - Mark tasks as completed without executing tests
   - Skip manual testing steps

4. **Fiscal Integrity**: Before marking any fiscal engine task complete, verify:
   - Legal reference is in the function docstring
   - ISP detection handles all three null/empty/non-ES cases
   - No fiscal arithmetic appears in route handlers
   - Coverage on `src/fiscal/` is exactly 100%
