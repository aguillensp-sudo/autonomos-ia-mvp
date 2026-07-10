# Step 12 Report - Manual Endpoint Testing with curl

- Date: 2026-07-06
- Change: calculo-iva-completo
- Server: `uvicorn src.api.main:app --port 8000` against local Supabase (Docker)

## Scope note

This change adds **no new API endpoint**. The new fiscal functions (ISP, bloque
informativo, rectificativas, criterio de caja, `saldo_iva_compensar` persistence,
`calcular_m303()` orchestrator) are consumed only by `calcular_m303()` itself, not
yet wired to a route — that wiring is Phase 5 scope per the original roadmap. This
step therefore verifies **regression only**: that Phase 1's endpoints still work
correctly now that `factura_emitida` has 3 new nullable/default columns.

## Commands Executed

```
curl -s http://localhost:8000/health

curl -s -X GET http://localhost:8000/api/proceso/p04/facturas -H "Authorization: Bearer $TEST_JWT"

curl -s -X POST http://localhost:8000/api/proceso/p04/facturas \
  -H "Authorization: Bearer $TEST_JWT" -H "Content-Type: application/json" \
  -d '{"tipo":"emitida","numero_factura":"F2-CURL-TEST-001",...}'

curl -s http://localhost:8000/api/proceso/p04/facturas   # no auth header

curl -s -X POST .../facturas -d '{"tipo":"emitida",...,"tipo_iva":25,...}'  # invalid tipo_iva
```

`$TEST_JWT` obtained via `client.auth.sign_in_with_password(...)` for
`perfil1-solo-servicios@test.autonomos.local` (the same Phase 1 seeded test user).

## Results

| Case | Expected | Actual | Status |
|---|---|---|---|
| `GET /health` | 200, `db: ok` | 200, `{"status":"ok","db":"ok","redis":"not_configured"}` | PASS |
| `GET /facturas` | 200, list includes the 3 new columns with defaults | 200 — every `factura_emitida` row now includes `"es_rectificativa":false,"factura_original_id":null,"cliente_es_empresario_ue":false` | PASS — no regression |
| `POST /facturas` (emitida, valid) | 201, created row | 201, response includes the 3 new columns with correct defaults | PASS |
| `GET /facturas` (no `Authorization`) | 401 | 401, `{"error":"UNAUTHORIZED",...}` | PASS |
| `POST /facturas` (`tipo_iva: 25`) | 422, structured error | 422, `{"error":"VALIDATION_ERROR",...}` | PASS |

## Database State Restoration

- `F2-CURL-TEST-001` deleted after verification. `F2-CURL-TEST-002` was never
  persisted (rejected at validation, 422).
- Post-test `factura_emitida` count returned to the pre-test baseline (16).

## Outcome

- Step 12 status: **PASS**
- Blocking issues: none. No new endpoint added or expected this phase.
