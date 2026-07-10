"""Integration tests for saldo_iva_compensar real persistence against local
Supabase. Acceptance criteria: CA-F2-08.
"""
import os
from decimal import Decimal

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.fiscal.iva.actualizar_saldo_iva_compensar import (
    actualizar_saldo_iva_compensar,
    leer_saldo_compensar,
)
from src.fiscal.models import ResultadoM303

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
TEST_PASSWORD = "saldo-test-password-123!"
EJERCICIO_TEST = 2031  # far-future year, isolated from other tests' data


def _admin_client():
    return create_client(SUPABASE_URL, SERVICE_KEY)


@pytest.fixture(scope="module")
def test_user_id():
    admin = _admin_client()
    email = "saldo-iva-test-user@test.autonomos.local"
    for user in admin.auth.admin.list_users():
        if user.email == email:
            user_id = user.id
            break
    else:
        created = admin.auth.admin.create_user(
            {"email": email, "password": TEST_PASSWORD, "email_confirm": True}
        )
        user_id = created.user.id

    # Clean slate for this ejercicio before each test module run
    admin.table("saldo_iva_compensar").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()
    yield user_id
    admin.table("saldo_iva_compensar").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()


def _resultado(tipo_resultado: str, resultado: str) -> ResultadoM303:
    return ResultadoM303(
        ejercicio=EJERCICIO_TEST,
        periodo="1T",
        total_devengado=Decimal("0.00"),
        total_deducible=Decimal("0.00"),
        saldo_compensar_anterior=Decimal("0.00"),
        resultado=Decimal(resultado),
        tipo_resultado=tipo_resultado,
    )


def test_leer_saldo_compensar_sin_registro_previo_devuelve_cero(test_user_id):
    client = _admin_client()
    saldo = leer_saldo_compensar(client, test_user_id, EJERCICIO_TEST)
    assert saldo == Decimal("0.00")


def test_actualizar_saldo_iva_compensar_persiste_a_compensar(test_user_id):
    client = _admin_client()
    resultado = _resultado("a_compensar", "-300.00")
    nuevo_saldo = actualizar_saldo_iva_compensar(client, test_user_id, EJERCICIO_TEST, resultado)
    assert nuevo_saldo == Decimal("300.00")


def test_leer_saldo_compensar_recupera_valor_persistido(test_user_id):
    client = _admin_client()
    # Depends on the previous test having persisted 300.00 — read it back
    # exactly as a "next quarter" read would.
    saldo = leer_saldo_compensar(client, test_user_id, EJERCICIO_TEST)
    assert saldo == Decimal("300.00")


def test_actualizar_saldo_iva_compensar_a_ingresar_resetea_a_cero(test_user_id):
    client = _admin_client()
    resultado = _resultado("a_ingresar", "150.00")
    nuevo_saldo = actualizar_saldo_iva_compensar(client, test_user_id, EJERCICIO_TEST, resultado)
    assert nuevo_saldo == Decimal("0.00")
    assert leer_saldo_compensar(client, test_user_id, EJERCICIO_TEST) == Decimal("0.00")


def test_actualizar_saldo_iva_compensar_sin_actividad_no_cambia(test_user_id):
    client = _admin_client()
    actualizar_saldo_iva_compensar(client, test_user_id, EJERCICIO_TEST, _resultado("a_compensar", "-50.00"))
    nuevo_saldo = actualizar_saldo_iva_compensar(client, test_user_id, EJERCICIO_TEST, _resultado("sin_actividad", "0.00"))
    assert nuevo_saldo == Decimal("50.00")
