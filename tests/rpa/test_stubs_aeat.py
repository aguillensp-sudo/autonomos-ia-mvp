"""Smoke tests for the AEAT stub fixtures — asserts each fixture returns the
fields SPEC-F4-04's form-filling/error-handling code expects to parse.
"""
from decimal import Decimal

from tests.rpa._stubs_aeat import (
    respuesta_aeat_no_disponible,
    respuesta_exito,
    respuesta_periodo_ya_presentado,
    respuesta_validacion_error,
)


def test_respuesta_exito_shape():
    r = respuesta_exito()
    assert r["errores_validacion"] == []
    assert r["csv_presentacion"]
    assert isinstance(r["casilla_27_calculada"], Decimal)


def test_respuesta_validacion_error_shape():
    r = respuesta_validacion_error()
    assert len(r["errores_validacion"]) > 0


def test_respuesta_periodo_ya_presentado_shape():
    r = respuesta_periodo_ya_presentado()
    assert r["error"] == "periodo_ya_presentado"


def test_respuesta_aeat_no_disponible_shape():
    r = respuesta_aeat_no_disponible()
    assert r["error"] == "aeat_no_disponible"
    assert r["status_code"] == 503
