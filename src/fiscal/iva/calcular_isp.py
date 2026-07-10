"""Art. 84.Uno.2º LIVA — Inversión del Sujeto Pasivo (ISP).

Known Spanish-registered suppliers — DATA ONLY, never logic (same rule as
tabla_deducibilidad.py). These have had a Spanish NIF-IVA since 2019 and do
NOT trigger ISP. Casuística C05.
"""
import re
from decimal import Decimal

from pydantic import BaseModel

from src.fiscal.models import FacturaRecibida, NIF_NIE_PATTERN

PROVEEDORES_CON_NIF_ESPANOL: dict[str, str] = {
    "Google Ireland Ltd": "ESN0076590D",
    "Meta Platforms Ireland": "ESN0133895B",
    "Adobe Systems": "ESB61653893",
    "Microsoft Ireland": "ESN0004929H",
}

_NIF_IVA_ESPANOL_PATTERN = re.compile(r"^ES[A-Za-z0-9]{9}$")


class ResultadoISP(BaseModel):
    base_isp: Decimal  # casilla 12
    cuota_isp_devengada: Decimal  # casilla 13
    cuota_isp_deducible: Decimal  # feeds into casillas 34-35


def detectar_isp(factura_recibida: FacturaRecibida) -> bool:
    """True if this received invoice triggers ISP self-assessment.

    Art. 84.Uno.2º LIVA. Handles the 3 mandatory cases per
    openspec/config.yaml fiscal_integrity_checks:
    - nif_proveedor is None
    - nif_proveedor == '' (empty string)
    - nif_proveedor is neither a valid Spanish NIF/NIE/CIF nor a known
      Spanish-registered NIF-IVA (e.g. 'ESB61653893')

    Spanish domestic NIFs (e.g. '12345678Z') do NOT carry an 'ES' prefix —
    that prefix only appears on NIF-IVA codes issued to foreign entities
    registered for VAT in Spain (e.g. Adobe's 'ESB61653893'). ISP applies
    unless the supplier has either format.
    """
    nif = factura_recibida.nif_proveedor
    if not nif:
        return True
    if NIF_NIE_PATTERN.match(nif):
        return False
    if _NIF_IVA_ESPANOL_PATTERN.match(nif):
        return False
    return True


def calcular_isp(facturas_recibidas: list[FacturaRecibida]) -> ResultadoISP:
    """Aggregates ISP self-liquidation across all received invoices that
    trigger detectar_isp(). Art. 84.Uno.2º LIVA.

    For each triggering invoice:
    - base_isp += base_imponible (casilla 12)
    - cuota_isp_devengada += base_imponible * 21% (casilla 13 — the autónomo
      self-assesses at the general rate regardless of the supplier's own
      invoice, since the supplier charged no Spanish VAT)
    - cuota_isp_deducible += cuota_isp_devengada_de_esta_factura * porcentaje_deducible / 100
      (feeds casillas 34-35; net effect is 0 when porcentaje_deducible == 100)
    """
    base_isp = Decimal("0.00")
    cuota_isp_devengada = Decimal("0.00")
    cuota_isp_deducible = Decimal("0.00")

    for factura in facturas_recibidas:
        if not detectar_isp(factura):
            continue
        cuota_factura = (factura.base_imponible * Decimal("0.21")).quantize(Decimal("0.01"))
        base_isp += factura.base_imponible
        cuota_isp_devengada += cuota_factura
        cuota_isp_deducible += (cuota_factura * factura.porcentaje_deducible / Decimal("100")).quantize(Decimal("0.01"))

    return ResultadoISP(
        base_isp=base_isp,
        cuota_isp_devengada=cuota_isp_devengada,
        cuota_isp_deducible=cuota_isp_deducible,
    )
