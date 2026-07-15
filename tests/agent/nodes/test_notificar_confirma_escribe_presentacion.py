"""SPEC-F4-00: notificar's confirmado=True branch must upsert a presentacion
row so Phase 4's ARQ worker has something to pick up. Acceptance: prerequisite
for CA-F4-01..10 (no CA of its own).
"""
import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.agent.nodes.notificar import notificar

load_dotenv()

EJERCICIO_TEST = 2037
PASSWORD = "notificar-f4-test-123!"
EMAIL = "notificar-f4-test@test.autonomos.local"


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
def test_user_id():
    admin = _admin_client()
    user_id = _get_or_create_user(admin, EMAIL)
    admin.table("presentacion").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()
    yield {"id": user_id, "jwt": _jwt_for(EMAIL)}
    admin.table("presentacion").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()


def test_notificar_confirmado_escribe_presentacion_estado_confirmado(test_user_id):
    estado = {
        "user_id": test_user_id["id"], "user_jwt": test_user_id["jwt"], "ejercicio": EJERCICIO_TEST, "periodo": "1T",
        "confirmado": True, "cancelado": False,
        "resultado_m303": {
            "ejercicio": EJERCICIO_TEST, "periodo": "1T",
            "total_devengado": "210.00", "total_deducible": "50.00",
            "saldo_compensar_anterior": "0.00", "resultado": "160.00",
            "tipo_resultado": "a_ingresar", "casillas": {"27": "210.00", "45": "50.00"},
        },
        "mensajes": [],
    }
    notificar(estado)

    admin = _admin_client()
    fila = admin.table("presentacion").select("*").eq("user_id", test_user_id["id"]).eq("ejercicio", EJERCICIO_TEST).eq("periodo", "1T").execute()
    assert len(fila.data) == 1
    row = fila.data[0]
    assert row["estado"] == "confirmado"
    assert row["proceso"] == "P04"
    assert row["modelo"] == "303"
    assert float(row["total_devengado"]) == 210.00
    assert float(row["total_deducible"]) == 50.00
    assert float(row["saldo_compensar_aplicado"]) == 0.00
    assert row["log_confirmacion"]["resultado"] == "160.00"
    assert row["log_confirmacion"]["casillas"]["27"] == "210.00"


def test_notificar_confirmado_es_idempotente_upsert(test_user_id):
    estado = {
        "user_id": test_user_id["id"], "user_jwt": test_user_id["jwt"], "ejercicio": EJERCICIO_TEST, "periodo": "2T",
        "confirmado": True, "cancelado": False,
        "resultado_m303": {
            "ejercicio": EJERCICIO_TEST, "periodo": "2T",
            "total_devengado": "100.00", "total_deducible": "20.00",
            "saldo_compensar_anterior": "0.00", "resultado": "80.00",
            "tipo_resultado": "a_ingresar", "casillas": {"27": "100.00"},
        },
        "mensajes": [],
    }
    notificar(estado)
    notificar(estado)  # calling twice must not create a duplicate row

    admin = _admin_client()
    fila = admin.table("presentacion").select("*").eq("user_id", test_user_id["id"]).eq("ejercicio", EJERCICIO_TEST).eq("periodo", "2T").execute()
    assert len(fila.data) == 1
