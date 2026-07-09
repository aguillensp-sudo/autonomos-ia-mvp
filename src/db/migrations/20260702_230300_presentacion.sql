CREATE TABLE presentacion (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  proceso               TEXT NOT NULL,
  modelo                TEXT NOT NULL,
  ejercicio             SMALLINT NOT NULL,
  periodo               TEXT NOT NULL,
  estado                TEXT NOT NULL DEFAULT 'pendiente'
                        CHECK (estado IN ('pendiente', 'calculado', 'confirmado', 'presentando', 'presentado', 'error', 'cancelado')),
  resultado             NUMERIC(12,2),
  tipo_resultado        TEXT
                        CHECK (tipo_resultado IN ('a_ingresar', 'a_compensar', 'a_devolver', 'sin_actividad', 'negativa')),
  csv_aeat              TEXT,
  nrc                   TEXT,
  justificante_path     TEXT,
  log_confirmacion      JSONB,
  rpa_job_id            TEXT,
  error_code            TEXT,
  error_detail          TEXT,
  screenshot_path       TEXT,
  total_devengado       NUMERIC(12,2),
  total_deducible       NUMERIC(12,2),
  saldo_compensar_aplicado NUMERIC(12,2) DEFAULT 0,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, proceso, ejercicio, periodo)
);

ALTER TABLE presentacion ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns declarations" ON presentacion USING (user_id = auth.uid());

CREATE INDEX idx_presentacion_user_proceso ON presentacion (user_id, proceso, ejercicio, periodo);
