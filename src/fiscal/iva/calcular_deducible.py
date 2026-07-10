"""Art. 95 LIVA — cálculo del IVA deducible (soportado)."""
from decimal import Decimal

from src.fiscal.iva.tabla_deducibilidad import DeducibilidadRule
from src.fiscal.models import FacturaRecibida, ResultadoDeducible


def calcular_iva_deducible(
    facturas_recibidas: list[FacturaRecibida],
    tabla_deducibilidad: dict[str, DeducibilidadRule],
) -> ResultadoDeducible:
    """Sum of deductible input VAT (IVA soportado deducible), applying the
    deductibility percentage per expense category.

    Art. 95 LIVA. Pure function: same input always produces same output.

    IMPORTANT: the percentage actually applied is always `factura.porcentaje_deducible`
    — the value already determined for THIS SPECIFIC invoice (set at ingestion,
    after any user confirmation for rule-based or dudoso categories such as
    `comida_profesional` or `suministros_domicilio`). `tabla_deducibilidad` is
    never used to override or recompute a per-invoice percentage — it exists as
    the reference data agents use upstream to *propose* `porcentaje_deducible`
    before an invoice reaches this function, per docs/backend-standards.md
    ("tabla_deducibilidad.py is a data file, not logic").
    """
    por_categoria: dict[str, Decimal] = {}

    for factura in facturas_recibidas:
        cuota_iva = factura.cuota_iva or Decimal("0")
        deducible = (cuota_iva * factura.porcentaje_deducible / Decimal("100")).quantize(Decimal("0.01"))
        por_categoria[factura.categoria_gasto] = (
            por_categoria.get(factura.categoria_gasto, Decimal("0.00")) + deducible
        )

    total = sum(por_categoria.values(), Decimal("0.00"))

    return ResultadoDeducible(por_categoria=por_categoria, total=total)
