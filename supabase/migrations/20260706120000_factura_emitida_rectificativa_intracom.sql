ALTER TABLE factura_emitida
  ADD COLUMN es_rectificativa BOOLEAN DEFAULT FALSE,
  ADD COLUMN factura_original_id UUID REFERENCES factura_emitida(id),
  ADD COLUMN cliente_es_empresario_ue BOOLEAN DEFAULT FALSE;
