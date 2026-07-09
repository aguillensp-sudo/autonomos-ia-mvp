"""Tests for validar_coherencia_m303. Acceptance criteria: CA-F1-09."""
from decimal import Decimal

from src.fiscal.iva.calcular_resultado import calcular_resultado_m303
from src.fiscal.iva.validar_coherencia import validar_coherencia_m303
from src.fiscal.models import ResultadoDeducible, ResultadoDevengado


def _devengado(total: str) -> ResultadoDevengado:
    return ResultadoDevengado(por_tipo={21: Decimal(total)}, cuotas={21: Decimal(total)}, total=Decimal(total))


def _deducible(total: str) -> ResultadoDeducible:
    return ResultadoDeducible(por_categoria={"software": Decimal(total)}, total=Decimal(total))


def test_validar_coherencia_m303_sin_incoherencias():
    devengado = _devengado("260.00")
    deducible = _deducible("48.30")
    resultado = calcular_resultado_m303(2026, "1T", devengado, deducible, Decimal("0.00"))
    errores = validar_coherencia_m303(resultado, devengado, deducible)
    assert errores == []


def test_validar_coherencia_m303_casilla_27_incoherente():
    devengado = _devengado("260.00")
    deducible = _deducible("48.30")
    resultado = calcular_resultado_m303(2026, "1T", devengado, deducible, Decimal("0.00"))
    # Tamper casilla 27 to simulate an inconsistent stored result
    resultado.casillas["27"] = Decimal("999.99")
    errores = validar_coherencia_m303(resultado, devengado, deducible)
    assert any("27" in e for e in errores)


def test_validar_coherencia_m303_casilla_45_incoherente():
    devengado = _devengado("260.00")
    deducible = _deducible("48.30")
    resultado = calcular_resultado_m303(2026, "1T", devengado, deducible, Decimal("0.00"))
    resultado.casillas["45"] = Decimal("999.99")
    errores = validar_coherencia_m303(resultado, devengado, deducible)
    assert any("45" in e for e in errores)


def test_validar_coherencia_m303_resultado_incoherente():
    devengado = _devengado("260.00")
    deducible = _deducible("48.30")
    resultado = calcular_resultado_m303(2026, "1T", devengado, deducible, Decimal("0.00"))
    resultado.resultado = Decimal("1.00")  # should be 211.70
    errores = validar_coherencia_m303(resultado, devengado, deducible)
    assert any("resultado" in e.lower() for e in errores)
