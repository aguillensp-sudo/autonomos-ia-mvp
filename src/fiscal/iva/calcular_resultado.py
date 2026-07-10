"""Art. 99 LIVA — right to deduction and liquidation mechanism (devengado -
deducible = resultado), computed here as casillas 70/71 of the M303."""
from decimal import Decimal

from src.fiscal.models import ResultadoDeducible, ResultadoDevengado, ResultadoM303


def calcular_resultado_m303(
    ejercicio: int,
    periodo: str,
    devengado: ResultadoDevengado,
    deducible: ResultadoDeducible,
    saldo_compensar_anterior: Decimal,
    solicita_devolucion: bool = False,
) -> ResultadoM303:
    """Art. 99 LIVA. Casilla 70/71 result: positive = a ingresar, negative = a compensar,
    zero with no invoices at all = sin_actividad. Applies casilla 110 carry-forward
    (saldo_compensar_anterior) before determining the final sign.

    Casuística C08 (Art. 115 LIVA — devoluciones): only in periodo == '4T' with
    a negative result, the caller (agent, per D12 in the P04 source spec) may
    set solicita_devolucion=True to route the negative result to casilla 72
    (a_devolver) instead of casilla 110 (a_compensar, carried to next year's 1T).

    devengado.total = casilla 27. deducible.total = casilla 45.
    Pure function. No rounding until this final step (2 decimals).
    """
    resultado = (devengado.total - deducible.total - saldo_compensar_anterior).quantize(Decimal("0.01"))

    sin_facturas = devengado.total == Decimal("0.00") and deducible.total == Decimal("0.00")

    if sin_facturas and saldo_compensar_anterior == Decimal("0.00"):
        tipo_resultado = "sin_actividad"
    elif resultado > Decimal("0.00"):
        tipo_resultado = "a_ingresar"
    elif resultado < Decimal("0.00") and periodo == "4T" and solicita_devolucion:
        tipo_resultado = "a_devolver"
    else:
        tipo_resultado = "a_compensar"

    casillas = {
        "27": devengado.total,
        "45": deducible.total,
        "70": resultado,
        "110": saldo_compensar_anterior,
    }
    if tipo_resultado == "a_devolver":
        casillas["72"] = abs(resultado)

    return ResultadoM303(
        ejercicio=ejercicio,
        periodo=periodo,
        total_devengado=devengado.total,
        total_deducible=deducible.total,
        saldo_compensar_anterior=saldo_compensar_anterior,
        resultado=resultado,
        tipo_resultado=tipo_resultado,
        casillas=casillas,
    )
