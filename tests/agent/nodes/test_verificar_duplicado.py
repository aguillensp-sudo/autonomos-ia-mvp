"""Integration tests for verificar_duplicado against local Supabase.
Acceptance criteria: CA-F3-09.
"""
import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.agent.nodes.verificar_duplicado import verificar_duplicado

load_dotenv()

EJERCICIO_TEST = 2033  # isolated ejercicio
PASSWORD = "verificar-dup-test-123!"
EMAIL = "verificar-duplicado-test@test.autonomos.local"


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
def test_user():
    admin = _admin_client()
    user_id = _get_or_create_user(admin, EMAIL)
    admin.table("presentacion").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()
    yield {"id": user_id, "jwt": _jwt_for(EMAIL)}
    admin.table("presentacion").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()


def test_verificar_duplicado_encuentra_presentacion_existente(test_user):
    admin = _admin_client()
    admin.table("presentacion").insert({
        "id": str(uuid4()),
        "user_id": test_user["id"],
        "proceso": "P04",
        "modelo": "303",
        "ejercicio": EJERCICIO_TEST,
        "periodo": "1T",
        "estado": "presentado",
        "csv_aeat": "ABCD1234EFGH5678",
    }).execute()

    resultado = verificar_duplicado({
        "user_id": test_user["id"],
        "user_jwt": test_user["jwt"],
        "ejercicio": EJERCICIO_TEST,
        "periodo": "1T",
    })

    assert resultado["presentacion_duplicada"] is True
    assert resultado["csv_presentacion_previa"] == "ABCD1234EFGH5678"


def test_verificar_duplicado_sin_presentacion_previa(test_user):
    resultado = verificar_duplicado({
        "user_id": test_user["id"],
        "user_jwt": test_user["jwt"],
        "ejercicio": EJERCICIO_TEST,
        "periodo": "2T",
    })

    assert resultado["presentacion_duplicada"] is False
    assert resultado["csv_presentacion_previa"] is None


def test_verificar_duplicado_periodo_distinto_no_es_duplicado(test_user):
    admin = _admin_client()
    admin.table("presentacion").insert({
        "id": str(uuid4()),
        "user_id": test_user["id"],
        "proceso": "P04",
        "modelo": "303",
        "ejercicio": EJERCICIO_TEST,
        "periodo": "1T",
        "estado": "presentado",
    }).execute()

    resultado = verificar_duplicado({
        "user_id": test_user["id"],
        "user_jwt": test_user["jwt"],
        "ejercicio": EJERCICIO_TEST,
        "periodo": "3T",
    })

    assert resultado["presentacion_duplicada"] is False
