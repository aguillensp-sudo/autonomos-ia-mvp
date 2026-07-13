"""Tests for calcular_iva_deducible. Acceptance criteria: CA-F1-07, CA-F2-01.

Manual pre-calculation:
- vehiculo_estandar: base 200.00, tipo 21% -> cuota_iva 42.00, deducible 50% -> 21.00
- software_saas: base 100.00, tipo 21% -> cuota_iva 21.00, deducible 100% -> 21.00
- comida_profesional: base 50.00,  tipo 10% -> cuota_iva 5.00,  deducible 0% default -> 0.00
- telefono_mixto: base 60.00, tipo 21% -> cuota_iva 12.60, deducible 50% -> 6.30
- cuota_reta: base 300.00, tipo 0% -> cuota_iva 0.00, deducible 0% -> 0.00
Total deducible (casilla 45) = 21.00 + 21.00 + 0.00 + 6.30 + 0.00 = 48.30

Note (Phase 2): category keys renamed from Phase 1's 5-category subset to match
the full 22-category table in specs/calculo-iva-completo/design.md SPEC-F2-01:
"vehiculo" -> "vehiculo_estandar", "software" -> "software_saas",
"comida" -> "comida_profesional". "telefono_mixto" and "cuota_reta" unchanged.
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.fiscal.iva.calcular_deducible import calcular_iva_deducible
from src.fiscal.iva.tabla_deducibilidad import TABLA_DEDUCIBILIDAD
from src.fiscal.models import FacturaRecibida


def _gasto(categoria: str, base: str, tipo: int, cuota: str, porcentaje: str, requiere_confirmacion: bool = False) -> FacturaRecibida:
    return FacturaRecibida(
        id=uuid4(),
        user_id=uuid4(),
        fecha=date(2026, 3, 1),
        categoria_gasto=categoria,
        base_imponible=Decimal(base),
        tipo_iva=tipo,
        cuota_iva=Decimal(cuota),
        porcentaje_deducible=Decimal(porcentaje),
        requiere_confirmacion=requiere_confirmacion,
    )


def test_calcular_iva_deducible_vehiculo_estandar():
    gastos = [_gasto("vehiculo_estandar", "200.00", 21, "42.00", "50", requiere_confirmacion=True)]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["vehiculo_estandar"] == Decimal("21.00")
    assert resultado.total == Decimal("21.00")


def test_calcular_iva_deducible_software_profesional():
    gastos = [_gasto("software_saas", "100.00", 21, "21.00", "100")]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["software_saas"] == Decimal("21.00")


def test_calcular_iva_deducible_comida_default():
    gastos = [_gasto("comida_profesional", "50.00", 10, "5.00", "0")]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["comida_profesional"] == Decimal("0.00")


def test_calcular_iva_deducible_comida_requiere_confirmacion():
    """Comidas en restaurante son 'dudosas' — deben marcarse requiere_confirmacion=True
    y el agente propone (no asume) el porcentaje segun confirmacion del usuario."""
    gasto = _gasto("comida_profesional", "50.00", 10, "5.00", "100", requiere_confirmacion=True)
    assert gasto.requiere_confirmacion is True
    resultado = calcular_iva_deducible([gasto], TABLA_DEDUCIBILIDAD)
    # If the user confirmed 100% deductible, the engine trusts porcentaje_deducible
    # from the invoice — it never overrides the confirmed value with the table default.
    assert resultado.por_categoria["comida_profesional"] == Decimal("5.00")


def test_calcular_iva_deducible_telefono_mixto():
    gastos = [_gasto("telefono_mixto", "60.00", 21, "12.60", "50")]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["telefono_mixto"] == Decimal("6.30")


def test_calcular_iva_deducible_cuota_reta():
    gastos = [_gasto("cuota_reta", "300.00", 0, "0.00", "0")]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.por_categoria["cuota_reta"] == Decimal("0.00")


def test_calcular_iva_deducible_suministros_domicilio_proporcional():
    """suministros_domicilio no tiene un porcentaje fijo en la tabla — el motor
    debe usar el porcentaje_deducible de la propia factura (calculado a partir
    de m2 despacho / m2 vivienda al ingerir la factura), no un valor de tabla."""
    gasto = _gasto("suministros_domicilio", "100.00", 21, "21.00", "15", requiere_confirmacion=True)
    assert gasto.requiere_confirmacion is True
    resultado = calcular_iva_deducible([gasto], TABLA_DEDUCIBILIDAD)
    # 15% is the invoice's own computed proportion, not any fixed table value —
    # if the engine had incorrectly hardcoded a table percentage, this would fail.
    assert resultado.por_categoria["suministros_domicilio"] == Decimal("3.15")


def test_calcular_iva_deducible_total_multiples_categorias():
    gastos = [
        _gasto("vehiculo_estandar", "200.00", 21, "42.00", "50"),
        _gasto("software_saas", "100.00", 21, "21.00", "100"),
        _gasto("comida_profesional", "50.00", 10, "5.00", "0"),
        _gasto("telefono_mixto", "60.00", 21, "12.60", "50"),
        _gasto("cuota_reta", "300.00", 0, "0.00", "0"),
    ]
    resultado = calcular_iva_deducible(gastos, TABLA_DEDUCIBILIDAD)
    assert resultado.total == Decimal("48.30")
