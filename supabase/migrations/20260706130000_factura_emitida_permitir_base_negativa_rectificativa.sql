-- Facturas rectificativas (casuística C04) legitimately carry a negative
-- base_imponible (abono). The original CHECK (base_imponible >= 0) from
-- Phase 1 would reject them. Relax it to allow negative values only when
-- es_rectificativa=true, matching src/fiscal/models.py's
-- _base_imponible_no_negativa_salvo_rectificativa validator.
ALTER TABLE factura_emitida DROP CONSTRAINT IF EXISTS factura_emitida_base_imponible_check;
ALTER TABLE factura_emitida ADD CONSTRAINT factura_emitida_base_imponible_check
  CHECK (es_rectificativa OR base_imponible >= 0);
