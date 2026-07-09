-- anon needs SELECT on at least one table for the /health check to verify DB
-- connectivity without a user JWT. RLS still returns zero rows for anon, so
-- this does not expose any data.
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT ON public.perfil_fiscal TO anon;
