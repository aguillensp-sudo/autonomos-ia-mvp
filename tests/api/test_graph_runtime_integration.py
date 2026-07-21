"""SPEC-F5-01 real end-to-end test: iniciar_graph -> enviar_mensaje ->
confirmar_graph against the REAL compiled graph, real Postgres checkpointer,
and real Claude Sonnet 5 — mirrors tests/agent/test_flujo_completo.py's
pattern. Requires ANTHROPIC_API_KEY. Never run in the default TDD cycle.
"""
import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.api.graph_runtime import confirmar_graph, enviar_mensaje, iniciar_graph

load_dotenv()

PASSWORD = "graph-runtime-integration-123!"
EMAIL = "graph-runtime-integration@test.autonomos.local"


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
def usuario_con_perfil():
    admin = _admin_client()
    user_id = _get_or_create_user(admin, EMAIL)
    admin.table("perfil_fiscal").delete().eq("user_id", user_id).execute()
    admin.table("perfil_fiscal").insert({
        "id": str(uuid4()), "user_id": user_id, "nif": "12345678Z", "nombre": "Test Autónomo",
        "epigrafe_iae": "7622", "regimen_iva": "general", "regimen_irpf": "ed_normal",
        "domicilio_fiscal": {"calle": "Test", "numero": "1", "cp": "28001", "municipio": "Madrid", "provincia": "Madrid"},
        "fecha_inicio": "2020-01-01",
    }).execute()
    yield {"id": user_id, "jwt": _jwt_for(EMAIL)}
    admin.table("perfil_fiscal").delete().eq("user_id", user_id).execute()
    admin.table("presentacion").delete().eq("user_id", user_id).execute()
    admin.table("saldo_iva_compensar").delete().eq("user_id", user_id).execute()


@pytest.mark.integration
def test_iniciar_enviar_confirmar_flujo_real_completo(usuario_con_perfil):
    user_id = usuario_con_perfil["id"]
    user_jwt = usuario_con_perfil["jwt"]

    inicio = iniciar_graph(user_id=user_id, user_jwt=user_jwt)
    assert inicio["proceso_id"]
    assert inicio["ejercicio"] > 2000
    assert inicio["periodo"] in ("1T", "2T", "3T", "4T")

    respuesta = enviar_mensaje(
        thread_id=inicio["proceso_id"],
        payload={
            "tipo": "texto",
            "contenido": (
                "No he tenido ninguna factura este trimestre, ni emitida ni recibida. "
                "No he tenido actividad."
            ),
        },
    )
    assert respuesta["pendiente"] == "confirmacion"

    confirmado = confirmar_graph(thread_id=inicio["proceso_id"], metodo_pago=None, iban=None)
    assert confirmado["confirmado"] is True
