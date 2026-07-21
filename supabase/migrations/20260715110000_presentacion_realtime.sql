-- SPEC-F5-04: enable Supabase Realtime on presentacion so the frontend's
-- RpaStatus component reacts to estado transitions (confirmado -> presentando
-- -> presentado|error) without polling. RLS applies to Realtime subscriptions
-- the same as to queries, so cross-user leakage is structurally impossible,
-- not just filtered client-side.

ALTER PUBLICATION supabase_realtime ADD TABLE presentacion;
