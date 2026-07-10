"""Art. 25 LIVA (entregas intracomunitarias exentas), Art. 21 LIVA (exportaciones)
— bloque informativo del M303, casillas 59-63. No afectan a `resultado`, pero
deben estar presentes y correctas (la AEAT las cruza con el M349).

DEFERRED (not this phase): real-time VIES NIF-IVA validation. Casuística C11
requires verifying the client's NIF-IVA in the VIES registry before applying
the intracom. exemption. This function trusts `cliente_es_empresario_ue` as
already-verified input data — it does not call the VIES API.
"""
from decimal import Decimal

from pydantic import BaseModel

from src.fiscal.models import FacturaEmitida


class BloqueInformativo(BaseModel):
    casilla_59: Decimal  # entregas intracomunitarias exentas (bienes/B2C)
    casilla_60: Decimal  # exportaciones (fuera UE)
    casilla_61: Decimal  # operaciones no sujetas / exentas sin derecho a deduccion
    casilla_62: Decimal  # servicios B2B prestados a empresarios UE (ISP en el cliente)


def calcular_bloque_informativo(facturas_emitidas: list[FacturaEmitida]) -> BloqueInformativo:
    """Art. 25 LIVA / Art. 21 LIVA. Casillas 59-63 of the M303:
    - casilla 59: sum(base) where es_intracomunitaria AND NOT cliente_es_empresario_ue
      (goods / B2C intracom. delivery, requires a valid NIF-IVA client per C11 — see
      module docstring for the VIES deferral)
    - casilla 60: sum(base) where es_exportacion (client outside the EU)
    - casilla 61: mixed-activity exempt operations — always 0 this phase (no seed
      profile has a mixed exempt activity; field exists for schema completeness)
    - casilla 62: sum(base) where es_intracomunitaria AND cliente_es_empresario_ue
      (B2B service to a UE business — reverse charge falls on the client)
    """
    casilla_59 = Decimal("0.00")
    casilla_60 = Decimal("0.00")
    casilla_62 = Decimal("0.00")

    for factura in facturas_emitidas:
        if factura.es_intracomunitaria and factura.cliente_es_empresario_ue:
            casilla_62 += factura.base_imponible
        elif factura.es_intracomunitaria:
            casilla_59 += factura.base_imponible
        elif factura.es_exportacion:
            casilla_60 += factura.base_imponible

    return BloqueInformativo(
        casilla_59=casilla_59,
        casilla_60=casilla_60,
        casilla_61=Decimal("0.00"),
        casilla_62=casilla_62,
    )
