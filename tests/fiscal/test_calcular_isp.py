"""Tests for the ISP (Inversión del Sujeto Pasivo) module.
Acceptance criteria: CA-F2-02, CA-F2-05.
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.fiscal.iva.calcular_isp import ResultadoISP, calcular_isp, detectar_isp
from src.fiscal.models import FacturaRecibida


def _gasto_isp(nif_proveedor, base="100.00", porcentaje="100") -> FacturaRecibida:
    return FacturaRecibida(
        id=uuid4(),
        user_id=uuid4(),
        fecha=date(2026, 3, 1),
        nif_proveedor=nif_proveedor,
        categoria_gasto="software_saas",
        base_imponible=Decimal(base),
        tipo_iva=0,
        cuota_iva=Decimal("0.00"),
        porcentaje_deducible=Decimal(porcentaje),
    )


# --- The 3 mandatory cases per openspec/config.yaml fiscal_integrity_checks ---

def test_detectar_isp_nif_none():
    assert detectar_isp(_gasto_isp(nif_proveedor=None)) is True


def test_detectar_isp_nif_vacio():
    assert detectar_isp(_gasto_isp(nif_proveedor="")) is True


def test_detectar_isp_nif_no_espanol():
    # Not a Spanish NIF/NIE/CIF format, and not in the known-supplier list
    assert detectar_isp(_gasto_isp(nif_proveedor="US-123456789")) is True


# --- Casuística C05 known suppliers ---

def test_detectar_isp_google_ireland_sin_nif_es():
    assert detectar_isp(_gasto_isp(nif_proveedor=None)) is True


def test_detectar_isp_google_spain_con_nif_es():
    # Spanish domestic NIF/CIF format — not ISP
    assert detectar_isp(_gasto_isp(nif_proveedor="12345678Z")) is False


def test_detectar_isp_adobe_sin_nif_es():
    assert detectar_isp(_gasto_isp(nif_proveedor="")) is True


def test_detectar_isp_adobe_con_nif_es():
    assert detectar_isp(_gasto_isp(nif_proveedor="ESB61653893")) is False


def test_detectar_isp_conocido_con_nif_iva_extranjero_formato():
    # NIF-IVA-style prefix but not in the known list and not Spanish format -> ISP
    assert detectar_isp(_gasto_isp(nif_proveedor="IE1234567X")) is True


# --- calcular_isp() aggregate ---

def test_calcular_isp_efecto_neto_cero():
    """100% deductible service triggers ISP but nets to zero devengado vs deducible."""
    facturas = [_gasto_isp(nif_proveedor=None, base="100.00", porcentaje="100")]
    resultado = calcular_isp(facturas)
    assert resultado.base_isp == Decimal("100.00")
    assert resultado.cuota_isp_devengada == Decimal("21.00")
    assert resultado.cuota_isp_deducible == Decimal("21.00")


def test_calcular_isp_efecto_neto_no_cero():
    """Partially deductible ISP service does not net to zero."""
    facturas = [_gasto_isp(nif_proveedor=None, base="100.00", porcentaje="50")]
    resultado = calcular_isp(facturas)
    assert resultado.cuota_isp_devengada == Decimal("21.00")
    assert resultado.cuota_isp_deducible == Decimal("10.50")


def test_calcular_isp_ignora_facturas_sin_isp():
    facturas = [_gasto_isp(nif_proveedor="12345678Z", base="100.00")]
    resultado = calcular_isp(facturas)
    assert resultado.base_isp == Decimal("0.00")
    assert resultado.cuota_isp_devengada == Decimal("0.00")


def test_calcular_isp_acumula_multiples_facturas():
    facturas = [
        _gasto_isp(nif_proveedor=None, base="100.00", porcentaje="100"),
        _gasto_isp(nif_proveedor="", base="50.00", porcentaje="100"),
    ]
    resultado = calcular_isp(facturas)
    assert resultado.base_isp == Decimal("150.00")
    assert resultado.cuota_isp_devengada == Decimal("31.50")
