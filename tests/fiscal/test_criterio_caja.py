"""Tests for filtrar_por_criterio_caja. Casuística C06 (CA-F2-09). Art. 163 terdecies LIVA."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.fiscal.iva.criterio_caja import filtrar_por_criterio_caja
from src.fiscal.models import FacturaEmitida, FacturaRecibida

PERIODO_INICIO = date(2026, 1, 1)
PERIODO_FIN = date(2026, 3, 31)


def _emitida(fecha, cobrada, fecha_cobro=None) -> FacturaEmitida:
    return FacturaEmitida(
        id=uuid4(),
        user_id=uuid4(),
        numero_factura="F-1",
        fecha=fecha,
        base_imponible=Decimal("100.00"),
        tipo_iva=21,
        cuota_iva=Decimal("21.00"),
        cobrada=cobrada,
        fecha_cobro=fecha_cobro,
    )


def _recibida(fecha, pagada, fecha_pago=None) -> FacturaRecibida:
    return FacturaRecibida(
        id=uuid4(),
        user_id=uuid4(),
        fecha=fecha,
        categoria_gasto="software_saas",
        base_imponible=Decimal("50.00"),
        tipo_iva=21,
        cuota_iva=Decimal("10.50"),
        porcentaje_deducible=Decimal("100"),
        pagada=pagada,
        fecha_pago=fecha_pago,
    )


def test_filtrar_criterio_caja_excluye_no_cobrada():
    emitida_no_cobrada = _emitida(date(2026, 1, 15), cobrada=False, fecha_cobro=None)
    emitidas, recibidas = filtrar_por_criterio_caja(
        [emitida_no_cobrada], [], "criterio_caja", PERIODO_INICIO, PERIODO_FIN
    )
    assert emitidas == []


def test_filtrar_criterio_caja_incluye_cobrada_en_periodo():
    emitida_cobrada = _emitida(date(2026, 1, 15), cobrada=True, fecha_cobro=date(2026, 2, 1))
    emitidas, recibidas = filtrar_por_criterio_caja(
        [emitida_cobrada], [], "criterio_caja", PERIODO_INICIO, PERIODO_FIN
    )
    assert len(emitidas) == 1


def test_filtrar_criterio_caja_excluye_cobrada_fuera_periodo():
    emitida_cobrada_despues = _emitida(date(2026, 1, 15), cobrada=True, fecha_cobro=date(2026, 4, 5))
    emitidas, recibidas = filtrar_por_criterio_caja(
        [emitida_cobrada_despues], [], "criterio_caja", PERIODO_INICIO, PERIODO_FIN
    )
    assert emitidas == []


def test_filtrar_criterio_caja_recibidas_solo_pagadas_en_periodo():
    pagada = _recibida(date(2026, 1, 10), pagada=True, fecha_pago=date(2026, 2, 5))
    no_pagada = _recibida(date(2026, 1, 12), pagada=False, fecha_pago=None)
    emitidas, recibidas = filtrar_por_criterio_caja(
        [], [pagada, no_pagada], "criterio_caja", PERIODO_INICIO, PERIODO_FIN
    )
    assert len(recibidas) == 1


def test_filtrar_criterio_caja_regimen_general_no_filtra():
    """Phase 1 behavior unchanged: regimen general passes invoices through
    regardless of cobrada/pagada — filtering by fecha (issue date) is Phase 1's
    concern, not this function's."""
    no_cobrada = _emitida(date(2026, 1, 15), cobrada=False, fecha_cobro=None)
    emitidas, recibidas = filtrar_por_criterio_caja(
        [no_cobrada], [], "general", PERIODO_INICIO, PERIODO_FIN
    )
    assert len(emitidas) == 1
