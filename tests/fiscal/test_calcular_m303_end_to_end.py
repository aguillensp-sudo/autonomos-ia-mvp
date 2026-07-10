"""End-to-end tests for calcular_m303() against the 3 seed profiles.
Acceptance criteria: CA-F2-10. Tolerance: +/- 0.02 EUR (rounding).

Manual pre-calculation (from tests/fixtures/facturas.py, Phase 1 seed data):

Perfil 1 (solo servicios):
  Devengado: 6x(500.00@21%=105.00) + 3x(300.00@10%=30.00) + 1x(1000.00@0%=0.00)
           = 630.00 + 90.00 + 0.00 = 720.00
  Deducible: 1x software_saas 50.00@21%=10.50, 100% deducible = 10.50
  Resultado = 720.00 - 10.50 - 0 = 709.50 (a_ingresar)

Perfil 2 (mixto con gastos):
  Devengado: 4x(400.00@21%=84.00) = 336.00
  Deducible: vehiculo_estandar 42.00*50%=21.00, telefono_mixto 12.60*50%=6.30,
             comida_profesional 5.00*0%=0.00, cuota_reta 0.00*0%=0.00,
             software_saas 16.80*100%=16.80, equipo_informatico 189.00*100%=189.00
           = 21.00+6.30+0.00+0.00+16.80+189.00 = 233.10
  Resultado = 336.00 - 233.10 - 0 = 102.90 (a_ingresar)

Perfil 3 (con ISP):
  Devengado normal: 1x(800.00@21%=168.00) = 168.00
  ISP: factura software_saas 40.00 base, nif_proveedor=None -> ISP triggers.
       cuota_isp_devengada = 40.00*0.21 = 8.40. porcentaje_deducible=100 ->
       cuota_isp_deducible = 8.40 (net effect 0, but both sides must appear).
  Devengado total = 168.00 + 8.40 = 176.40
  Deducible normal = 0.00 (stored cuota_iva=0.00 for the ISP invoice)
  Deducible total = 0.00 + 8.40 = 8.40
  Resultado = 176.40 - 8.40 - 0 = 168.00 (a_ingresar)
"""
import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

import tests.fixtures.facturas as fixtures
from src.fiscal.iva.calcular_m303 import calcular_m303
from src.fiscal.models import FacturaEmitida, PerfilFiscal

load_dotenv()

TOLERANCIA = Decimal("0.02")
EJERCICIO_TEST = 2032  # isolated ejercicio to avoid cross-test saldo collisions


def _admin_client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def _get_or_create_user(admin, email: str) -> str:
    for user in admin.auth.admin.list_users():
        if user.email == email:
            return user.id
    created = admin.auth.admin.create_user({"email": email, "password": "e2e-test-password-123!", "email_confirm": True})
    return created.user.id


@pytest.fixture(scope="module", autouse=True)
def _usuarios_reales():
    """calcular_m303 persists to saldo_iva_compensar, which has a FK to
    auth.users — the fixtures module's PROFILE_X_USER_ID are random uuid4()
    values with no backing auth user, so we override them with the same real
    seeded test users scripts/seed_data.py creates (get-or-create, idempotent).
    """
    admin = _admin_client()
    fixtures.PROFILE_1_USER_ID = _get_or_create_user(admin, "perfil1-solo-servicios@test.autonomos.local")
    fixtures.PROFILE_2_USER_ID = _get_or_create_user(admin, "perfil2-mixto@test.autonomos.local")
    fixtures.PROFILE_3_USER_ID = _get_or_create_user(admin, "perfil3-isp@test.autonomos.local")


def _perfil(user_id) -> PerfilFiscal:
    from uuid import uuid4
    return PerfilFiscal(
        id=uuid4(),
        user_id=user_id,
        nif="12345678Z",
        nombre="Test Autónomo",
        epigrafe_iae="7622",
        regimen_iva="general",
        regimen_irpf="ed_normal",
        domicilio_fiscal={"calle": "Test", "numero": "1", "cp": "28001", "municipio": "Madrid", "provincia": "Madrid"},
        fecha_inicio=date(2020, 1, 1),
    )


@pytest.fixture(autouse=True)
def _limpiar_saldo():
    client = _admin_client()
    for user_id in (fixtures.PROFILE_1_USER_ID, fixtures.PROFILE_2_USER_ID, fixtures.PROFILE_3_USER_ID):
        client.table("saldo_iva_compensar").delete().eq("user_id", str(user_id)).eq("ejercicio", EJERCICIO_TEST).execute()
    yield


def _assert_cerca(actual: Decimal, esperado: Decimal):
    assert abs(actual - esperado) <= TOLERANCIA, f"esperado {esperado}, obtenido {actual} (diff {abs(actual - esperado)})"


def test_calcular_m303_perfil_1_solo_servicios():
    client = _admin_client()
    resultado, errores = calcular_m303(
        client=client,
        user_id=str(fixtures.PROFILE_1_USER_ID),
        ejercicio=EJERCICIO_TEST,
        periodo="1T",
        perfil_fiscal=_perfil(fixtures.PROFILE_1_USER_ID),
        facturas_emitidas=fixtures.facturas_emitidas_perfil_1(),
        facturas_recibidas=fixtures.facturas_recibidas_perfil_1(),
        fecha_inicio_periodo=date(2026, 1, 1),
        fecha_fin_periodo=date(2026, 3, 31),
    )
    assert errores == []
    _assert_cerca(resultado.resultado, Decimal("709.50"))
    assert resultado.tipo_resultado == "a_ingresar"


def test_calcular_m303_perfil_2_mixto_con_gastos():
    client = _admin_client()
    resultado, errores = calcular_m303(
        client=client,
        user_id=str(fixtures.PROFILE_2_USER_ID),
        ejercicio=EJERCICIO_TEST,
        periodo="1T",
        perfil_fiscal=_perfil(fixtures.PROFILE_2_USER_ID),
        facturas_emitidas=fixtures.facturas_emitidas_perfil_2(),
        facturas_recibidas=fixtures.facturas_recibidas_perfil_2(),
        fecha_inicio_periodo=date(2026, 1, 1),
        fecha_fin_periodo=date(2026, 3, 31),
    )
    assert errores == []
    _assert_cerca(resultado.resultado, Decimal("102.90"))
    assert resultado.tipo_resultado == "a_ingresar"


def test_calcular_m303_perfil_3_con_isp():
    client = _admin_client()
    resultado, errores = calcular_m303(
        client=client,
        user_id=str(fixtures.PROFILE_3_USER_ID),
        ejercicio=EJERCICIO_TEST,
        periodo="1T",
        perfil_fiscal=_perfil(fixtures.PROFILE_3_USER_ID),
        facturas_emitidas=fixtures.facturas_emitidas_perfil_3(),
        facturas_recibidas=fixtures.facturas_recibidas_perfil_3(),
        fecha_inicio_periodo=date(2026, 1, 1),
        fecha_fin_periodo=date(2026, 3, 31),
    )
    assert errores == []
    _assert_cerca(resultado.resultado, Decimal("168.00"))
    assert resultado.tipo_resultado == "a_ingresar"


def test_calcular_m303_perfil_1_persiste_saldo_para_siguiente_trimestre():
    """Confirms calcular_m303 actually calls actualizar_saldo_iva_compensar
    (CA-F2-08 wiring, not just the isolated function from Step 7)."""
    client = _admin_client()
    calcular_m303(
        client=client,
        user_id=str(fixtures.PROFILE_1_USER_ID),
        ejercicio=EJERCICIO_TEST,
        periodo="1T",
        perfil_fiscal=_perfil(fixtures.PROFILE_1_USER_ID),
        facturas_emitidas=fixtures.facturas_emitidas_perfil_1(),
        facturas_recibidas=fixtures.facturas_recibidas_perfil_1(),
        fecha_inicio_periodo=date(2026, 1, 1),
        fecha_fin_periodo=date(2026, 3, 31),
    )
    from src.fiscal.iva.actualizar_saldo_iva_compensar import leer_saldo_compensar
    saldo = leer_saldo_compensar(client, str(fixtures.PROFILE_1_USER_ID), EJERCICIO_TEST)
    # a_ingresar result -> saldo resets to 0 per SPEC-F2-06
    assert saldo == Decimal("0.00")


def _factura_intracom_o_exportacion(base, es_intracom=False, es_exportacion=False, cliente_empresario_ue=False) -> FacturaEmitida:
    return FacturaEmitida(
        id=uuid4(),
        user_id=uuid4(),
        numero_factura="F-BLOQUE-INFO",
        fecha=date(2026, 2, 1),
        base_imponible=Decimal(base),
        tipo_iva=0,
        cuota_iva=Decimal("0.00"),
        es_intracomunitaria=es_intracom,
        es_exportacion=es_exportacion,
        cliente_es_empresario_ue=cliente_empresario_ue,
    )


def test_calcular_m303_propaga_bloque_informativo_a_casillas():
    """Regression test for adversarial-review finding H1: calcular_bloque_informativo()
    was computed inside calcular_m303() but its result was discarded — resultado.casillas
    never carried casillas 59/60/61/62. None of the 3 seed profiles have
    intracomunitario/exportacion invoices, so this test uses a dedicated set."""
    client = _admin_client()
    user_id = fixtures.PROFILE_1_USER_ID  # reuse an already-seeded real auth user
    client.table("saldo_iva_compensar").delete().eq("user_id", str(user_id)).eq("ejercicio", EJERCICIO_TEST + 1).execute()

    facturas = [
        _factura_intracom_o_exportacion("1000.00", es_intracom=True, cliente_empresario_ue=False),  # -> 59
        _factura_intracom_o_exportacion("500.00", es_exportacion=True),  # -> 60
        _factura_intracom_o_exportacion("2000.00", es_intracom=True, cliente_empresario_ue=True),  # -> 62
    ]

    resultado, errores = calcular_m303(
        client=client,
        user_id=str(user_id),
        ejercicio=EJERCICIO_TEST + 1,  # isolated saldo row, avoids clashing with other tests in this module
        periodo="1T",
        perfil_fiscal=_perfil(user_id),
        facturas_emitidas=facturas,
        facturas_recibidas=[],
        fecha_inicio_periodo=date(2026, 1, 1),
        fecha_fin_periodo=date(2026, 3, 31),
    )

    assert resultado.casillas["59"] == Decimal("1000.00")
    assert resultado.casillas["60"] == Decimal("500.00")
    assert resultado.casillas["61"] == Decimal("0.00")
    assert resultado.casillas["62"] == Decimal("2000.00")

    client.table("saldo_iva_compensar").delete().eq("user_id", str(user_id)).eq("ejercicio", EJERCICIO_TEST + 1).execute()
