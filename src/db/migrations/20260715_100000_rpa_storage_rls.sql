-- RLS policies for the 3 Storage buckets Phase 4 (rpa-aeat) writes to:
-- justificantes, qr-clave, screenshots. Adversarial-review HIGH-1: these
-- buckets were created ad hoc without any storage.objects policy, meaning
-- only the service role key could ever read/write them -- the exact same
-- RLS-bypass problem 20260713_140000_facturas_storage_rls.sql closed for
-- the `facturas` bucket.
--
-- Path convention: {bucket_name}/{user_id}/{filename} for all three, e.g.
-- justificantes/{user_id}/{ejercicio}_{periodo}.pdf. storage.foldername(name)
-- returns the path split into folder segments, so (storage.foldername(name))[2]
-- is the user_id segment (index 1 is the redundant bucket-name-shaped prefix
-- src/rpa/aeat/justificante.py and src/workers/rpa_worker.py already write).

CREATE POLICY "user reads own justificante files"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'justificantes'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );

CREATE POLICY "user uploads own justificante files"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'justificantes'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );

CREATE POLICY "user reads own qr-clave files"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'qr-clave'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );

CREATE POLICY "user uploads own qr-clave files"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'qr-clave'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );

CREATE POLICY "user reads own screenshot files"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'screenshots'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );

CREATE POLICY "user uploads own screenshot files"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'screenshots'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );
