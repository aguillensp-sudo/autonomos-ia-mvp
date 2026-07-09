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

    Art. 95 LIVA. `tabla_deducibilidad` is injected data — never hardcoded here.
    Pure function: same input always produces same output.
    """
    por_categoria: dict[str, Decimal] = {}

    for factura in facturas_recibidas:
        rule = tabla_deducibilidad.get(factura.categoria_gasto)
        porcentaje = rule.porcentaje if rule is not None else Decimal("0")
        cuota_iva = factura.cuota_iva or Decimal("0")
        deducible = (cuota_iva * porcentaje / Decimal("100")).quantize(Decimal("0.01"))
        por_categoria[factura.categoria_gasto] = (
            por_categoria.get(factura.categoria_gasto, Decimal("0.00")) + deducible
        )

    total = sum(por_categoria.values(), Decimal("0.00"))

    return ResultadoDeducible(por_categoria=por_categoria, total=total)
