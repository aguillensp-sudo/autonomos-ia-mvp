"""SPEC-F4-06 — AEAT test stubs. Never hit real AEAT in tests: these are the
four canned response shapes m303_form.py/rpa_worker.py tests drive a mocked
Playwright Page against, covering every branch of SPEC-F4-04's error table.
"""
from datetime import datetime, timezone
from decimal import Decimal


def respuesta_exito() -> dict:
    """Validation clean, submission succeeds."""
    return {
        "errores_validacion": [],
        "casilla_27_calculada": Decimal("210.00"),
        "casilla_45_calculada": Decimal("50.00"),
        "csv_presentacion": "ABCD1234EFGH5678",
        "nrc_resultado": None,
        "timestamp_presentacion": datetime(2026, 4, 15, 10, 30, tzinfo=timezone.utc),
    }


def respuesta_validacion_error() -> dict:
    """AEAT's own 'Validar' step returns a non-empty error list."""
    return {
        "errores_validacion": ["La casilla 27 no coincide con el detalle declarado"],
        "casilla_27_calculada": Decimal("210.00"),
        "casilla_45_calculada": Decimal("50.00"),
    }


def respuesta_periodo_ya_presentado() -> dict:
    """T04-E1: AEAT reports an existing declaration for this period."""
    return {
        "error": "periodo_ya_presentado",
        "mensaje": "Ya existe una declaración presentada para este período",
    }


def respuesta_aeat_no_disponible() -> dict:
    """T04-E4 (general-failure branch): AEAT unavailable / timeout."""
    return {
        "error": "aeat_no_disponible",
        "status_code": 503,
        "mensaje": "El servicio no está disponible en este momento",
    }
