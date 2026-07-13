"""Shared Supabase client builder for src/agent/ nodes. Post-adversarial-review
Blocker 2: every node that touches Supabase (Postgres tables or Storage) must
authenticate as the user themselves — anon key + the user's own JWT — never
the service role key. The service role bypasses RLS entirely, so relying on
it plus an application-level `.eq("user_id", ...)` filter leaves no
database-level backstop if that filter value is ever wrong (a state-merge
bug, a future API layer mis-binding a session). RLS, not the filter clause,
must be the actual enforcement mechanism.
"""
import os

from storage3 import SyncStorageClient
from supabase import Client, create_client


def crear_cliente_usuario(jwt: str) -> Client:
    """Builds a Supabase client scoped to the given user JWT. Both the
    PostgREST client (table queries) and the Storage client need their
    Authorization header set explicitly — constructing the client with the
    anon key alone is not enough for either to be treated as that user.

    Storage needs special handling: supabase-py's `Client.storage` property
    builds its `SyncStorageClient` from a headers dict snapshotted at first
    access (`storage3`'s bucket/file API keeps that snapshot in `_headers`,
    not `session.headers`), so mutating `client.storage.session.headers`
    after the fact silently has no effect on real requests. The client's
    cached `_storage` must be replaced with a freshly built one that already
    has the JWT baked into its headers.
    """
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
    client.postgrest.auth(jwt)
    client._storage = SyncStorageClient(
        url=str(client.storage_url),
        headers={**client.options.headers, "Authorization": f"Bearer {jwt}"},
    )
    return client
