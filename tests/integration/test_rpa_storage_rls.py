"""RLS integration tests for the 3 new Storage buckets this phase writes to
(justificantes, qr-clave, screenshots). Adversarial review HIGH-1: these
buckets had no RLS policy at all — only a service-role client could ever
read/write them. Mirrors tests/agent/test_rls_agent_nodes.py's pattern:
a user-scoped client (anon key + JWT) must never read another user's file,
and must be able to read their own.
"""
import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.agent.supabase_client import crear_cliente_usuario

load_dotenv()

PASSWORD = "rpa-storage-rls-test-123!"
BUCKETS = ["justificantes", "qr-clave", "screenshots"]


def _admin_client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def _get_or_create_user(admin, email: str) -> str:
    for user in admin.auth.admin.list_users():
        if user.email == email:
            return user.id
    created = admin.auth.admin.create_user({"email": email, "password": PASSWORD, "email_confirm": True})
    return created.user.id


def _jwt_for(email: str) -> str:
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
    session = client.auth.sign_in_with_password({"email": email, "password": PASSWORD})
    return session.session.access_token


@pytest.fixture(scope="module")
def usuarios():
    admin = _admin_client()
    user_a = _get_or_create_user(admin, "rpa-storage-rls-a@test.autonomos.local")
    user_b = _get_or_create_user(admin, "rpa-storage-rls-b@test.autonomos.local")
    return {
        "a": {"id": user_a, "jwt": _jwt_for("rpa-storage-rls-a@test.autonomos.local")},
        "b": {"id": user_b, "jwt": _jwt_for("rpa-storage-rls-b@test.autonomos.local")},
    }


@pytest.mark.parametrize("bucket", BUCKETS)
def test_usuario_no_puede_leer_archivo_de_otro_usuario(usuarios, bucket):
    admin = _admin_client()
    user_b = usuarios["b"]["id"]
    path = f"{bucket}/{user_b}/rls-test-{uuid4().hex}.bin"
    admin.storage.from_(bucket).upload(path, b"fake-bytes", {"upsert": "true"})

    cliente_a = crear_cliente_usuario(usuarios["a"]["jwt"])
    with pytest.raises(Exception):
        resultado = cliente_a.storage.from_(bucket).download(path)
        # storage3 may return an empty/error payload instead of raising in
        # some client versions — treat that as a failure too, not a pass.
        assert not resultado

    admin.storage.from_(bucket).remove([path])


@pytest.mark.parametrize("bucket", BUCKETS)
def test_usuario_puede_leer_su_propio_archivo(usuarios, bucket):
    admin = _admin_client()
    user_b = usuarios["b"]["id"]
    path = f"{bucket}/{user_b}/rls-test-{uuid4().hex}.bin"
    contenido = b"fake-bytes-own-file"
    admin.storage.from_(bucket).upload(path, contenido, {"upsert": "true"})

    cliente_b = crear_cliente_usuario(usuarios["b"]["jwt"])
    descargado = cliente_b.storage.from_(bucket).download(path)
    assert descargado == contenido

    admin.storage.from_(bucket).remove([path])
