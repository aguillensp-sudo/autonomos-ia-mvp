CREATE TABLE factura_recibida (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  numero_factura        TEXT,
  fecha                 DATE NOT NULL,
  nif_proveedor         TEXT,
  nombre_proveedor      TEXT,
  descripcion           TEXT,
  categoria_gasto       TEXT NOT NULL,
  base_imponible        NUMERIC(12,2) NOT NULL CHECK (base_imponible >= 0),
  tipo_iva              SMALLINT CHECK (tipo_iva IN (0, 4, 10, 21)),
  cuota_iva             NUMERIC(12,2),
  porcentaje_deducible  NUMERIC(5,2) NOT NULL,
  cuota_deducible       NUMERIC(12,2),
  es_bien_inversion     BOOLEAN DEFAULT FALSE,
  es_isp                BOOLEAN DEFAULT FALSE,
  es_intracomunitaria   BOOLEAN DEFAULT FALSE,
  requiere_confirmacion BOOLEAN DEFAULT FALSE,
  pagada                BOOLEAN DEFAULT TRUE,
  fecha_pago            DATE,
  periodo_declarado     TEXT,
  origen                TEXT DEFAULT 'manual'
                        CHECK (origen IN ('manual', 'ocr', 'import')),
  ocr_confidence        NUMERIC(3,2),
  pdf_path              TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE factura_recibida ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns received invoices" ON factura_recibida USING (user_id = auth.uid());

CREATE INDEX idx_factura_recibida_user_fecha ON factura_recibida (user_id, fecha);
CREATE INDEX idx_factura_recibida_categoria ON factura_recibida (user_id, categoria_gasto);
