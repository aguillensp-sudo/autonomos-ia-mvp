-- RLS policies for the `facturas` Storage bucket (post-adversarial-review,
-- Blocker 2). The bucket was created ad hoc without any storage.objects
-- policy, meaning only the service role key could ever read/write it —
-- exactly the RLS-bypass problem this migration closes for src/agent/'s
-- switch to a user-scoped (anon key + JWT) Supabase client.
--
-- Path convention (from this migration onwards): {emitidas|recibidas}/{user_id}/{filename}.
-- storage.foldername(name) returns the path split into folder segments, so
-- (storage.foldername(name))[2] is the user_id segment.

CREATE POLICY "user reads own factura files"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'facturas'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );

CREATE POLICY "user uploads own factura files"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'facturas'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );
