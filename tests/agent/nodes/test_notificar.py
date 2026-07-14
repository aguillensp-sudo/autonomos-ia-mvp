"""Tests for the notificar node."""
import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.agent.nodes.notificar import notificar

load_dotenv()

EJERCICIO_TEST = 2036
PASSWORD = "notificar-test-123!"
EMAIL = "notificar-node-test@test.autonomos.local"


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


def test_notificar_confirmado_escribe_presentacion_para_que_f4_la_recoja(test_user_id):
    # SPEC-F4-00 (rpa-aeat): confirmado=True now upserts a presentacion row
    # in estado='confirmado' so Phase 4's ARQ worker has something to pick
    # up. See tests/agent/nodes/test_notificar_confirma_escribe_presentacion.py
    # for the full assertion set on the written row's fields.
    estado = {
        "user_id": test_user_id["id"], "user_jwt": test_user_id["jwt"], "ejercicio": EJERCICIO_TEST, "periodo": "1T",
        "confirmado": True, "cancelado": False,
        "resultado_m303": {
            "total_devengado": "100.00", "total_deducible": "0.00",
            "saldo_compensar_anterior": "0.00", "resultado": "100.00",
            "tipo_resultado": "a_ingresar", "casillas": {},
        },
        "mensajes": [],
    }
    notificar(estado)

    admin = _admin_client()
    fila = admin.table("presentacion").select("estado").eq("user_id", test_user_id["id"]).eq("ejercicio", EJERCICIO_TEST).execute()
    assert len(fila.data) == 1
    assert fila.data[0]["estado"] == "confirmado"


def test_notificar_cancelado_actualiza_estado_bd(test_user_id):
    estado = {
        "user_id": test_user_id["id"], "user_jwt": test_user_id["jwt"], "ejercicio": EJERCICIO_TEST, "periodo": "2T",
        "confirmado": False, "cancelado": True,
        "resultado_m303": None,
        "mensajes": [],
    }
    notificar(estado)

    admin = _admin_client()
    fila = admin.table("presentacion").select("estado").eq("user_id", test_user_id["id"]).eq("ejercicio", EJERCICIO_TEST).eq("periodo", "2T").execute()
    assert len(fila.data) == 1
    assert fila.data[0]["estado"] == "cancelado"


def test_notificar_confirmado_agrega_mensaje_final(test_user_id):
    estado = {
        "user_id": test_user_id["id"], "user_jwt": test_user_id["jwt"], "ejercicio": EJERCICIO_TEST, "periodo": "1T",
        "confirmado": True, "cancelado": False,
        "resultado_m303": {
            "total_devengado": "100.00", "total_deducible": "0.00",
            "saldo_compensar_anterior": "0.00", "resultado": "100.00",
            "tipo_resultado": "a_ingresar", "casillas": {},
        },
        "mensajes": [],
    }
    resultado = notificar(estado)
    assert len(resultado["mensajes"]) >= 1
    assert resultado["mensajes"][-1]["rol"] == "agente"
    # Minor fix (post-adversarial-review): this graph never files anything
    # with the AEAT (Phase 4 does) — the message must not imply otherwise.
    contenido = resultado["mensajes"][-1]["contenido"].lower()
    assert "presentando" not in contenido
    assert "presentado" not in contenido


def test_notificar_ni_confirmado_ni_cancelado_solo_pasa_mensajes():
    estado = {
        "user_id": "user-1", "ejercicio": 2026, "periodo": "1T",
        "confirmado": False, "cancelado": False,
        "resultado_m303": None,
        "mensajes": [{"rol": "usuario", "contenido": "hola"}],
    }
    resultado = notificar(estado)
    assert resultado == {"mensajes": [{"rol": "usuario", "contenido": "hola"}]}
