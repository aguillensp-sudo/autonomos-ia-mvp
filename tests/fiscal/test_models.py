"""Validation tests for src/fiscal/models.py. Written before implementation (TDD).
Acceptance criteria: CA-F1-04.
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.fiscal.models import FacturaEmitida, FacturaRecibida


def _valid_factura_kwargs() -> dict:
    return dict(
        id=uuid4(),
        user_id=uuid4(),
        numero_factura="F-2026-001",
        fecha=date(2026, 3, 15),
        nif_cliente="12345678Z",
        base_imponible=Decimal("100.00"),
        tipo_iva=21,
        cuota_iva=Decimal("21.00"),
    )


def test_factura_emitida_tipo_iva_invalido():
    """tipo_iva=25 does not exist in Spain (valid: 0, 4, 10, 21) — must raise ValidationError."""
    kwargs = _valid_factura_kwargs()
    kwargs["tipo_iva"] = 25
    with pytest.raises(ValidationError):
        FacturaEmitida(**kwargs)


def test_factura_emitida_nif_invalido():
    """NIF must match the Spanish format (8 digits + letter, or letter + 7 digits + letter)."""
    kwargs = _valid_factura_kwargs()
    kwargs["nif_cliente"] = "not-a-nif"
    with pytest.raises(ValidationError):
        FacturaEmitida(**kwargs)


def test_factura_emitida_fecha_futura():
    """An invoice dated in the future is invalid."""
    kwargs = _valid_factura_kwargs()
    kwargs["fecha"] = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        FacturaEmitida(**kwargs)


def test_factura_emitida_base_imponible_negativa():
    """base_imponible must be >= 0."""
    kwargs = _valid_factura_kwargs()
    kwargs["base_imponible"] = Decimal("-10.00")
    with pytest.raises(ValidationError):
        FacturaEmitida(**kwargs)


def test_factura_emitida_nif_vacio_es_valido_cuando_opcional():
    """nif_cliente is optional (B2C sales) — None must be accepted, not raise."""
    kwargs = _valid_factura_kwargs()
    kwargs["nif_cliente"] = None
    factura = FacturaEmitida(**kwargs)
    assert factura.nif_cliente is None


def test_factura_recibida_base_imponible_negativa():
    """base_imponible must be >= 0 for received invoices too."""
    kwargs = dict(
        id=uuid4(),
        user_id=uuid4(),
        fecha=date(2026, 3, 15),
        categoria_gasto="software",
        base_imponible=Decimal("-5.00"),
        porcentaje_deducible=Decimal("100"),
    )
    with pytest.raises(ValidationError):
        FacturaRecibida(**kwargs)
