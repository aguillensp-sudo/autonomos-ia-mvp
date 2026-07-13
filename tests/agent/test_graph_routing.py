"""Unit tests for the graph's pure routing functions and helpers — closes
coverage gaps not requiring a live LLM call.
"""
from src.agent.checkpointer import construir_thread_id
from src.agent.graph import _ruta_tras_confirmar, _ruta_tras_recopilar_datos


def test_ruta_tras_recopilar_datos_sin_actividad_va_a_calcular():
    assert _ruta_tras_recopilar_datos({"sin_actividad": True, "facturas_pendientes_ocr": []}) == "calcular"


def test_ruta_tras_recopilar_datos_con_pendientes_ocr_va_a_ocr():
    assert _ruta_tras_recopilar_datos({"sin_actividad": None, "facturas_pendientes_ocr": ["x.png"]}) == "ocr_factura"


def test_ruta_tras_recopilar_datos_sin_pendientes_va_a_calcular():
    assert _ruta_tras_recopilar_datos({"sin_actividad": None, "facturas_pendientes_ocr": []}) == "calcular"


def test_ruta_tras_recopilar_datos_no_revisa_baja_confianza():
    """Post-second-adversarial-review fix: routing no longer checks
    facturas_baja_confianza at all (no self-edge exists). recopilar_datos
    resolves it internally via a real interrupt() loop before ever
    returning control to this routing function — see
    tests/agent/test_flujo_baja_confianza.py for the interrupt behavior
    itself."""
    estado = {
        "sin_actividad": None,
        "facturas_pendientes_ocr": [],
        "facturas_baja_confianza": [{"path": "emitidas/f1.png", "campo": "base_imponible"}],
    }
    assert _ruta_tras_recopilar_datos(estado) == "calcular"


def test_ruta_tras_confirmar_confirmado_va_a_notificar():
    assert _ruta_tras_confirmar({"confirmado": True, "quiere_revisar": False}) == "notificar"


def test_ruta_tras_confirmar_revisar_va_a_recopilar_datos():
    assert _ruta_tras_confirmar({"confirmado": False, "quiere_revisar": True}) == "recopilar_datos"


def test_ruta_tras_confirmar_cancelado_va_a_notificar():
    assert _ruta_tras_confirmar({"confirmado": False, "quiere_revisar": False}) == "notificar"


def test_construir_thread_id_es_deterministico():
    assert construir_thread_id("user-1", 2026, "1T") == "user-1:P04:2026:1T"
    assert construir_thread_id("user-1", 2026, "1T") == construir_thread_id("user-1", 2026, "1T")
