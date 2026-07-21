"""Tests for the calcular node. Proves it delegates to calcular_m303() and
implements no fiscal arithmetic of its own. Acceptance criteria: feeds
CA-F3-05; casuistica C01 path.
"""
import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.agent.nodes.calcular import calcular
from src.fiscal.iva.calcular_m303 import calcular_m303
from src.fiscal.models import FacturaEmitida, PerfilFiscal

load_dotenv()

EJERCICIO_TEST = 2034


PASSWORD = "calcular-node-test-123!"
EMAIL = "calcular-node-test@test.autonomos.local"


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
def test_user_con_perfil():
    admin = _admin_client()
    user_id = _get_or_create_user(admin, EMAIL)
    admin.table("perfil_fiscal").delete().eq("user_id", user_id).execute()
    admin.table("perfil_fiscal").insert({
        "id": str(uuid4()),
        "user_id": user_id,
        "nif": "12345678Z",
        "nombre": "Test Autónomo",
        "epigrafe_iae": "7622",
        "regimen_iva": "general",
        "regimen_irpf": "ed_normal",
        "domicilio_fiscal": {"calle": "Test", "numero": "1", "cp": "28001", "municipio": "Madrid", "provincia": "Madrid"},
        "fecha_inicio": "2020-01-01",
    }).execute()
    admin.table("saldo_iva_compensar").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()
    yield {"id": user_id, "jwt": _jwt_for(EMAIL)}
    admin.table("perfil_fiscal").delete().eq("user_id", user_id).execute()
    admin.table("saldo_iva_compensar").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()


def _factura_emitida_dict(user_id: str) -> dict:
    f = FacturaEmitida(
        id=uuid4(), user_id=user_id, numero_factura="F-1", fecha=date(2026, 1, 15),
        base_imponible=Decimal("100.00"), tipo_iva=21, cuota_iva=Decimal("21.00"),
    )
    return f.model_dump(mode="json")


def test_calcular_node_delega_a_calcular_m303(test_user_con_perfil):
    user_id = test_user_con_perfil["id"]
    estado = {
        "user_id": user_id,
        "user_jwt": test_user_con_perfil["jwt"],
        "ejercicio": EJERCICIO_TEST,
        "periodo": "1T",
        "fecha_inicio_periodo": "2026-01-01",
        "fecha_fin_periodo": "2026-03-31",
        "facturas_emitidas": [_factura_emitida_dict(user_id)],
        "facturas_recibidas": [],
    }

    resultado_nodo = calcular(estado)

    # Reset saldo (calcular_m303 writes it) and compute independently to compare
    client = _admin_client()
    client.table("saldo_iva_compensar").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()
    perfil = PerfilFiscal(
        id=uuid4(), user_id=user_id, nif="12345678Z", nombre="Test Autónomo", epigrafe_iae="7622",
        regimen_iva="general", regimen_irpf="ed_normal",
        domicilio_fiscal={"calle": "Test", "numero": "1", "cp": "28001", "municipio": "Madrid", "provincia": "Madrid"},
        fecha_inicio=date(2020, 1, 1),
    )
    resultado_directo, _ = calcular_m303(
        client=client, user_id=user_id, ejercicio=EJERCICIO_TEST, periodo="1T",
        perfil_fiscal=perfil,
        facturas_emitidas=[FacturaEmitida(**_factura_emitida_dict(user_id))],
        facturas_recibidas=[],
        fecha_inicio_periodo=date(2026, 1, 1), fecha_fin_periodo=date(2026, 3, 31),
    )

    assert resultado_nodo["resultado_m303"]["resultado"] == str(resultado_directo.resultado)
    assert resultado_nodo["resultado_m303"]["tipo_resultado"] == resultado_directo.tipo_resultado


def test_calcular_node_sin_actividad_facturas_vacias(test_user_con_perfil):
    user_id = test_user_con_perfil["id"]
    estado = {
        "user_id": user_id,
        "user_jwt": test_user_con_perfil["jwt"],
        "ejercicio": EJERCICIO_TEST,
        "periodo": "2T",
        "fecha_inicio_periodo": "2026-04-01",
        "fecha_fin_periodo": "2026-06-30",
        "facturas_emitidas": [],
        "facturas_recibidas": [],
    }

    resultado = calcular(estado)

    assert resultado["resultado_m303"]["tipo_resultado"] == "sin_actividad"
    assert resultado["errores_coherencia"] == []


def test_calcular_node_acepta_payload_con_forma_facturareviewer(test_user_con_perfil):
    """CRITICAL fix (SPEC-F5-07): proves the exact crash site from adversarial
    review Finding 1 is closed — a dict shaped exactly like FacturaReviewer.tsx's
    post-fix onConfirm() output (all required fields present, cuota_iva
    pre-computed, categoria_gasto/porcentaje_deducible present for recibida)
    must construct FacturaEmitida/FacturaRecibida and calcular() without a
    ValidationError."""
    user_id = test_user_con_perfil["id"]
    factura_emitida_reviewer_shape = {
        "id": str(uuid4()), "user_id": user_id, "numero_factura": f"OCR-{uuid4().hex[:8]}",
        "fecha": "2026-01-15", "nif_cliente": "12345678Z",
        "base_imponible": "100.00", "tipo_iva": 21, "cuota_iva": "21.00",
    }
    factura_recibida_reviewer_shape = {
        "id": str(uuid4()), "user_id": user_id, "fecha": "2026-01-16",
        "nif_proveedor": "B87654321", "categoria_gasto": "software_saas",
        "base_imponible": "50.00", "tipo_iva": 21, "cuota_iva": "10.50",
        "porcentaje_deducible": "100",
    }
    estado = {
        "user_id": user_id,
        "user_jwt": test_user_con_perfil["jwt"],
        "ejercicio": EJERCICIO_TEST,
        "periodo": "3T",
        "fecha_inicio_periodo": "2026-07-01",
        "fecha_fin_periodo": "2026-09-30",
        "facturas_emitidas": [factura_emitida_reviewer_shape],
        "facturas_recibidas": [factura_recibida_reviewer_shape],
    }

    resultado = calcular(estado)  # must not raise pydantic.ValidationError

    assert resultado["resultado_m303"]["tipo_resultado"] != "sin_actividad"


def test_calcular_node_sin_perfil_fiscal_lanza_error(test_user_con_perfil):
    import pytest
    # A real JWT is required (RLS rejects an invalid/unsigned one outright,
    # before ever reaching the "no perfil_fiscal" check) — but the random
    # user_id below has no perfil_fiscal row, real auth or not.
    with pytest.raises(ValueError, match="No perfil_fiscal"):
        calcular({
            "user_id": "00000000-0000-0000-0000-000000000000",
            "user_jwt": test_user_con_perfil["jwt"],
            "ejercicio": 2099, "periodo": "1T",
            "fecha_inicio_periodo": "2099-01-01", "fecha_fin_periodo": "2099-03-31",
            "facturas_emitidas": [], "facturas_recibidas": [],
        })
