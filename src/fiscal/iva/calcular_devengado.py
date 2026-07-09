"""Art. 92 LIVA — cálculo del IVA devengado (repercutido)."""
from decimal import Decimal

from src.fiscal.models import FacturaEmitida, ResultadoDevengado


def calcular_iva_devengado(facturas_emitidas: list[FacturaEmitida]) -> ResultadoDevengado:
    """Sum of accrued VAT (IVA repercutido) across issued invoices, broken down by rate.

    Art. 92 LIVA. Pure function: same input always produces same output.
    No rounding in intermediate steps — inputs already carry their final cuota_iva,
    this function only aggregates.
    """
    por_tipo: dict[int, Decimal] = {}
    cuotas: dict[int, Decimal] = {}

    for factura in facturas_emitidas:
        tipo = factura.tipo_iva
        por_tipo[tipo] = por_tipo.get(tipo, Decimal("0.00")) + factura.base_imponible
        cuotas[tipo] = cuotas.get(tipo, Decimal("0.00")) + factura.cuota_iva

    total = sum(cuotas.values(), Decimal("0.00"))

    return ResultadoDevengado(por_tipo=por_tipo, cuotas=cuotas, total=total)
