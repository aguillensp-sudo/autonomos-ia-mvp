"""Tests for calcular_iva_deducible. Acceptance criteria: CA-F1-07.

Manual pre-calculation:
- vehiculo: base 200.00, tipo 21% -> cuota_iva 42.00, deducible 50% -> 21.00
- software: base 100.00, tipo 21% -> cuota_iva 21.00, deducible 100% -> 21.00
- comida:   base 50.00,  tipo 10% -> cuota_iva 5.00,  deducible 0% default -> 0.00
- telefono_mixto: base 60.00, tipo 21% -> cuota_iva 12.60, deducible 50% -> 6.30
- cuota_reta: base 300.00, tipo 0% -> cuota_iva 0.00, deducible 0% -> 0.00
Total deducible (casilla 45) = 21.00 + 21.00 + 0.00 + 6.30 + 0.00 = 48.30
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.fiscal.iva.calcular_deducible import calcular_iva_deducible
from src.fiscal.iva.tabla_deducibilidad import TABLA_DEDUCIBILIDAD
from src.fiscal.models import FacturaRecibida


def _gasto(categoria: str, base: str, tipo: int, cuota: str, porcentaje: str) -> FacturaRecibida:
    return FacturaRecibida(
        id=uuid4(),
        user_id=uuid4(),
        fecha=date(2026, 3, 1),
        categoria_gasto=categoria,
        base_imponible=Decimal(base),
        tipo_iva=tipo,
        cuota_iva=Decimal(cuota),
        porcentaje_deducible=Decimal(porcentaje),
    )


def test_calcular_iva_deducible_vehiculo_uso_mixto():
    gastos = [_gasto("vehiculo", "200.00", 21, "42.00", "50")]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["vehiculo"] == Decimal("21.00")
    assert resultado.total == Decimal("21.00")


def test_calcular_iva_deducible_software_profesional():
    gastos = [_gasto("software", "100.00", 21, "21.00", "100")]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["software"] == Decimal("21.00")


def test_calcular_iva_deducible_comida_default():
    gastos = [_gasto("comida", "50.00", 10, "5.00", "0")]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["comida"] == Decimal("0.00")


def test_calcular_iva_deducible_telefono_mixto():
    gastos = [_gasto("telefono_mixto", "60.00", 21, "12.60", "50")]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["telefono_mixto"] == Decimal("6.30")


def test_calcular_iva_deducible_cuota_reta():
    gastos = [_gasto("cuota_reta", "300.00", 0, "0.00", "0")]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["cuota_reta"] == Decimal("0.00")


def test_calcular_iva_deducible_total_multiples_categorias():
    gastos = [
        _gasto("vehiculo", "200.00", 21, "42.00", "50"),
        _gasto("software", "100.00", 21, "21.00", "100"),
        _gasto("comida", "50.00", 10, "5.00", "0"),
        _gasto("telefono_mixto", "60.00", 21, "12.60", "50"),
        _gasto("cuota_reta", "300.00", 0, "0.00", "0"),
    ]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.total == Decimal("48.30")
