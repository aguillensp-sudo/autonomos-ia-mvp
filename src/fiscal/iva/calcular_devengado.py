"""Art. 92 LIVA — cálculo del IVA devengado (repercutido)."""
from decimal import Decimal

from src.fiscal.models import FacturaEmitida, ResultadoDevengado


def calcular_iva_devengado(facturas_emitidas: list[FacturaEmitida]) -> ResultadoDevengado:
    """Sum of accrued VAT (IVA repercutido) across issued invoices, broken down by rate.

    Art. 92 LIVA. Pure function: same input always produces same output.
    No rounding in intermediate steps — inputs already carry their final cuota_iva,
    this function only aggregates.

    Facturas rectificativas (casuística C04, Art. 89 LIVA): a rectificativa whose
    `factura_original_id` resolves to another invoice present in THIS SAME batch
    is being declared in the same quarter as the invoice it corrects — it is
    summed directly into `por_tipo`/`cuotas` like any other invoice (their
    negative amount naturally cancels part of the original). A rectificativa
    whose `factura_original_id` does NOT resolve within this batch is correcting
    an invoice from an already-filed, different quarter — it is routed instead
    to `base_modificacion`/`cuota_modificacion` (casillas 14-15), not into the
    regular per-rate breakdown.
    """
    por_tipo: dict[int, Decimal] = {}
    cuotas: dict[int, Decimal] = {}
    base_modificacion = Decimal("0.00")
    cuota_modificacion = Decimal("0.00")

    ids_en_este_lote = {factura.id for factura in facturas_emitidas}

    for factura in facturas_emitidas:
        es_rectificativa_de_otro_trimestre = (
            factura.es_rectificativa
            and factura.factura_original_id is not None
            and factura.factura_original_id not in ids_en_este_lote
        )
        if es_rectificativa_de_otro_trimestre:
            base_modificacion += factura.base_imponible
            cuota_modificacion += factura.cuota_iva
            continue

        tipo = factura.tipo_iva
        por_tipo[tipo] = por_tipo.get(tipo, Decimal("0.00")) + factura.base_imponible
        cuotas[tipo] = cuotas.get(tipo, Decimal("0.00")) + factura.cuota_iva

    total = sum(cuotas.values(), Decimal("0.00")) + cuota_modificacion

    return ResultadoDevengado(
        por_tipo=por_tipo,
        cuotas=cuotas,
        base_modificacion=base_modificacion,
        cuota_modificacion=cuota_modificacion,
        total=total,
    )
