"""Tests for calcular_bloque_informativo (casillas 59-63). Acceptance criteria: CA-F2-07."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.fiscal.iva.calcular_bloque_informativo import calcular_bloque_informativo
from src.fiscal.models import FacturaEmitida


def _factura(base, tipo=21, es_intracom=False, es_exportacion=False, cliente_empresario_ue=False):
    cuota = (Decimal(base) * Decimal(tipo) / Decimal("100")).quantize(Decimal("0.01"))
    return FacturaEmitida(
        id=uuid4(),
        user_id=uuid4(),
        numero_factura="F-1",
        fecha=date(2026, 3, 1),
        base_imponible=Decimal(base),
        tipo_iva=tipo,
        cuota_iva=cuota,
        es_intracomunitaria=es_intracom,
        es_exportacion=es_exportacion,
        cliente_es_empresario_ue=cliente_empresario_ue,
    )


def test_calcular_bloque_informativo_casilla_59_venta_ue_bien():
    # Intracom sale to a non-business (goods) client -> casilla 59, not 62
    facturas = [_factura("1000.00", tipo=0, es_intracom=True, cliente_empresario_ue=False)]
    resultado = calcular_bloque_informativo(facturas)
    assert resultado.casilla_59 == Decimal("1000.00")
    assert resultado.casilla_62 == Decimal("0.00")


def test_calcular_bloque_informativo_casilla_60_exportacion():
    facturas = [_factura("500.00", tipo=0, es_exportacion=True)]
    resultado = calcular_bloque_informativo(facturas)
    assert resultado.casilla_60 == Decimal("500.00")


def test_calcular_bloque_informativo_casilla_62_servicio_b2b_ue():
    # Intracom B2B service -> casilla 62, not 59
    facturas = [_factura("2000.00", tipo=0, es_intracom=True, cliente_empresario_ue=True)]
    resultado = calcular_bloque_informativo(facturas)
    assert resultado.casilla_62 == Decimal("2000.00")
    assert resultado.casilla_59 == Decimal("0.00")


def test_calcular_bloque_informativo_casilla_61_default_cero():
    facturas = [_factura("1000.00", tipo=21)]  # domestic, standard sale
    resultado = calcular_bloque_informativo(facturas)
    assert resultado.casilla_61 == Decimal("0.00")


def test_calcular_bloque_informativo_mixto():
    facturas = [
        _factura("1000.00", tipo=0, es_intracom=True, cliente_empresario_ue=False),  # 59
        _factura("500.00", tipo=0, es_exportacion=True),  # 60
        _factura("2000.00", tipo=0, es_intracom=True, cliente_empresario_ue=True),  # 62
        _factura("300.00", tipo=21),  # domestic, none of the above
    ]
    resultado = calcular_bloque_informativo(facturas)
    assert resultado.casilla_59 == Decimal("1000.00")
    assert resultado.casilla_60 == Decimal("500.00")
    assert resultado.casilla_62 == Decimal("2000.00")
    assert resultado.casilla_61 == Decimal("0.00")
