CREATE TABLE perfil_fiscal (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  nif             TEXT NOT NULL,
  nombre          TEXT NOT NULL,
  epigrafe_iae    TEXT NOT NULL,
  cnae            TEXT,
  regimen_iva     TEXT NOT NULL
                  CHECK (regimen_iva IN ('general', 'simplificado', 'recargo_equivalencia', 'criterio_caja')),
  regimen_irpf    TEXT NOT NULL
                  CHECK (regimen_irpf IN ('ed_normal', 'ed_simplificada', 'modulos')),
  domicilio_fiscal JSONB NOT NULL,
  iban            TEXT,
  fecha_inicio    DATE NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id)
);

ALTER TABLE perfil_fiscal ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns profile" ON perfil_fiscal
  USING (user_id = auth.uid());
