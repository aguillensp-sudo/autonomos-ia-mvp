CREATE TABLE alerta (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  tipo            TEXT NOT NULL,
  proceso         TEXT,
  ejercicio       SMALLINT,
  periodo         TEXT,
  fecha_alerta    DATE NOT NULL,
  fecha_limite    DATE,
  mensaje         TEXT NOT NULL,
  enviada         BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE alerta ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns alerts" ON alerta USING (user_id = auth.uid());

CREATE INDEX idx_alerta_fecha ON alerta (user_id, fecha_alerta, enviada);
