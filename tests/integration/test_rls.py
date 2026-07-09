"""RLS integration tests against the real local Supabase instance.
Acceptance criteria: CA-F1-02. Requires `supabase start` running locally.
"""
import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
TEST_PASSWORD = "rls-test-password-123!"


def _admin_client():
    return create_client(SUPABASE_URL, SERVICE_KEY)


def _get_or_create_user(admin, email: str) -> str:
    for user in admin.auth.admin.list_users():
        if user.email == email:
            return user.id
    created = admin.auth.admin.create_user({"email": email, "password": TEST_PASSWORD, "email_confirm": True})
    return created.user.id


def _client_as(email: str) -> "Client":  # noqa: F821
    client = create_client(SUPABASE_URL, ANON_KEY)
    client.auth.sign_in_with_password({"email": email, "password": TEST_PASSWORD})
    return client


@pytest.fixture(scope="module")
def user_a_and_b():
    admin = _admin_client()
    user_a_id = _get_or_create_user(admin, "rls-test-user-a@test.autonomos.local")
    user_b_id = _get_or_create_user(admin, "rls-test-user-b@test.autonomos.local")

    # Seed one factura_emitida and one presentacion owned by user A only.
    # Clean up any leftovers from a previous run first — these tests hit a real,
    # persistent local Supabase instance, not a rolled-back transaction.
    admin.table("factura_emitida").delete().eq("numero_factura", "RLS-TEST-001").execute()
    admin.table("presentacion").delete().eq("user_id", user_a_id).eq("proceso", "P04").eq("ejercicio", 2026).eq("periodo", "1T").execute()

    admin.table("factura_emitida").insert({
        "id": str(uuid4()),
        "user_id": user_a_id,
        "numero_factura": "RLS-TEST-001",
        "fecha": str(date(2026, 1, 15)),
        "base_imponible": "100.00",
        "tipo_iva": 21,
        "cuota_iva": "21.00",
    }).execute()

    admin.table("presentacion").insert({
        "id": str(uuid4()),
        "user_id": user_a_id,
        "proceso": "P04",
        "modelo": "303",
        "ejercicio": 2026,
        "periodo": "1T",
    }).execute()

    return user_a_id, user_b_id


def test_rls_factura_emitida_usuario_b_no_ve_facturas_de_a(user_a_and_b):
    _, _ = user_a_and_b
    client_b = _client_as("rls-test-user-b@test.autonomos.local")
    result = client_b.table("factura_emitida").select("*").eq("numero_factura", "RLS-TEST-001").execute()
    assert result.data == []


def test_rls_presentacion_usuario_b_no_ve_presentaciones_de_a(user_a_and_b):
    _, _ = user_a_and_b
    client_b = _client_as("rls-test-user-b@test.autonomos.local")
    result = client_b.table("presentacion").select("*").eq("proceso", "P04").eq("ejercicio", 2026).execute()
    assert result.data == []


def test_rls_factura_emitida_usuario_a_ve_su_propia_factura(user_a_and_b):
    _, _ = user_a_and_b
    client_a = _client_as("rls-test-user-a@test.autonomos.local")
    result = client_a.table("factura_emitida").select("*").eq("numero_factura", "RLS-TEST-001").execute()
    assert len(result.data) == 1
