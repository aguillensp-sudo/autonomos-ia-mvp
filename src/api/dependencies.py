"""Auth and DB session injection. Per docs/backend-standards.md: never use the
service role key in application code — only the anon key with the user's JWT,
so Row Level Security is enforced on every query."""
import base64
import json
import os
from dataclasses import dataclass

from fastapi import Header, HTTPException
from supabase import Client, create_client


@dataclass
class AuthedRequest:
    client: Client
    user_id: str
    jwt: str  # raw JWT — needed by graph_runtime.py to build EstadoP04.user_jwt
              # (Phase 5, SPEC-F5-01) since agent nodes construct their own
              # RLS-scoped client from this string, not from `client` above.


def _decode_jwt_sub(jwt: str) -> str:
    """Extracts the `sub` (user id) claim from the JWT payload.

    Signature verification already happened at the Postgres/PostgREST layer
    when the query executes with this JWT (RLS enforces it) — this decode is
    only to read the claim so we can stamp `user_id` on inserts ourselves.
    """
    try:
        payload_b64 = jwt.split(".")[1]
        padding = "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
        return payload["sub"]
    except (IndexError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "detail": "Malformed JWT", "proceso": "P04"},
        ) from exc


def get_authed_request(authorization: str | None = Header(default=None)) -> AuthedRequest:
    """Builds a request-scoped Supabase client authenticated as the calling user,
    plus the user's id (from the JWT `sub` claim) for stamping owned rows.

    Raises 401 if the Authorization header is missing or malformed.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "detail": "Missing or malformed Authorization header", "proceso": "P04"},
        )

    jwt = authorization.removeprefix("Bearer ").strip()
    url = os.environ["SUPABASE_URL"]
    anon_key = os.environ["SUPABASE_ANON_KEY"]

    client = create_client(url, anon_key)
    client.postgrest.auth(jwt)
    user_id = _decode_jwt_sub(jwt)
    return AuthedRequest(client=client, user_id=user_id, jwt=jwt)
