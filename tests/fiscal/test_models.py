"""Validation tests for src/fiscal/models.py. Written before implementation (TDD).
Acceptance criteria: CA-F1-04.
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.fiscal.models import (
    FacturaEmitida,
    FacturaRecibida,
    ResultadoDeducible,
    ResultadoDevengado,
    ResultadoM303,
)


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


def _resultado_m303_kwargs() -> dict:
    return dict(
        ejercicio=2026,
        periodo="1T",
        total_devengado=Decimal("210.00"),
        total_deducible=Decimal("50.00"),
        saldo_compensar_anterior=Decimal("0.00"),
        resultado=Decimal("160.00"),
        tipo_resultado="a_ingresar",
    )


def test_resultado_m303_devengado_deducible_opcionales_por_defecto_none():
    """SPEC-F4-03 amendment (rpa-aeat): existing direct constructions of
    ResultadoM303 (e.g. tests/integration/test_saldo_iva_compensar.py) omit
    devengado/deducible entirely — this must keep working unchanged."""
    resultado = ResultadoM303(**_resultado_m303_kwargs())
    assert resultado.devengado is None
    assert resultado.deducible is None


def test_resultado_m303_acepta_devengado_deducible_explicitos():
    devengado = ResultadoDevengado(
        por_tipo={21: Decimal("1000.00")},
        cuotas={21: Decimal("210.00")},
        total=Decimal("210.00"),
    )
    deducible = ResultadoDeducible(
        por_categoria={"software_saas": Decimal("50.00")},
        base_por_categoria={"software_saas": Decimal("238.10")},
        total=Decimal("50.00"),
    )
    resultado = ResultadoM303(**_resultado_m303_kwargs(), devengado=devengado, deducible=deducible)
    assert resultado.devengado.por_tipo == {21: Decimal("1000.00")}
    assert resultado.deducible.por_categoria == {"software_saas": Decimal("50.00")}
    assert resultado.deducible.base_por_categoria == {"software_saas": Decimal("238.10")}


def test_resultado_deducible_base_por_categoria_por_defecto_vacio():
    """Existing direct constructions of ResultadoDeducible (e.g.
    tests/fiscal/test_calcular_resultado.py) omit base_por_categoria — must
    keep working, defaulting to {}."""
    deducible = ResultadoDeducible(por_categoria={"software": Decimal("48.30")}, total=Decimal("48.30"))
    assert deducible.base_por_categoria == {}
