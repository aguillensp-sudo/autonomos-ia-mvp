"""Seed fixtures for the 3 autónomo profiles. Acceptance criteria: CA-F1-05.

Profile 1 — solo servicios: only 21% issued invoices, minimal expenses.
Profile 2 — mixto con gastos: issued invoices + vehicle/phone/restaurant expenses.
Profile 3 — con ISP: includes a received invoice from a foreign supplier without
Spanish NIF (Google Ireland Ltd) to exercise es_isp=True. Full ISP calculation
logic ships in Phase 2 — this phase only needs the flagged data to exist.
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.fiscal.models import FacturaEmitida, FacturaRecibida

PROFILE_1_USER_ID = uuid4()
PROFILE_2_USER_ID = uuid4()
PROFILE_3_USER_ID = uuid4()


def _emitida(user_id, numero, fecha, base, tipo, cuota, nif_cliente="12345678Z", retencion=Decimal("0")):
    cuota_retencion = (Decimal(base) * retencion / Decimal("100")).quantize(Decimal("0.01"))
    return FacturaEmitida(
        id=uuid4(),
        user_id=user_id,
        numero_factura=numero,
        fecha=fecha,
        nif_cliente=nif_cliente,
        base_imponible=Decimal(base),
        tipo_iva=tipo,
        cuota_iva=Decimal(cuota),
        retencion_irpf=retencion,
        cuota_retencion=cuota_retencion,
    )


def _recibida(user_id, categoria, fecha, base, tipo, cuota, porcentaje, nif_proveedor="87654321X", es_isp=False, nombre_proveedor=None, es_bien_inversion=False):
    return FacturaRecibida(
        id=uuid4(),
        user_id=user_id,
        fecha=fecha,
        nif_proveedor=nif_proveedor,
        nombre_proveedor=nombre_proveedor,
        categoria_gasto=categoria,
        base_imponible=Decimal(base),
        tipo_iva=tipo,
        cuota_iva=Decimal(cuota),
        porcentaje_deducible=Decimal(porcentaje),
        es_isp=es_isp,
        es_bien_inversion=es_bien_inversion,
    )


def facturas_emitidas_perfil_1() -> list[FacturaEmitida]:
    """Solo servicios — 10 issued invoices across 0/10/21% rates."""
    return [
        _emitida(PROFILE_1_USER_ID, f"F1-{i:03d}", date(2026, 1, 5 + i), "500.00", 21, "105.00")
        for i in range(6)
    ] + [
        _emitida(PROFILE_1_USER_ID, f"F1-{i:03d}", date(2026, 2, 1 + i), "300.00", 10, "30.00")
        for i in range(6, 9)
    ] + [
        _emitida(PROFILE_1_USER_ID, "F1-009", date(2026, 3, 1), "1000.00", 0, "0.00"),
    ]


def facturas_recibidas_perfil_1() -> list[FacturaRecibida]:
    return [
        _recibida(PROFILE_1_USER_ID, "software_saas", date(2026, 1, 10), "50.00", 21, "10.50", "100"),
    ]


def facturas_emitidas_perfil_2() -> list[FacturaEmitida]:
    """Mixto con gastos."""
    return [
        _emitida(PROFILE_2_USER_ID, f"F2-{i:03d}", date(2026, 1, 5 + i), "400.00", 21, "84.00")
        for i in range(4)
    ]


def facturas_recibidas_perfil_2() -> list[FacturaRecibida]:
    return [
        _recibida(PROFILE_2_USER_ID, "vehiculo_estandar", date(2026, 1, 12), "200.00", 21, "42.00", "50"),
        _recibida(PROFILE_2_USER_ID, "telefono_mixto", date(2026, 1, 15), "60.00", 21, "12.60", "50"),
        _recibida(PROFILE_2_USER_ID, "comida_profesional", date(2026, 1, 20), "50.00", 10, "5.00", "0"),
        _recibida(PROFILE_2_USER_ID, "cuota_reta", date(2026, 1, 1), "300.00", 0, "0.00", "0"),
        _recibida(PROFILE_2_USER_ID, "software_saas", date(2026, 1, 22), "80.00", 21, "16.80", "100"),
        _recibida(
            PROFILE_2_USER_ID, "equipo_informatico", date(2026, 1, 25), "900.00", 21, "189.00", "100",
            es_bien_inversion=True,
        ),
    ]


def facturas_emitidas_perfil_3() -> list[FacturaEmitida]:
    """Con ISP — 1 issued invoice with retención IRPF (CA-F1-05 requires >= 1)."""
    return [
        _emitida(
            PROFILE_3_USER_ID, "F3-001", date(2026, 1, 8), "800.00", 21, "168.00",
            retencion=Decimal("15"),
        ),
    ]


def facturas_recibidas_perfil_3() -> list[FacturaRecibida]:
    return [
        _recibida(
            PROFILE_3_USER_ID, "software_saas", date(2026, 1, 15), "40.00", 0, "0.00", "100",
            nif_proveedor=None, es_isp=True, nombre_proveedor="Google Ireland Ltd",
        ),
    ]


def todas_las_facturas_emitidas() -> list[FacturaEmitida]:
    return facturas_emitidas_perfil_1() + facturas_emitidas_perfil_2() + facturas_emitidas_perfil_3()


def todas_las_facturas_recibidas() -> list[FacturaRecibida]:
    return facturas_recibidas_perfil_1() + facturas_recibidas_perfil_2() + facturas_recibidas_perfil_3()
