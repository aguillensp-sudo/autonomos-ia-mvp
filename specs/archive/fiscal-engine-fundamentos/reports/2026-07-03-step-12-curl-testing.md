# Step 12 Report - Manual Endpoint Testing with curl

- Date: 2026-07-03
- Change: fiscal-engine-fundamentos
- Server: `uvicorn src.api.main:app --port 8000` against local Supabase (Docker)

## Commands Executed

```
curl -s http://localhost:8000/health

curl -s -X POST http://localhost:8000/api/proceso/p04/facturas \
  -H "Authorization: Bearer $TEST_JWT" -H "Content-Type: application/json" \
  -d '{"tipo":"emitida","numero_factura":"CURL-TEST-001","fecha":"2026-03-01","nif_cliente":"12345678Z","base_imponible":"100.00","tipo_iva":21,"cuota_iva":"21.00"}'

curl -s http://localhost:8000/api/proceso/p04/facturas -H "Authorization: Bearer $TEST_JWT"

curl -s http://localhost:8000/api/proceso/p04/facturas   # no auth header

curl -s -X POST http://localhost:8000/api/proceso/p04/facturas \
  -H "Authorization: Bearer $TEST_JWT" -H "Content-Type: application/json" \
  -d '{"tipo":"emitida","numero_factura":"CURL-TEST-002","fecha":"2026-03-01","base_imponible":"100.00","tipo_iva":25,"cuota_iva":"25.00"}'
```

`$TEST_JWT` obtained via `client.auth.sign_in_with_password(...)` for the seeded test user `perfil1-solo-servicios@test.autonomos.local`.

## Results

| Case | Expected | Actual | Status |
|---|---|---|---|
| `GET /health` | 200, `{"status":"ok","db":"ok","redis":...}` | 200, `{"status":"ok","db":"ok","redis":"not_configured"}` | PASS (redis reported honestly as not configured — Phase 5 scope) |
| `POST /facturas` (emitida, valid) | 201, created row | 201, row returned with `user_id` correctly stamped from JWT | PASS |
| `GET /facturas` | 200, list including created invoice | 200, list of 11 emitidas + 1 recibida including `CURL-TEST-001` | PASS |
| `GET /facturas` (no `Authorization` header) | 401 | 401, `{"error":"UNAUTHORIZED",...}` | PASS (fixed — see Issues Found) |
| `POST /facturas` (`tipo_iva: 25`) | 422, structured error | 422, `{"error":"VALIDATION_ERROR",...}` | PASS |

## Issues Found and Fixed During This Step

1. **`db: "error"` on `/health`**: the `anon` Postgres role had no `GRANT SELECT` on any table (only `service_role`/`authenticated` were granted in the initial migration), so the unauthenticated health check failed with a permission error rather than an empty RLS-filtered result. Fixed with migration `20260702230700_grant_anon_health.sql` (`GRANT SELECT ON perfil_fiscal TO anon` — RLS still returns zero rows for `anon`, so no data is exposed).
2. **RLS violation on insert**: `POST /facturas` didn't stamp `user_id` on the row before inserting, so the RLS `WITH CHECK` (implicit from `USING (user_id = auth.uid())`) rejected every insert. Fixed by decoding the JWT's `sub` claim in `src/api/dependencies.py` (`get_authed_request` now returns both the authed client and `user_id`) and setting it explicitly on every insert in `src/api/routers/p04.py`.
3. **Missing-auth case returned 422 instead of 401**: `Header(...)` made the header FastAPI-required, so FastAPI's own validation short-circuited with a generic 422 before the endpoint's 401 logic ran. Fixed by declaring `authorization: str | None = Header(default=None)` and handling the missing case explicitly.

## Database State Restoration

- `CURL-TEST-001` deleted after verification. `CURL-TEST-002` was never persisted (rejected at validation, 422).
- Post-test `factura_emitida` count returned to the seed baseline (16 → 15 after cleanup, matching Step 11's report before this step's test insert).

## Outcome

- Step 12 status: **PASS**
- Blocking issues: none (all 3 issues found were fixed within this step)
