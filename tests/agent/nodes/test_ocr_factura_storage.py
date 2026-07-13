"""Integration test for _descargar_bytes against the real local Supabase
Storage 'facturas' bucket — not mocked, unlike tests/agent/nodes/test_ocr_factura.py
(which mocks this function to test only the node's routing logic).

Uses a real user-scoped (anon key + JWT) client, not the service role key —
post-adversarial-review Blocker 2 — so this also exercises the storage.objects
RLS policy (src/db/migrations/20260713_140000_facturas_storage_rls.sql), which
requires the path's second segment to match the authenticated user's id.
"""
import os

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.agent.nodes.ocr_factura import _descargar_bytes

load_dotenv()

_CONTENIDO_PRUEBA = b"%PDF-1.4 contenido minimo de prueba para test de descarga"
PASSWORD = "descargar-bytes-test-123!"
EMAIL = "descargar-bytes-storage-test@test.autonomos.local"


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


@pytest.fixture
def factura_de_prueba_en_storage():
    admin = _admin_client()
    user_id = _get_or_create_user(admin, EMAIL)
    path = f"emitidas/{user_id}/test-descargar-bytes.pdf"
    try:
        admin.storage.from_("facturas").remove([path])
    except Exception:
        pass
    admin.storage.from_("facturas").upload(
        path, _CONTENIDO_PRUEBA, file_options={"content-type": "application/pdf"}
    )
    yield path, _jwt_for(EMAIL)
    try:
        admin.storage.from_("facturas").remove([path])
    except Exception:
        pass


def test_descargar_bytes_recupera_contenido_real_de_storage(factura_de_prueba_en_storage):
    path, jwt = factura_de_prueba_en_storage
    contenido = _descargar_bytes(path, jwt)
    assert contenido == _CONTENIDO_PRUEBA
