"""RLS integration tests for the 4 Supabase-touching agent nodes
(verificar_duplicado, calcular, ocr_factura, notificar). Acceptance:
post-adversarial-review Blocker 2 — these nodes must query Supabase with a
client scoped to the authenticated user's own JWT, never the service role
key, so RLS is the actual enforcement mechanism (not just an application-
level `.eq("user_id", ...)` filter with no database-level backstop).

Each test simulates the exact failure mode the review flagged: EstadoP04
claims a `user_id` (an application-level value that could be wrong due to a
state-merge bug or a future API mis-binding a session), but the node is only
ever authenticated as the JWT it's actually given. RLS must block any
cross-user access regardless of what `estado["user_id"]` says.
"""
import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.agent.nodes.calcular import calcular
from src.agent.nodes.notificar import notificar
from src.agent.nodes.ocr_factura import ocr_factura
from src.agent.nodes.verificar_duplicado import verificar_duplicado

load_dotenv()

EJERCICIO_TEST = 2036
PASSWORD = "rls-agent-nodes-test-123!"


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
    user_a = _get_or_create_user(admin, "rls-agent-nodes-a@test.autonomos.local")
    user_b = _get_or_create_user(admin, "rls-agent-nodes-b@test.autonomos.local")
    return {
        "a": {"id": user_a, "jwt": _jwt_for("rls-agent-nodes-a@test.autonomos.local")},
        "b": {"id": user_b, "jwt": _jwt_for("rls-agent-nodes-b@test.autonomos.local")},
    }


def test_verificar_duplicado_no_ve_presentacion_de_otro_usuario_aunque_estado_lo_pida(usuarios):
    admin = _admin_client()
    user_b = usuarios["b"]["id"]
    admin.table("presentacion").delete().eq("user_id", user_b).eq("ejercicio", EJERCICIO_TEST).execute()
    admin.table("presentacion").insert({
        "id": str(uuid4()), "user_id": user_b, "proceso": "P04", "modelo": "303",
        "ejercicio": EJERCICIO_TEST, "periodo": "1T", "estado": "presentado", "csv_aeat": "SHOULD-NOT-LEAK",
    }).execute()

    # estado claims user_id=user_b, but the node is authenticated as user A —
    # RLS must block this regardless of what the state dict says.
    resultado = verificar_duplicado({
        "user_id": user_b, "ejercicio": EJERCICIO_TEST, "periodo": "1T", "user_jwt": usuarios["a"]["jwt"],
    })

    assert resultado["presentacion_duplicada"] is False
    admin.table("presentacion").delete().eq("user_id", user_b).eq("ejercicio", EJERCICIO_TEST).execute()


def test_calcular_no_ve_perfil_fiscal_de_otro_usuario_aunque_estado_lo_pida(usuarios):
    admin = _admin_client()
    user_b = usuarios["b"]["id"]
    admin.table("perfil_fiscal").delete().eq("user_id", user_b).execute()
    admin.table("perfil_fiscal").insert({
        "id": str(uuid4()), "user_id": user_b, "nif": "12345678Z", "nombre": "User B",
        "epigrafe_iae": "7622", "regimen_iva": "general", "regimen_irpf": "ed_normal",
        "domicilio_fiscal": {"calle": "X", "numero": "1", "cp": "28001", "municipio": "Madrid", "provincia": "Madrid"},
        "fecha_inicio": "2020-01-01",
    }).execute()

    with pytest.raises(ValueError, match="No perfil_fiscal"):
        calcular({
            "user_id": user_b, "user_jwt": usuarios["a"]["jwt"],
            "ejercicio": EJERCICIO_TEST, "periodo": "1T",
            "fecha_inicio_periodo": "2026-01-01", "fecha_fin_periodo": "2026-03-31",
            "facturas_emitidas": [], "facturas_recibidas": [],
        })

    admin.table("perfil_fiscal").delete().eq("user_id", user_b).execute()


def test_ocr_factura_no_descarga_archivo_de_otro_usuario(usuarios):
    admin = _admin_client()
    user_b = usuarios["b"]["id"]
    path = f"emitidas/{user_b}/rls-test.png"
    admin.storage.from_("facturas").upload(path, b"fake-bytes", {"upsert": "true"})

    with pytest.raises(Exception):
        ocr_factura({
            "user_id": user_b, "user_jwt": usuarios["a"]["jwt"],
            "facturas_pendientes_ocr": [path],
            "facturas_emitidas": [], "facturas_recibidas": [], "facturas_baja_confianza": [],
        })


def test_notificar_no_puede_cancelar_presentacion_de_otro_usuario(usuarios):
    admin = _admin_client()
    user_b = usuarios["b"]["id"]
    admin.table("presentacion").delete().eq("user_id", user_b).eq("ejercicio", EJERCICIO_TEST).eq("periodo", "2T").execute()

    with pytest.raises(Exception):
        notificar({
            "user_id": user_b, "user_jwt": usuarios["a"]["jwt"],
            "ejercicio": EJERCICIO_TEST, "periodo": "2T",
            "cancelado": True, "mensajes": [],
        })

    # No row should have been written under user B's id via user A's session.
    result = admin.table("presentacion").select("*").eq("user_id", user_b).eq("ejercicio", EJERCICIO_TEST).eq("periodo", "2T").execute()
    assert result.data == []
