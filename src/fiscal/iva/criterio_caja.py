"""Art. 163 terdecies LIVA — régimen especial del criterio de caja (RECC).
Casuística C06."""
from datetime import date

from src.fiscal.models import FacturaEmitida, FacturaRecibida


def filtrar_por_criterio_caja(
    facturas_emitidas: list[FacturaEmitida],
    facturas_recibidas: list[FacturaRecibida],
    regimen_iva: str,
    fecha_inicio_periodo: date,
    fecha_fin_periodo: date,
) -> tuple[list[FacturaEmitida], list[FacturaRecibida]]:
    """Art. 163 terdecies LIVA. If regimen_iva != 'criterio_caja': returns the
    inputs unchanged (Phase 1 behavior — invoices are already filtered by
    issue date upstream).

    If regimen_iva == 'criterio_caja': IVA devengado/deducible is recognized
    on COLLECTION/PAYMENT, not on issue. Filters facturas_emitidas to those
    with cobrada=True and fecha_cobro within [fecha_inicio_periodo,
    fecha_fin_periodo]; facturas_recibidas to those with pagada=True and
    fecha_pago within the same range.
    """
    if regimen_iva != "criterio_caja":
        return facturas_emitidas, facturas_recibidas

    emitidas_filtradas = [
        f for f in facturas_emitidas
        if f.cobrada and f.fecha_cobro is not None
        and fecha_inicio_periodo <= f.fecha_cobro <= fecha_fin_periodo
    ]
    recibidas_filtradas = [
        f for f in facturas_recibidas
        if f.pagada and f.fecha_pago is not None
        and fecha_inicio_periodo <= f.fecha_pago <= fecha_fin_periodo
    ]

    return emitidas_filtradas, recibidas_filtradas
