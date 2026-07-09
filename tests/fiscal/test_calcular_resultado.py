"""Tests for calcular_resultado_m303. Acceptance criteria: CA-F1-08.

Manual pre-calculation:
- a_ingresar: devengado 260.00, deducible 48.30, saldo_anterior 0 -> 211.70 (positive)
- a_compensar: devengado 50.00, deducible 200.00, saldo_anterior 0 -> -150.00 (negative)
- sin_actividad: devengado 0.00, deducible 0.00, saldo_anterior 0 -> 0.00, no invoices
"""
from decimal import Decimal

from src.fiscal.iva.calcular_resultado import calcular_resultado_m303
from src.fiscal.models import ResultadoDeducible, ResultadoDevengado


def test_calcular_resultado_m303_a_ingresar():
    devengado = ResultadoDevengado(por_tipo={21: Decimal("1200.00")}, cuotas={21: Decimal("260.00")}, total=Decimal("260.00"))
    deducible = ResultadoDeducible(por_categoria={"software": Decimal("48.30")}, total=Decimal("48.30"))
    resultado = calcular_resultado_m303(2026, "1T", devengado, deducible, Decimal("0.00"))
    assert resultado.resultado == Decimal("211.70")
    assert resultado.tipo_resultado == "a_ingresar"


def test_calcular_resultado_m303_a_compensar():
    devengado = ResultadoDevengado(por_tipo={21: Decimal("238.10")}, cuotas={21: Decimal("50.00")}, total=Decimal("50.00"))
    deducible = ResultadoDeducible(por_categoria={"vehiculo": Decimal("200.00")}, total=Decimal("200.00"))
    resultado = calcular_resultado_m303(2026, "1T", devengado, deducible, Decimal("0.00"))
    assert resultado.resultado == Decimal("-150.00")
    assert resultado.tipo_resultado == "a_compensar"


def test_calcular_resultado_m303_sin_actividad():
    devengado = ResultadoDevengado(por_tipo={}, cuotas={}, total=Decimal("0.00"))
    deducible = ResultadoDeducible(por_categoria={}, total=Decimal("0.00"))
    resultado = calcular_resultado_m303(2026, "1T", devengado, deducible, Decimal("0.00"))
    assert resultado.resultado == Decimal("0.00")
    assert resultado.tipo_resultado == "sin_actividad"


def test_calcular_resultado_m303_aplica_saldo_compensar_anterior():
    devengado = ResultadoDevengado(por_tipo={21: Decimal("1000.00")}, cuotas={21: Decimal("210.00")}, total=Decimal("210.00"))
    deducible = ResultadoDeducible(por_categoria={}, total=Decimal("0.00"))
    resultado = calcular_resultado_m303(2026, "2T", devengado, deducible, Decimal("150.00"))
    assert resultado.resultado == Decimal("60.00")
    assert resultado.tipo_resultado == "a_ingresar"
