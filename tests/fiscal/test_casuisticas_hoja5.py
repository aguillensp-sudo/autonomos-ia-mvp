"""Coverage for the casuísticas in Hoja 5 not already exercised by a dedicated
test module. Acceptance criteria: CA-F2-03, CA-F2-06, CA-F2-09.

Casuística coverage map for this change (11 total, C01-C11):
- C01 (sin actividad) -> test_c01_sin_actividad (this file) + Phase 1's
  test_calcular_resultado_m303_sin_actividad
- C02 (trimestres acumulados) -> RESCOPED, not a fiscal engine concern.
  See design.md "Casuística C02 — scope clarification". Covered minimally
  by test_c02_procesa_un_trimestre_aislado (this file). Detection/alerting
  itself is Phase 3 (agent/orchestration layer) — TODO: Phase 3.
- C03 (retención IRPF no afecta IVA) -> test_c03_* (this file)
- C04 (rectificativas) -> tests/fiscal/test_calcular_devengado.py
- C05 (ISP conocidos) -> tests/fiscal/test_calcular_isp.py
- C06 (criterio de caja) -> tests/fiscal/test_criterio_caja.py
- C07 (prorrata, actividades mixtas) -> test_c07_* (this file). MVP: ALERTAR
  only, per design.md — no proportional calculation attempted (V2 scope).
- C08 (devolución 4T vs compensación) -> test_c08_* (this file)
- C09 (autoliquidación rectificativa de un 303 ya presentado) -> OUT OF SCOPE
  for this change. Requires the RPA/filing capability (Phase 4) to correct an
  *already filed* declaration — belongs to a future, separate P04-R change
  per feature.md. No test written for it here, deliberately.
- C10 (exportación fuera UE) -> tests/fiscal/test_calcular_bloque_informativo.py
  (casilla 60 cases)
- C11 (venta B2B UE) -> tests/fiscal/test_calcular_bloque_informativo.py
  (casilla 62 cases)
"""
import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from supabase import create_client

from src.fiscal.iva.calcular_deducible import calcular_iva_deducible
from src.fiscal.iva.calcular_devengado import calcular_iva_devengado
from src.fiscal.iva.calcular_m303 import calcular_m303
from src.fiscal.iva.calcular_resultado import calcular_resultado_m303
from src.fiscal.iva.prorrata_alerta import detectar_alerta_prorrata
from src.fiscal.iva.tabla_deducibilidad import TABLA_DEDUCIBILIDAD
from src.fiscal.models import FacturaEmitida, PerfilFiscal

load_dotenv()

EJERCICIO_TEST = 2033  # isolated from other test modules


def _admin_client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def _get_or_create_user(admin, email: str) -> str:
    for user in admin.auth.admin.list_users():
        if user.email == email:
            return user.id
    created = admin.auth.admin.create_user({"email": email, "password": "c-test-password-123!", "email_confirm": True})
    return created.user.id


def _perfil(user_id, tiene_actividad_mixta: bool = False, regimen_iva: str = "general") -> PerfilFiscal:
    return PerfilFiscal(
        id=uuid4(),
        user_id=user_id,
        nif="12345678Z",
        nombre="Test Autónomo",
        epigrafe_iae="7622",
        regimen_iva=regimen_iva,
        regimen_irpf="ed_normal",
        domicilio_fiscal={"calle": "Test", "numero": "1", "cp": "28001", "municipio": "Madrid", "provincia": "Madrid"},
        fecha_inicio=date(2020, 1, 1),
        tiene_actividad_mixta=tiene_actividad_mixta,
    )


def _factura_emitida(base, tipo=21, retencion=Decimal("0")) -> FacturaEmitida:
    cuota = (Decimal(base) * Decimal(tipo) / Decimal("100")).quantize(Decimal("0.01"))
    return FacturaEmitida(
        id=uuid4(),
        user_id=uuid4(),
        numero_factura="F-1",
        fecha=date(2026, 3, 1),
        base_imponible=Decimal(base),
        tipo_iva=tipo,
        cuota_iva=cuota,
        retencion_irpf=retencion,
    )


# --- C01 — sin actividad ---

def test_c01_sin_actividad():
    devengado = calcular_iva_devengado([])
    deducible = calcular_iva_deducible([], TABLA_DEDUCIBILIDAD)
    resultado = calcular_resultado_m303(2026, "1T", devengado, deducible, Decimal("0.00"))
    assert resultado.tipo_resultado == "sin_actividad"
    assert resultado.resultado == Decimal("0.00")


# --- C02 — rescoped, engine-only scope (design.md) ---

def test_c02_procesa_un_trimestre_aislado():
    """calcular_m303 must process the requested quarter correctly regardless
    of how many other quarters are pending elsewhere — it has no visibility
    into (and must not try to query) filing history. That detection/alerting
    belongs to Phase 3."""
    admin = _admin_client()
    user_id = _get_or_create_user(admin, "c02-test-user@test.autonomos.local")
    admin.table("saldo_iva_compensar").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()

    # Simulate a "pending" prior presentacion existing in the DB — the engine
    # must not need to inspect or react to this table at all.
    admin.table("presentacion").insert({
        "id": str(uuid4()), "user_id": user_id, "proceso": "P04", "modelo": "303",
        "ejercicio": EJERCICIO_TEST - 1, "periodo": "4T", "estado": "pendiente",
    }).execute()

    resultado, errores = calcular_m303(
        client=admin, user_id=user_id, ejercicio=EJERCICIO_TEST, periodo="1T",
        perfil_fiscal=_perfil(user_id),
        facturas_emitidas=[_factura_emitida("1000.00")], facturas_recibidas=[],
        fecha_inicio_periodo=date(2026, 1, 1), fecha_fin_periodo=date(2026, 3, 31),
    )
    assert resultado.resultado == Decimal("210.00")
    assert errores == []

    admin.table("presentacion").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST - 1).execute()
    admin.table("saldo_iva_compensar").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()


# --- C03 — retención IRPF no afecta IVA ---

def test_c03_retencion_irpf_no_afecta_iva():
    sin_retencion = _factura_emitida("1000.00", retencion=Decimal("0"))
    con_retencion = _factura_emitida("1000.00", retencion=Decimal("15"))
    resultado_sin = calcular_iva_devengado([sin_retencion])
    resultado_con = calcular_iva_devengado([con_retencion])
    assert resultado_sin.total == resultado_con.total == Decimal("210.00")


# --- C07 — prorrata, MVP: alertar únicamente ---

def test_c07_prorrata_alerta_no_calculo():
    perfil_mixto = _perfil(uuid4(), tiene_actividad_mixta=True)
    alerta = detectar_alerta_prorrata(perfil_mixto)
    assert alerta is not None
    assert "prorrata" in alerta.lower()


def test_c07_sin_actividad_mixta_no_alerta():
    perfil_normal = _perfil(uuid4(), tiene_actividad_mixta=False)
    assert detectar_alerta_prorrata(perfil_normal) is None


def test_c07_calcular_m303_propaga_alerta_prorrata():
    """calcular_m303 must surface the C07 alert in its returned errores list
    when the profile has mixed activity — not just detectar_alerta_prorrata
    in isolation."""
    admin = _admin_client()
    user_id = _get_or_create_user(admin, "c07-test-user@test.autonomos.local")
    admin.table("saldo_iva_compensar").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()

    resultado, errores = calcular_m303(
        client=admin, user_id=user_id, ejercicio=EJERCICIO_TEST, periodo="1T",
        perfil_fiscal=_perfil(user_id, tiene_actividad_mixta=True),
        facturas_emitidas=[_factura_emitida("1000.00")], facturas_recibidas=[],
        fecha_inicio_periodo=date(2026, 1, 1), fecha_fin_periodo=date(2026, 3, 31),
    )
    assert any("prorrata" in e.lower() for e in errores)

    admin.table("saldo_iva_compensar").delete().eq("user_id", user_id).eq("ejercicio", EJERCICIO_TEST).execute()


# --- C08 — devolución 4T vs compensación ---

def test_c08_devolucion_4t_solicitada():
    devengado = calcular_iva_devengado([_factura_emitida("100.00")])  # 21.00
    deducible = calcular_iva_deducible(
        [], TABLA_DEDUCIBILIDAD,
    )
    # Force a negative result via a large saldo_compensar_anterior
    resultado = calcular_resultado_m303(
        2026, "4T", devengado, deducible, saldo_compensar_anterior=Decimal("300.00"),
        solicita_devolucion=True,
    )
    assert resultado.tipo_resultado == "a_devolver"
    assert resultado.casillas["72"] == abs(resultado.resultado)
    assert "110" in resultado.casillas  # still recorded, just not the active routing


def test_c08_compensacion_4t_sin_solicitar_devolucion():
    devengado = calcular_iva_devengado([_factura_emitida("100.00")])
    deducible = calcular_iva_deducible([], TABLA_DEDUCIBILIDAD)
    resultado = calcular_resultado_m303(
        2026, "4T", devengado, deducible, saldo_compensar_anterior=Decimal("300.00"),
        solicita_devolucion=False,
    )
    assert resultado.tipo_resultado == "a_compensar"
    assert "72" not in resultado.casillas


def test_c08_devolucion_ignorada_fuera_de_4t():
    """solicita_devolucion is only meaningful in 4T — a 1T negative result
    with solicita_devolucion=True still routes to a_compensar."""
    devengado = calcular_iva_devengado([_factura_emitida("100.00")])
    deducible = calcular_iva_deducible([], TABLA_DEDUCIBILIDAD)
    resultado = calcular_resultado_m303(
        2026, "1T", devengado, deducible, saldo_compensar_anterior=Decimal("300.00"),
        solicita_devolucion=True,
    )
    assert resultado.tipo_resultado == "a_compensar"
