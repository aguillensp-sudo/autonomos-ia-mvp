CREATE TABLE saldo_iva_compensar (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ejercicio   SMALLINT NOT NULL,
  saldo       NUMERIC(12,2) NOT NULL DEFAULT 0,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, ejercicio)
);

ALTER TABLE saldo_iva_compensar ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns IVA balance" ON saldo_iva_compensar USING (user_id = auth.uid());
