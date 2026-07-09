"""Art. 99.2 LIVA — coherence checks for a computed ResultadoM303 before it is
shown to the user or persisted. Art. 99.2 caps deductible VAT against accrued
VAT for the liquidation to be valid, which is exactly what these checks enforce
before a result is trusted. Never raises — returns the list of problems found
(empty if none)."""
from decimal import Decimal

from src.fiscal.models import ResultadoDeducible, ResultadoDevengado, ResultadoM303


def validar_coherencia_m303(
    resultado: ResultadoM303,
    devengado: ResultadoDevengado,
    deducible: ResultadoDeducible,
) -> list[str]:
    """Art. 99.2 LIVA. Returns a list of coherence errors (empty if none). Checks:
    - casilla 27 == devengado.total
    - casilla 45 == deducible.total
    - resultado.resultado == casilla27 - casilla45 - saldo_compensar_anterior
    """
    errores: list[str] = []

    casilla_27 = resultado.casillas.get("27")
    if casilla_27 != devengado.total:
        errores.append(
            f"Casilla 27 ({casilla_27}) no coincide con el total de IVA devengado calculado ({devengado.total})"
        )

    casilla_45 = resultado.casillas.get("45")
    if casilla_45 != deducible.total:
        errores.append(
            f"Casilla 45 ({casilla_45}) no coincide con el total de IVA deducible calculado ({deducible.total})"
        )

    esperado = (devengado.total - deducible.total - resultado.saldo_compensar_anterior).quantize(Decimal("0.01"))
    if resultado.resultado != esperado:
        errores.append(
            f"El resultado ({resultado.resultado}) no coincide con casilla 27 - casilla 45 - saldo anterior ({esperado})"
        )

    return errores
