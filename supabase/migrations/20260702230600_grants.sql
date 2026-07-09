GRANT SELECT, INSERT, UPDATE, DELETE ON
  public.perfil_fiscal,
  public.factura_emitida,
  public.factura_recibida,
  public.presentacion,
  public.saldo_iva_compensar,
  public.alerta
TO service_role, authenticated;

GRANT USAGE ON SCHEMA public TO service_role, authenticated;
