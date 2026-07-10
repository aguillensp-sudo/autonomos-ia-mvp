"""Tests for calcular_iva_devengado. Acceptance criteria: CA-F1-06.

Manual pre-calculation for test_calcular_iva_devengado_multiples_tipos:
- Factura A: base 1000.00, tipo 21% -> cuota 210.00
- Factura B: base 500.00,  tipo 10% -> cuota 50.00
- Factura C: base 200.00,  tipo 0%  -> cuota 0.00
Total devengado (casilla 27) = 210.00 + 50.00 + 0.00 = 260.00
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.fiscal.iva.calcular_devengado import calcular_iva_devengado
from src.fiscal.models import FacturaEmitida


def _factura(base: str, tipo: int, cuota: str, **kwargs) -> FacturaEmitida:
    return FacturaEmitida(
        id=uuid4(),
        user_id=uuid4(),
        numero_factura="F-1",
        fecha=date(2026, 3, 1),
        base_imponible=Decimal(base),
        tipo_iva=tipo,
        cuota_iva=Decimal(cuota),
        **kwargs,
    )


def test_calcular_iva_devengado_multiples_tipos():
    facturas = [
        _factura("1000.00", 21, "210.00"),
        _factura("500.00", 10, "50.00"),
        _factura("200.00", 0, "0.00"),
    ]
    resultado = calcular_iva_devengado(facturas)
    assert resultado.por_tipo == {21: Decimal("1000.00"), 10: Decimal("500.00"), 0: Decimal("200.00")}
    assert resultado.cuotas == {21: Decimal("210.00"), 10: Decimal("50.00"), 0: Decimal("0.00")}
    assert resultado.total == Decimal("260.00")


def test_calcular_iva_devengado_sin_facturas():
    resultado = calcular_iva_devengado([])
    assert resultado.por_tipo == {}
    assert resultado.cuotas == {}
    assert resultado.total == Decimal("0.00")


def test_calcular_iva_devengado_mismo_tipo_suma_acumulada():
    facturas = [
        _factura("100.00", 21, "21.00"),
        _factura("50.00", 21, "10.50"),
    ]
    resultado = calcular_iva_devengado(facturas)
    assert resultado.por_tipo == {21: Decimal("150.00")}
    assert resultado.cuotas == {21: Decimal("31.50")}
    assert resultado.total == Decimal("31.50")


def test_calcular_devengado_rectificativa_mismo_trimestre():
    """A credit-note (rectificativa) for an invoice declared in the SAME
    quarter cancels out directly in the normal cuotas/por_tipo breakdown —
    no casilla 14/15 routing needed, since both original and rectificativa
    are in this same calculation batch. Acceptance criteria: CA-F2-04.
    """
    original_id = uuid4()
    original = _factura("1000.00", 21, "210.00")
    object.__setattr__(original, "id", original_id)
    rectificativa = _factura(
        "-200.00", 21, "-42.00",
        es_rectificativa=True, factura_original_id=original_id,
    )
    resultado = calcular_iva_devengado([original, rectificativa])
    assert resultado.cuotas[21] == Decimal("168.00")
    assert resultado.base_modificacion == Decimal("0.00")
    assert resultado.cuota_modificacion == Decimal("0.00")
    assert resultado.total == Decimal("168.00")


def test_calcular_devengado_rectificativa_trimestre_diferente():
    """A rectificativa whose original invoice is NOT in this batch (it was
    declared in a prior, already-filed quarter) routes to casillas 14-15
    (base_modificacion/cuota_modificacion) instead of the normal cuotas.
    Acceptance criteria: CA-F2-04.
    """
    original_id_de_otro_trimestre = uuid4()  # not present in this batch
    rectificativa = _factura(
        "-200.00", 21, "-42.00",
        es_rectificativa=True, factura_original_id=original_id_de_otro_trimestre,
    )
    otra_factura = _factura("500.00", 21, "105.00")
    resultado = calcular_iva_devengado([otra_factura, rectificativa])
    assert resultado.cuotas[21] == Decimal("105.00")  # unaffected by the rectificativa
    assert resultado.base_modificacion == Decimal("-200.00")
    assert resultado.cuota_modificacion == Decimal("-42.00")
    assert resultado.total == Decimal("63.00")  # 105.00 + (-42.00)
