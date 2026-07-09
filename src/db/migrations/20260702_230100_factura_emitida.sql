CREATE TABLE factura_emitida (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  numero_factura      TEXT NOT NULL,
  fecha               DATE NOT NULL,
  nif_cliente         TEXT,
  nombre_cliente      TEXT,
  base_imponible      NUMERIC(12,2) NOT NULL CHECK (base_imponible >= 0),
  tipo_iva            SMALLINT NOT NULL CHECK (tipo_iva IN (0, 4, 10, 21)),
  cuota_iva           NUMERIC(12,2) NOT NULL,
  retencion_irpf      NUMERIC(5,2) DEFAULT 0,
  cuota_retencion     NUMERIC(12,2) DEFAULT 0,
  es_isp              BOOLEAN DEFAULT FALSE,
  es_intracomunitaria BOOLEAN DEFAULT FALSE,
  es_exportacion      BOOLEAN DEFAULT FALSE,
  cobrada             BOOLEAN DEFAULT TRUE,
  fecha_cobro         DATE,
  periodo_declarado   TEXT,
  origen              TEXT DEFAULT 'manual'
                      CHECK (origen IN ('manual', 'ocr', 'import')),
  ocr_confidence      NUMERIC(3,2),
  pdf_path            TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE factura_emitida ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns invoices" ON factura_emitida USING (user_id = auth.uid());

CREATE INDEX idx_factura_emitida_user_fecha ON factura_emitida (user_id, fecha);
CREATE INDEX idx_factura_emitida_periodo ON factura_emitida (user_id, periodo_declarado);
